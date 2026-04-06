#!/bin/bash
# Build a standalone .app bundle using py2app

cd "$(dirname "$0")"
source .venv/bin/activate

pip install -q py2app

# Create setup.py for py2app
rm -rf build dist

cat > setup_app.py << 'EOF'
from setuptools import setup

APP = ['app.py']
DATA_FILES = ['config.py']
OPTIONS = {
    'argv_emulation': False,
    'plist': {
        'CFBundleName': 'icloudpd Monitor',
        'CFBundleDisplayName': 'icloudpd Monitor',
        'CFBundleIdentifier': 'com.tommi.icloudpd-monitor',
        'CFBundleVersion': '1.0.0',
        'LSUIElement': True,  # Hide from Dock
        'NSHighResolutionCapable': True,
    },
    'packages': ['paramiko', 'rumps', 'cffi', 'nacl', 'bcrypt', 'cryptography'],
    'includes': ['PyObjCTools', 'PyObjCTools.AppHelper', 'objc', 'Foundation', 'AppKit'],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
EOF

echo "Building .app bundle..."
python3 setup_app.py py2app 2>&1 | tail -20

if [ -d "dist/icloudpd Monitor.app" ]; then
    echo ""
    echo "✅ Build erfolgreich!"
    echo ""
    # Stop running instances
    launchctl unload ~/Library/LaunchAgents/com.tommi.icloudpd-monitor.plist 2>/dev/null
    pkill -f "icloudpd Monitor" 2>/dev/null
    pkill -f "python3 app.py" 2>/dev/null
    sleep 1
    # Install to /Applications
    rm -rf "/Applications/icloudpd Monitor.app"
    cp -R "dist/icloudpd Monitor.app" /Applications/
    echo "✅ Installiert nach /Applications/icloudpd Monitor.app"
else
    echo "❌ Build fehlgeschlagen"
    exit 1
fi
