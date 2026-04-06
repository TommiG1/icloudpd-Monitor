# icloudpd Monitor

macOS-Menüleisten-App zur Überwachung und Steuerung des [icloudpd](https://github.com/boredazfcuk/docker-icloudpd) Docker-Containers auf einem Unraid-Server.

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![macOS](https://img.shields.io/badge/macOS-13%2B-black)
![License](https://img.shields.io/badge/License-MIT-green)

## Features

| Feature | Beschreibung |
|---------|-------------|
| **Status-Anzeige** | ☁️ Läuft · ⛅ Gestoppt · 🌧 Fehler · ⚠️ MFA-Warnung |
| **Container-Steuerung** | Starten, Stoppen, Neustarten per Menü |
| **MFA-Überwachung** | Zeigt Ablaufdatum und verbleibende Tage der 2FA-Session |
| **MFA-Erneuerung** | 6-stelligen Code direkt über die App eingeben |
| **Logs** | Letzte Log-Zeilen abrufen und in TextEdit anzeigen |
| **Auto-Polling** | Status wird alle 30 Sekunden aktualisiert |
| **Autostart** | Startet automatisch beim Login via LaunchAgent |

## Voraussetzungen

### macOS

- macOS 13 (Ventura) oder neuer
- Python 3.9+ (im Lieferumfang von Xcode Command Line Tools)

### Server (Unraid)

- [boredazfcuk/docker-icloudpd](https://github.com/boredazfcuk/docker-icloudpd) Container läuft
- SSH-Zugang zum Server (Root oder User mit Docker-Rechten)
- Container mit `authentication_type=2FA` konfiguriert

## Installation

### 1. Repository klonen

```bash
git clone https://github.com/tommigraef/icloudpd-Monitor.git
cd icloudpd-Monitor
```

### 2. Python-Abhängigkeiten installieren

Die App benötigt eine virtuelle Python-Umgebung mit folgenden Paketen:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### Abhängigkeiten

| Paket | Version | Zweck |
|-------|---------|-------|
| [rumps](https://github.com/jaredks/rumps) | ≥ 0.4.0 | macOS Menüleisten-Framework (basiert auf PyObjC) |
| [paramiko](https://www.paramiko.org/) | ≥ 3.0.0 | SSH-Verbindung zum Unraid-Server |

Diese ziehen automatisch folgende Unter-Abhängigkeiten:

- **pyobjc-core** / **pyobjc-framework-Cocoa** – Python-Bindings für macOS AppKit/Foundation
- **PyObjCTools** – Hilfsfunktionen (u.a. `AppHelper.callAfter` für Thread-sichere UI-Updates)
- **cryptography** / **bcrypt** / **pynacl** / **cffi** – SSH-Kryptographie (Paramiko)

### 3. Konfiguration

```bash
cp config.example.py config.py
```

Bearbeite `config.py` mit deinen Server-Daten:

```python
SSH_HOST = "192.168.1.25"        # IP deines Unraid-Servers
SSH_PORT = 22
SSH_USER = "root"
SSH_PASSWORD = "dein_passwort"   # Oder SSH-Keys verwenden

CONTAINER_NAME = "icloudpd"
CONFIG_PATH = "/mnt/user/appdata/icloudpd"
COOKIE_FILE = "deineemailadresse"  # Apple ID ohne Sonderzeichen
```

> **Hinweis:** `COOKIE_FILE` ist deine Apple ID mit entfernten Sonderzeichen.
> Beispiel: `john.doe@gmail.com` → `johndoegmailcom`

### 4. App starten

#### Variante A: Direkt aus dem Terminal

```bash
source .venv/bin/activate
python3 app.py
```

Oder mit dem Schnellstart-Script:

```bash
./run.sh
```

#### Variante B: Als native macOS-App (empfohlen)

Baut ein eigenständiges `.app`-Bundle und installiert es nach `/Applications`:

```bash
source .venv/bin/activate
pip install py2app
./build.sh
```

Die App liegt dann unter `/Applications/icloudpd Monitor.app`.

### 5. Autostart einrichten

Erstelle einen LaunchAgent, damit die App bei jedem Login startet:

```bash
cat > ~/Library/LaunchAgents/com.tommi.icloudpd-monitor.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.tommi.icloudpd-monitor</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/open</string>
        <string>-a</string>
        <string>/Applications/icloudpd Monitor.app</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>/tmp/icloudpd-monitor.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/icloudpd-monitor.err</string>
</dict>
</plist>
EOF
```

Aktivieren:

```bash
launchctl load ~/Library/LaunchAgents/com.tommi.icloudpd-monitor.plist
```

### Nützliche Befehle

| Aktion | Befehl |
|--------|--------|
| App starten | `open -a "icloudpd Monitor"` |
| App stoppen | `pkill -f "icloudpd Monitor"` |
| Autostart deaktivieren | `launchctl unload ~/Library/LaunchAgents/com.tommi.icloudpd-monitor.plist` |
| Autostart aktivieren | `launchctl load ~/Library/LaunchAgents/com.tommi.icloudpd-monitor.plist` |
| Logs prüfen | `cat /tmp/icloudpd-monitor.err` |
| Neu bauen + installieren | `cd ~/Projects/icloudpd-Monitor && source .venv/bin/activate && ./build.sh` |

## Projektstruktur

```
icloudpd-Monitor/
├── app.py              # Hauptanwendung (rumps + paramiko)
├── config.example.py   # Konfigurations-Vorlage
├── config.py           # Deine Konfiguration (git-ignored)
├── requirements.txt    # Python-Abhängigkeiten
├── run.sh              # Schnellstart-Script
├── build.sh            # Baut .app-Bundle und installiert nach /Applications
└── .gitignore
```

## Fehlerbehebung

### App crasht sofort
Prüfe `/tmp/icloudpd-monitor.err` auf Fehlermeldungen. Häufige Ursache: `config.py` fehlt oder SSH-Daten sind falsch.

### SSH-Verbindung schlägt fehl
- Server erreichbar? `ping 192.168.1.XXX`
- SSH-Port offen? `nc -zv 192.168.1.XXX 22`
- Credentials korrekt? `ssh root@192.168.1.XXX`

### MFA-Erneuerung schlägt fehl
- Container muss laufen
- Code muss 6-stellig sein
- Bei Problemen: Container-Logs über die App prüfen

## Lizenz

MIT
