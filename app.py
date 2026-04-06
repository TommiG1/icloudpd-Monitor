"""
icloudpd Menubar Monitor
macOS status bar app to monitor and control icloudpd Docker container on Unraid.
"""

import rumps
import paramiko
import threading
import time
import re
import subprocess
from datetime import datetime, timezone
from PyObjCTools import AppHelper

from config import (
    SSH_HOST, SSH_PORT, SSH_USER, SSH_PASSWORD,
    CONTAINER_NAME, POLL_INTERVAL, LOG_LINES,
    CONFIG_PATH, COOKIE_FILE, MFA_WARN_DAYS,
)


# ── Status bar icons (emoji-based) ──────────────────────────────────────
ICON_RUNNING = "☁️"
ICON_STOPPED = "⛅"
ICON_ERROR = "🌧"
ICON_SYNCING = "⏳"
ICON_MFA_WARN = "⚠️"


class SSHConnection:
    """Manages a reusable SSH connection to the Unraid server."""

    def __init__(self):
        self._client = None
        self._lock = threading.Lock()

    def _connect(self):
        """Establish SSH connection."""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            SSH_HOST,
            port=SSH_PORT,
            username=SSH_USER,
            password=SSH_PASSWORD,
            timeout=10,
            banner_timeout=10,
        )
        return client

    def execute(self, command, timeout=15):
        """Execute a command over SSH. Returns (stdout, stderr, exit_code)."""
        with self._lock:
            try:
                if self._client is None or self._client.get_transport() is None or not self._client.get_transport().is_active():
                    self._client = self._connect()
                stdin, stdout, stderr = self._client.exec_command(command, timeout=timeout)
                exit_code = stdout.channel.recv_exit_status()
                return stdout.read().decode("utf-8", errors="replace"), stderr.read().decode("utf-8", errors="replace"), exit_code
            except Exception as e:
                # Reset connection on error
                self._client = None
                raise e

    def close(self):
        with self._lock:
            if self._client:
                self._client.close()
                self._client = None


class ICloudPDMenubar(rumps.App):
    def __init__(self):
        super().__init__(
            ICON_ERROR,
            title=None,
            quit_button=None,
        )

        self.ssh = SSHConnection()
        self._status = "unknown"
        self._last_check = None
        self._logs_cache = ""
        self._days_remaining = None
        self._mfa_expiry_date = None

        # ── Build menu ──────────────────────────────────────────────
        self.status_item = rumps.MenuItem("Status: prüfe...", callback=None)
        self.status_item.set_callback(None)

        self.last_check_item = rumps.MenuItem("Letzte Prüfung: –", callback=None)
        self.last_check_item.set_callback(None)

        self.separator1 = rumps.separator

        # ── MFA section ─────────────────────────────────────────────
        self.mfa_expiry_item = rumps.MenuItem("🔑 MFA: prüfe...", callback=None)
        self.mfa_expiry_item.set_callback(None)

        self.mfa_days_item = rumps.MenuItem("   Tage verbleibend: –", callback=None)
        self.mfa_days_item.set_callback(None)

        self.mfa_reauth_item = rumps.MenuItem("🔐 Neu authentifizieren (MFA)…", callback=self.on_reauth)

        self.separator_mfa = rumps.separator

        # ── Container controls ──────────────────────────────────────
        self.start_item = rumps.MenuItem("▶ Container starten", callback=self.on_start)
        self.stop_item = rumps.MenuItem("⏹ Container stoppen", callback=self.on_stop)
        self.restart_item = rumps.MenuItem("🔄 Container neustarten", callback=self.on_restart)

        self.separator2 = rumps.separator

        self.logs_item = rumps.MenuItem("📋 Logs anzeigen", callback=self.on_show_logs)
        self.refresh_item = rumps.MenuItem("🔃 Jetzt prüfen", callback=self.on_refresh)

        self.separator3 = rumps.separator

        self.quit_item = rumps.MenuItem("Beenden", callback=self.on_quit)

        self.menu = [
            self.status_item,
            self.last_check_item,
            self.separator1,
            self.mfa_expiry_item,
            self.mfa_days_item,
            self.mfa_reauth_item,
            self.separator_mfa,
            self.start_item,
            self.stop_item,
            self.restart_item,
            self.separator2,
            self.logs_item,
            self.refresh_item,
            self.separator3,
            self.quit_item,
        ]

        # Start background polling
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    # ── Polling ─────────────────────────────────────────────────────
    def _poll_loop(self):
        while True:
            self._check_status()
            time.sleep(POLL_INTERVAL)

    def _check_status(self):
        try:
            cmd = f'docker inspect --format "{{{{.State.Status}}}} {{{{.State.StartedAt}}}}" {CONTAINER_NAME} 2>/dev/null'
            stdout, stderr, code = self.ssh.execute(cmd)

            if code != 0 or not stdout.strip():
                self._update_ui("not_found", "Container nicht gefunden")
                return

            parts = stdout.strip().split(" ", 1)
            state = parts[0]
            started = parts[1] if len(parts) > 1 else ""

            if state == "running":
                # Get a quick health indicator from recent logs
                log_cmd = f"docker logs {CONTAINER_NAME} --tail 3 2>&1 | tail -1"
                log_out, _, _ = self.ssh.execute(log_cmd, timeout=10)
                last_log = log_out.strip().split("\n")[-1] if log_out.strip() else ""

                short_info = last_log[:60] + "…" if len(last_log) > 60 else last_log
                self._update_ui("running", f"Läuft – {short_info}")
            elif state == "exited":
                self._update_ui("stopped", "Container gestoppt")
            elif state == "restarting":
                self._update_ui("syncing", "Container startet neu…")
            else:
                self._update_ui("unknown", f"Status: {state}")

            # Check MFA expiry
            self._check_mfa_expiry()

        except Exception as e:
            self._update_ui("error", f"SSH-Fehler: {str(e)[:50]}")

    def _check_mfa_expiry(self):
        """Read DAYS_REMAINING and cookie expiry date from the server."""
        try:
            # Read DAYS_REMAINING
            cmd_days = f"cat {CONFIG_PATH}/DAYS_REMAINING 2>/dev/null"
            stdout, _, code = self.ssh.execute(cmd_days, timeout=10)
            if code == 0 and stdout.strip().isdigit():
                self._days_remaining = int(stdout.strip())
            else:
                self._days_remaining = None

            # Read MFA cookie expiry date from cookie file
            cmd_expiry = (
                f"grep 'X-APPLE-WEBAUTH-USER' {CONFIG_PATH}/{COOKIE_FILE} 2>/dev/null"
                f" | sed -e 's#.*expires=\"\\(.*\\)Z\"; HttpOnly.*#\\1#'"
            )
            stdout, _, code = self.ssh.execute(cmd_expiry, timeout=10)
            expiry_str = stdout.strip()
            if expiry_str:
                try:
                    self._mfa_expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    self._mfa_expiry_date = None
            else:
                self._mfa_expiry_date = None

            # Update MFA UI on main thread
            AppHelper.callAfter(self._apply_mfa_ui)

        except Exception:
            AppHelper.callAfter(self._apply_mfa_error)

    def _apply_mfa_error(self):
        """Set MFA error text (must be called on main thread)."""
        self.mfa_expiry_item.title = "🔑 MFA: Fehler beim Abruf"
        self.mfa_days_item.title = "   Tage verbleibend: ?"

    def _apply_mfa_ui(self):
        """Update MFA-related menu items (must be called on main thread)."""
        if self._mfa_expiry_date:
            expiry_display = self._mfa_expiry_date.strftime("%d.%m.%Y %H:%M")
            self.mfa_expiry_item.title = f"🔑 MFA läuft ab: {expiry_display}"
        else:
            self.mfa_expiry_item.title = "🔑 MFA Ablauf: unbekannt"

        if self._days_remaining is not None:
            days = self._days_remaining
            if days <= 0:
                self.mfa_days_item.title = f"   ⛔ ABGELAUFEN! Neu-Auth nötig!"
                # Override status bar icon
                self.title = ICON_MFA_WARN
            elif days <= MFA_WARN_DAYS:
                self.mfa_days_item.title = f"   ⚠️ Noch {days} Tage verbleibend"
                if self._status == "running":
                    self.title = ICON_MFA_WARN
            else:
                self.mfa_days_item.title = f"   ✅ Noch {days} Tage verbleibend"
        else:
            self.mfa_days_item.title = "   Tage verbleibend: –"

    def _update_ui(self, status, text):
        self._status = status
        self._last_check = datetime.now().strftime("%H:%M:%S")
        AppHelper.callAfter(self._apply_ui, status, text)

    def _apply_ui(self, status, text):
        """Apply UI changes (must be called on main thread)."""
        icon_map = {
            "running": ICON_RUNNING,
            "stopped": ICON_STOPPED,
            "error": ICON_ERROR,
            "not_found": ICON_ERROR,
            "syncing": ICON_SYNCING,
            "unknown": ICON_ERROR,
        }
        self.title = icon_map.get(status, ICON_ERROR)
        self.status_item.title = f"Status: {text}"
        self.last_check_item.title = f"Letzte Prüfung: {self._last_check}"

        # Enable/disable buttons based on state
        is_running = status == "running"
        self.start_item.set_callback(None if is_running else self.on_start)
        self.stop_item.set_callback(self.on_stop if is_running else None)

    # ── Actions ─────────────────────────────────────────────────────
    def _run_docker_action(self, action, label):
        """Run a docker action in a background thread."""
        def _do():
            self._update_ui("syncing", f"{label}…")
            try:
                cmd = f"docker {action} {CONTAINER_NAME}"
                stdout, stderr, code = self.ssh.execute(cmd, timeout=60)
                if code != 0:
                    err = stderr.strip() or stdout.strip()
                    rumps.notification(
                        "icloudpd Monitor",
                        f"{label} fehlgeschlagen",
                        err[:100],
                    )
                else:
                    rumps.notification(
                        "icloudpd Monitor",
                        label,
                        "Erfolgreich ✓",
                    )
                # Re-check immediately
                time.sleep(2)
                self._check_status()
            except Exception as e:
                self._update_ui("error", f"Fehler: {str(e)[:50]}")
                rumps.notification("icloudpd Monitor", "Fehler", str(e)[:100])

        threading.Thread(target=_do, daemon=True).start()

    def on_start(self, _):
        self._run_docker_action("start", "Container starten")

    def on_stop(self, _):
        self._run_docker_action("stop", "Container stoppen")

    def on_restart(self, _):
        self._run_docker_action("restart", "Container neustarten")

    def on_refresh(self, _):
        threading.Thread(target=self._check_status, daemon=True).start()

    def on_show_logs(self, _):
        """Fetch logs and display in a window."""
        def _fetch_and_show():
            try:
                cmd = f"docker logs {CONTAINER_NAME} --tail {LOG_LINES} 2>&1"
                stdout, stderr, code = self.ssh.execute(cmd, timeout=20)
                log_text = stdout if stdout else stderr
                if not log_text.strip():
                    log_text = "(Keine Logs verfügbar)"

                # Write to temp file and open in TextEdit for a quick viewer
                tmp_path = "/tmp/icloudpd_logs.txt"
                header = f"=== icloudpd Logs (letzte {LOG_LINES} Zeilen) ===\n"
                header += f"=== Abgerufen: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n\n"
                with open(tmp_path, "w") as f:
                    f.write(header + log_text)
                subprocess.Popen(["open", "-a", "TextEdit", tmp_path])

            except Exception as e:
                rumps.notification("icloudpd Monitor", "Log-Fehler", str(e)[:100])

        threading.Thread(target=_fetch_and_show, daemon=True).start()

    def on_reauth(self, _):
        """Prompt for MFA code and run re-authentication."""
        # Step 1: Ask for MFA code
        window = rumps.Window(
            message=(
                "Gib den 6-stelligen Code von deinem Apple-Gerät ein.\n\n"
                "Der Container wird die Session-Cookies erneuern."
            ),
            title="iCloud 2FA Authentifizierung",
            default_text="",
            ok="Authentifizieren",
            cancel="Abbrechen",
            dimensions=(220, 24),
        )
        response = window.run()
        if not response.clicked:
            return

        mfa_code = response.text.strip()
        if not re.match(r"^\d{6}$", mfa_code):
            rumps.notification(
                "icloudpd Monitor",
                "Ungültiger Code",
                "Bitte einen 6-stelligen Zahlencode eingeben.",
            )
            return

        # Step 2: Run re-auth in background thread
        def _do_reauth():
            self._update_ui("syncing", "Authentifizierung läuft…")
            AppHelper.callAfter(lambda: setattr(self.mfa_reauth_item, 'title', '🔐 Authentifizierung läuft…'))
            AppHelper.callAfter(lambda: self.mfa_reauth_item.set_callback(None))

            try:
                # Use interactive SSH channel for the auth-only command
                # The reauth.sh script deletes cookies and runs icloudpd --auth-only
                # which expects interactive 2FA input
                result = self._run_interactive_reauth(mfa_code)

                if result["success"]:
                    rumps.notification(
                        "icloudpd Monitor",
                        "Authentifizierung erfolgreich ✓",
                        "MFA-Session wurde erneuert.",
                    )
                    # Restart container to pick up new session
                    self.ssh.execute(f"docker restart {CONTAINER_NAME}", timeout=60)
                    time.sleep(3)
                else:
                    rumps.notification(
                        "icloudpd Monitor",
                        "Authentifizierung fehlgeschlagen",
                        result.get("error", "Unbekannter Fehler")[:100],
                    )

                self._check_status()

            except Exception as e:
                rumps.notification("icloudpd Monitor", "Auth-Fehler", str(e)[:100])
                self._update_ui("error", f"Auth-Fehler: {str(e)[:50]}")
            finally:
                AppHelper.callAfter(self._reset_reauth_button)

        threading.Thread(target=_do_reauth, daemon=True).start()

    def _reset_reauth_button(self):
        self.mfa_reauth_item.title = "🔐 Neu authentifizieren (MFA)…"
        self.mfa_reauth_item.set_callback(self.on_reauth)

    def _run_interactive_reauth(self, mfa_code):
        """Run icloudpd --auth-only interactively and feed MFA code."""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            SSH_HOST,
            port=SSH_PORT,
            username=SSH_USER,
            password=SSH_PASSWORD,
            timeout=15,
        )

        try:
            # Run reauth via docker exec with pseudo-tty
            channel = client.get_transport().open_session()
            channel.settimeout(90)
            channel.get_pty()

            # Use the container's reauth mechanism:
            # Delete old cookies, run icloudpd --auth-only
            reauth_cmd = (
                f"docker exec -i {CONTAINER_NAME} sh -c '"
                f"rm -f /config/{COOKIE_FILE} /config/{COOKIE_FILE}.session 2>/dev/null; "
                f"/opt/icloudpd/bin/icloudpd "
                f"--username $(grep apple_id /config/icloudpd.conf | cut -d= -f2) "
                f"--cookie-directory /config "
                f"--auth-only "
                f"--domain com"
                f"'"
            )

            channel.exec_command(reauth_cmd)

            output = ""
            mfa_sent = False
            start_time = time.time()

            while time.time() - start_time < 80:
                if channel.recv_ready():
                    chunk = channel.recv(4096).decode("utf-8", errors="replace")
                    output += chunk

                    # Look for MFA code prompt and send code
                    if not mfa_sent and ("enter the code" in output.lower()
                                         or "verification code" in output.lower()
                                         or "two-factor" in output.lower()
                                         or "2fa" in output.lower()
                                         or "please enter" in output.lower()):
                        time.sleep(1)
                        channel.sendall(mfa_code + "\n")
                        mfa_sent = True

                if channel.exit_status_ready():
                    # Drain remaining output
                    while channel.recv_ready():
                        output += channel.recv(4096).decode("utf-8", errors="replace")
                    break

                time.sleep(0.5)

            exit_code = channel.recv_exit_status()

            # Check for success indicators
            output_lower = output.lower()
            if exit_code == 0 or "authentication successful" in output_lower or "great" in output_lower:
                return {"success": True, "output": output}
            else:
                # Extract last meaningful line as error
                lines = [l.strip() for l in output.strip().split("\n") if l.strip()]
                error_msg = lines[-1] if lines else f"Exit code: {exit_code}"
                return {"success": False, "error": error_msg, "output": output}

        finally:
            client.close()

    def on_quit(self, _):
        self.ssh.close()
        rumps.quit_application()


if __name__ == "__main__":
    ICloudPDMenubar().run()
