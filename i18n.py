"""
Internationalization (i18n) for icloudpd Monitor.
Detects macOS system language and provides translated UI strings.
Supported: English (en), German (de). Fallback: English.
"""

from Foundation import NSLocale

# ── Language detection ───────────────────────────────────────────────────
_preferred = NSLocale.preferredLanguages()
_lang_code = str(_preferred[0])[:2] if _preferred else "en"
LANG = _lang_code if _lang_code in ("de", "en") else "en"

# ── Translations ─────────────────────────────────────────────────────────
_STRINGS = {
    # Menu items
    "status_checking":          {"de": "Status: prüfe…",                    "en": "Status: checking…"},
    "last_check_none":          {"de": "Letzte Prüfung: –",                 "en": "Last check: –"},
    "last_check":               {"de": "Letzte Prüfung: {}",                "en": "Last check: {}"},
    "mfa_checking":             {"de": "🔑 MFA: prüfe…",                   "en": "🔑 MFA: checking…"},
    "days_remaining_none":      {"de": "   Tage verbleibend: –",            "en": "   Days remaining: –"},
    "reauth_button":            {"de": "🔐 Neu authentifizieren (MFA)…",    "en": "🔐 Re-authenticate (MFA)…"},
    "start_container":          {"de": "▶ Container starten",               "en": "▶ Start container"},
    "stop_container":           {"de": "⏹ Container stoppen",               "en": "⏹ Stop container"},
    "restart_container":        {"de": "🔄 Container neustarten",           "en": "🔄 Restart container"},
    "show_logs":                {"de": "📋 Logs anzeigen",                  "en": "📋 Show logs"},
    "check_now":                {"de": "🔃 Jetzt prüfen",                   "en": "🔃 Check now"},
    "quit":                     {"de": "Beenden",                           "en": "Quit"},

    # Status messages
    "container_not_found":      {"de": "Container nicht gefunden",          "en": "Container not found"},
    "running":                  {"de": "Läuft – {}",                        "en": "Running – {}"},
    "container_stopped":        {"de": "Container gestoppt",                "en": "Container stopped"},
    "container_restarting":     {"de": "Container startet neu…",            "en": "Container restarting…"},
    "ssh_error":                {"de": "SSH-Fehler: {}",                    "en": "SSH error: {}"},
    "error":                    {"de": "Fehler: {}",                        "en": "Error: {}"},

    # MFA
    "mfa_fetch_error":          {"de": "🔑 MFA: Fehler beim Abruf",        "en": "🔑 MFA: fetch error"},
    "days_remaining_unknown":   {"de": "   Tage verbleibend: ?",            "en": "   Days remaining: ?"},
    "mfa_expires":              {"de": "🔑 MFA läuft ab: {}",               "en": "🔑 MFA expires: {}"},
    "mfa_expiry_unknown":       {"de": "🔑 MFA Ablauf: unbekannt",          "en": "🔑 MFA expiry: unknown"},
    "mfa_expired":              {"de": "   ⛔ ABGELAUFEN! Neu-Auth nötig!", "en": "   ⛔ EXPIRED! Re-auth needed!"},
    "days_remaining_warn":      {"de": "   ⚠️ Noch {} Tage verbleibend",   "en": "   ⚠️ {} days remaining"},
    "days_remaining_ok":        {"de": "   ✅ Noch {} Tage verbleibend",    "en": "   ✅ {} days remaining"},

    # Docker actions
    "action_start":             {"de": "Container starten",                 "en": "Start container"},
    "action_stop":              {"de": "Container stoppen",                 "en": "Stop container"},
    "action_restart":           {"de": "Container neustarten",              "en": "Restart container"},
    "action_failed":            {"de": "{} fehlgeschlagen",                 "en": "{} failed"},
    "action_success":           {"de": "Erfolgreich ✓",                     "en": "Success ✓"},

    # Logs
    "no_logs":                  {"de": "(Keine Logs verfügbar)",            "en": "(No logs available)"},
    "logs_header":              {"de": "=== icloudpd Logs (letzte {} Zeilen) ===", "en": "=== icloudpd Logs (last {} lines) ==="},
    "logs_retrieved":           {"de": "=== Abgerufen: {} ===",             "en": "=== Retrieved: {} ==="},
    "log_error":                {"de": "Log-Fehler",                        "en": "Log error"},

    # Re-auth dialog
    "reauth_message":           {"de": "Gib den 6-stelligen Code von deinem Apple-Gerät ein.\n\nDer Container wird die Session-Cookies erneuern.",
                                 "en": "Enter the 6-digit code from your Apple device.\n\nThe container will renew the session cookies."},
    "reauth_title":             {"de": "iCloud 2FA Authentifizierung",      "en": "iCloud 2FA Authentication"},
    "reauth_ok":                {"de": "Authentifizieren",                  "en": "Authenticate"},
    "reauth_cancel":            {"de": "Abbrechen",                         "en": "Cancel"},
    "invalid_code":             {"de": "Ungültiger Code",                   "en": "Invalid code"},
    "invalid_code_msg":         {"de": "Bitte einen 6-stelligen Zahlencode eingeben.", "en": "Please enter a 6-digit numeric code."},
    "auth_in_progress":         {"de": "Authentifizierung läuft…",          "en": "Authenticating…"},
    "reauth_in_progress":       {"de": "🔐 Authentifizierung läuft…",      "en": "🔐 Authenticating…"},
    "auth_success":             {"de": "Authentifizierung erfolgreich ✓",   "en": "Authentication successful ✓"},
    "auth_session_renewed":     {"de": "MFA-Session wurde erneuert.",       "en": "MFA session has been renewed."},
    "auth_failed":              {"de": "Authentifizierung fehlgeschlagen",   "en": "Authentication failed"},
    "auth_unknown_error":       {"de": "Unbekannter Fehler",               "en": "Unknown error"},
    "auth_error":               {"de": "Auth-Fehler",                       "en": "Auth error"},
}


def t(key, *args):
    """Get translated string. Use {} placeholders and pass values as args."""
    entry = _STRINGS.get(key)
    if entry is None:
        return key
    text = entry.get(LANG, entry.get("en", key))
    if args:
        return text.format(*args)
    return text
