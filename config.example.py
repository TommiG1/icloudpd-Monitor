# icloudpd Menubar Monitor - Configuration
# Copy this file to config.py and edit the values below.

SSH_HOST = "192.168.1.XXX"       # IP or hostname of your Unraid server
SSH_PORT = 22
SSH_USER = "root"
SSH_PASSWORD = "YOUR_PASSWORD"   # Consider using SSH keys instead

CONTAINER_NAME = "icloudpd"

# Host path where icloudpd appdata is stored
CONFIG_PATH = "/mnt/user/appdata/icloudpd"

# Cookie file name (apple_id with non-alphanumeric chars stripped)
# e.g. john.doe@gmail.com -> johndoegmailcom
COOKIE_FILE = "youremailaddresshere"

# How often to poll container status (seconds)
POLL_INTERVAL = 30

# Number of log lines to show
LOG_LINES = 40

# Days remaining threshold for warning icon in menu bar
MFA_WARN_DAYS = 14
