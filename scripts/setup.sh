#!/bin/bash

# BabylonPiles Setup Script for Raspberry Pi
# This script sets up the complete BabylonPiles system

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BABYLONPILES_DIR="/opt/babylonpiles"
DATA_DIR="/mnt/babylonpiles"
SERVICE_USER="babylonpiles"
SERVICE_NAME="babylonpiles"

# Logging
LOG_FILE="/var/log/babylonpiles-setup.log"

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" | tee -a "$LOG_FILE"
    exit 1
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}" | tee -a "$LOG_FILE"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)"
    fi
}

# Update system
update_system() {
    log "Updating system packages..."
    apt update && apt upgrade -y
}

# Install system dependencies
install_dependencies() {
    log "Installing system dependencies..."
    
    # Python and development tools
    apt install -y python3 python3-pip python3-venv python3-dev
    
    # Database
    apt install -y sqlite3
    
    # Network tools
    apt install -y hostapd dnsmasq iptables-persistent
    
    # File system tools
    apt install -y ntfs-3g exfat-fuse exfat-utils
    
    # Monitoring tools
    apt install -y htop iotop nethogs
    
    # Torrent client (optional)
    apt install -y transmission-cli
    
    # Git
    apt install -y git
    
    # Build tools
    apt install -y build-essential cmake pkg-config
    
    # Additional Python packages
    apt install -y python3-psutil python3-aiohttp python3-yaml
}

# Create service user
create_user() {
    log "Creating service user..."
    
    if ! id "$SERVICE_USER" &>/dev/null; then
        useradd -r -s /bin/bash -d "$BABYLONPILES_DIR" "$SERVICE_USER"
        log "Created user: $SERVICE_USER"
    else
        warn "User $SERVICE_USER already exists"
    fi
}

# Setup storage
setup_storage() {
    log "Setting up storage..."
    
    # Create data directory
    mkdir -p "$DATA_DIR"
    chown "$SERVICE_USER:$SERVICE_USER" "$DATA_DIR"
    
    # Auto-mount external drives
    setup_auto_mount
}

# Setup auto-mount for external drives
setup_auto_mount() {
    log "Setting up auto-mount for external drives..."
    
    # Create mount point
    mkdir -p /mnt/external
    
    # Add to fstab for auto-mount
    if ! grep -q "external" /etc/fstab; then
        echo "# Auto-mount external drives for BabylonPiles" >> /etc/fstab
        echo "/dev/sda1 /mnt/external auto defaults,noatime 0 0" >> /etc/fstab
    fi
    
    # Create udev rule for automatic mounting
    cat > /etc/udev/rules.d/99-babylonpiles.rules << EOF
# Auto-mount external drives for BabylonPiles
KERNEL=="sd[a-z][0-9]", SUBSYSTEM=="block", RUN+="/usr/local/bin/babylonpiles-mount.sh %k"
EOF
    
    # Create mount script
    cat > /usr/local/bin/babylonpiles-mount.sh << 'EOF'
#!/bin/bash
# Auto-mount script for BabylonPiles

DEVICE=$1
MOUNT_POINT="/mnt/external"

# Wait a moment for device to be ready
sleep 2

# Check if device exists and is not already mounted
if [ -b "/dev/$DEVICE" ] && ! mountpoint -q "$MOUNT_POINT"; then
    # Try to mount
    mount "/dev/$DEVICE" "$MOUNT_POINT" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo "Mounted /dev/$DEVICE to $MOUNT_POINT"
        
        # Create symlink to data directory
        ln -sf "$MOUNT_POINT" /mnt/babylonpiles
    fi
fi
EOF
    
    chmod +x /usr/local/bin/babylonpiles-mount.sh
}

# Setup network (WiFi hotspot)
setup_network() {
    log "Setting up network configuration..."
    
    # Configure hostapd
    cat > /etc/hostapd/hostapd.conf << EOF
# BabylonPiles WiFi Hotspot Configuration
interface=wlan0
driver=nl80211
ssid=BabylonPiles
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=babylonpiles123
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF
    
    # Configure dnsmasq
    cat > /etc/dnsmasq.conf << EOF
# BabylonPiles DNS/DHCP Configuration
interface=wlan0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
dhcp-option=3,192.168.4.1
dhcp-option=6,192.168.4.1
server=8.8.8.8
server=8.8.4.4
EOF
    
    # Enable services
    systemctl enable hostapd
    systemctl enable dnsmasq
}

# Install Python dependencies
install_python_deps() {
    log "Installing Python dependencies..."
    
    # Create virtual environment
    python3 -m venv "$BABYLONPILES_DIR/venv"
    
    # Activate virtual environment and install dependencies
    source "$BABYLONPILES_DIR/venv/bin/activate"
    pip install --upgrade pip
    
    # Install from requirements.txt
    if [ -f "backend/requirements.txt" ]; then
        pip install -r backend/requirements.txt
    else
        warn "requirements.txt not found, installing basic dependencies"
        pip install fastapi uvicorn sqlalchemy aiofiles psutil requests
    fi
}

# Setup systemd service
setup_service() {
    log "Setting up systemd service..."
    
    cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=BabylonPiles Offline Knowledge NAS
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$BABYLONPILES_DIR/backend
Environment=PATH=$BABYLONPILES_DIR/venv/bin
ExecStart=$BABYLONPILES_DIR/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable $SERVICE_NAME
}

# Setup firewall
setup_firewall() {
    log "Setting up firewall..."
    
    # Allow SSH
    ufw allow ssh
    
    # Allow web interface
    ufw allow 8080/tcp
    
    # Allow local network
    ufw allow from 192.168.4.0/24
    
    # Enable firewall
    ufw --force enable
}

# Create initial configuration
create_config() {
    log "Creating initial configuration..."
    
    # Create .env file
    cat > "$BABYLONPILES_DIR/backend/.env" << EOF
# BabylonPiles Configuration
DEBUG=false
HOST=0.0.0.0
PORT=8080
DATABASE_URL=sqlite:///babylonpiles.db
SECRET_KEY=$(openssl rand -hex 32)
DATA_DIR=$DATA_DIR
PILES_DIR=$DATA_DIR/piles
TEMP_DIR=/tmp/babylonpiles
WIFI_SSID=BabylonPiles
WIFI_PASSWORD=babylonpiles123
DEFAULT_MODE=store
AUTO_UPDATE_ENABLED=false
EOF
    
    chown "$SERVICE_USER:$SERVICE_USER" "$BABYLONPILES_DIR/backend/.env"
}

# Setup logging
setup_logging() {
    log "Setting up logging..."
    
    # Create log directory
    mkdir -p /var/log/babylonpiles
    chown "$SERVICE_USER:$SERVICE_USER" /var/log/babylonpiles
    
    # Configure logrotate
    cat > /etc/logrotate.d/babylonpiles << EOF
/var/log/babylonpiles/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 $SERVICE_USER $SERVICE_USER
}
EOF
}

# Final setup steps
final_setup() {
    log "Performing final setup steps..."
    
    # Set proper permissions
    chown -R "$SERVICE_USER:$SERVICE_USER" "$BABYLONPILES_DIR"
    
    # Create initial database
    su - "$SERVICE_USER" -c "cd $BABYLONPILES_DIR/backend && python -c 'from app.core.database import init_db; import asyncio; asyncio.run(init_db())'"
    
    # Start service
    systemctl start $SERVICE_NAME
    
    log "Setup completed successfully!"
    log "BabylonPiles is now running at: http://localhost:8080"
    log "WiFi hotspot: BabylonPiles (password: babylonpiles123)"
    log "Service status: systemctl status $SERVICE_NAME"
}

# Main setup function
main() {
    log "Starting BabylonPiles setup..."
    
    check_root
    update_system
    install_dependencies
    create_user
    setup_storage
    setup_network
    install_python_deps
    setup_service
    setup_firewall
    create_config
    setup_logging
    final_setup
    
    log "BabylonPiles setup completed successfully!"
    log "Check the log file at: $LOG_FILE"
}

# Run main function
main "$@" 