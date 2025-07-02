# BabylonPiles Installation Guide

This guide covers installation of BabylonPiles on different platforms and scenarios.

## Table of Contents

- [Raspberry Pi Installation](#raspberry-pi-installation)
- [Development Installation](#development-installation)
- [Docker Installation](#docker-installation)
- [Manual Installation](#manual-installation)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

## Quick Start (Raspberry Pi)

1. **Flash Raspberry Pi OS** and boot
2. **Clone and setup**:
   ```bash
   git clone https://github.com/VictoKu1/babylonpiles.git
   cd babylonpiles
   sudo chmod +x scripts/setup.sh
   sudo ./scripts/setup.sh
   ```
3. **Access**: http://raspberrypi.local:8080

## Development Setup

### Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Configuration

Create `.env` file in backend directory:
```bash
DEBUG=false
HOST=0.0.0.0
PORT=8080
DATABASE_URL=sqlite:///babylonpiles.db
SECRET_KEY=your-secret-key
DATA_DIR=/mnt/babylonpiles
PILES_DIR=/mnt/babylonpiles/piles
WIFI_SSID=BabylonPiles
WIFI_PASSWORD=babylonpiles123
DEFAULT_MODE=store
```

## System Requirements

- **OS**: Linux (Raspberry Pi OS, Ubuntu, Debian)
- **Python**: 3.8+
- **RAM**: 2GB minimum, 4GB recommended
- **Storage**: 10GB+ for system, additional for content
- **Network**: Ethernet or WiFi

## Troubleshooting

- Check service status: `systemctl status babylonpiles`
- View logs: `journalctl -u babylonpiles -f`
- Test API: `curl http://localhost:8080/health`

## Raspberry Pi Installation

### Prerequisites

- Raspberry Pi 3 or 4 (recommended: 4GB RAM or more)
- MicroSD card (32GB or larger, Class 10 recommended)
- External HDD/SSD (for data storage)
- Power supply
- Network connection (Ethernet or WiFi)

### Quick Installation

1. **Flash Raspberry Pi OS**
   ```bash
   # Download Raspberry Pi Imager
   # Flash Raspberry Pi OS Lite (64-bit recommended)
   ```

2. **Boot and configure Raspberry Pi**
   ```bash
   # Enable SSH, set hostname, configure WiFi if needed
   sudo raspi-config
   ```

3. **Clone BabylonPiles**
   ```bash
   git clone https://github.com/VictoKu1/babylonpiles.git
   cd babylonpiles
   ```

4. **Run automated setup**
   ```bash
   sudo chmod +x scripts/setup.sh
   sudo ./scripts/setup.sh
   ```

5. **Access the system**
   - Web interface: http://raspberrypi.local:8080
   - WiFi hotspot: Connect to "BabylonPiles" network (password: babylonpiles123)

### Manual Raspberry Pi Setup

If you prefer manual setup:

1. **Install system dependencies**
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install -y python3 python3-pip python3-venv git hostapd dnsmasq
   ```

2. **Setup storage**
   ```bash
   sudo mkdir -p /mnt/babylonpiles
   sudo chown $USER:$USER /mnt/babylonpiles
   ```

3. **Install Python dependencies**
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Configure network**
   ```bash
   # Edit /etc/hostapd/hostapd.conf
   # Edit /etc/dnsmasq.conf
   sudo systemctl enable hostapd dnsmasq
   ```

5. **Start the service**
   ```bash
   python main.py
   ```

## Development Installation

### Prerequisites

- Python 3.8+
- Node.js 16+ (for frontend)
- Git

### Backend Setup

1. **Clone repository**
   ```bash
   git clone https://github.com/VictoKu1/babylonpiles.git
   cd babylonpiles
   ```

2. **Setup Python environment**
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Initialize database**
   ```bash
   python -c "from app.core.database import init_db; import asyncio; asyncio.run(init_db())"
   ```

5. **Run development server**
   ```bash
   python main.py
   ```

### Frontend Setup

1. **Install Node.js dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Run development server**
   ```bash
   npm run dev
   ```

3. **Build for production**
   ```bash
   npm run build
   ```

## Docker Installation

### Using Docker Compose

1. **Create docker-compose.yml**
   ```yaml
   version: '3.8'
   services:
     babylonpiles:
       build: .
       ports:
         - "8080:8080"
       volumes:
         - ./data:/mnt/babylonpiles
         - ./config:/app/config
       environment:
         - DATA_DIR=/mnt/babylonpiles
         - DEBUG=false
       restart: unless-stopped
   ```

2. **Build and run**
   ```bash
   docker-compose up -d
   ```

### Using Docker directly

1. **Build image**
   ```bash
   docker build -t babylonpiles .
   ```

2. **Run container**
   ```bash
   docker run -d \
     --name babylonpiles \
     -p 8080:8080 \
     -v /path/to/data:/mnt/babylonpiles \
     babylonpiles
   ```

## Manual Installation

### System Requirements

- **OS**: Linux (Ubuntu 20.04+, Debian 11+, CentOS 8+)
- **Python**: 3.8+
- **RAM**: 2GB minimum, 4GB recommended
- **Storage**: 10GB minimum for system, additional for content
- **Network**: Ethernet or WiFi

### Step-by-Step Installation

1. **Install system dependencies**
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install -y python3 python3-pip python3-venv git sqlite3

   # CentOS/RHEL
   sudo yum install -y python3 python3-pip git sqlite
   ```

2. **Create service user**
   ```bash
   sudo useradd -r -s /bin/bash -d /opt/babylonpiles babylonpiles
   ```

3. **Setup directories**
   ```bash
   sudo mkdir -p /opt/babylonpiles /mnt/babylonpiles
   sudo chown babylonpiles:babylonpiles /opt/babylonpiles /mnt/babylonpiles
   ```

4. **Install application**
   ```bash
   sudo -u babylonpiles git clone https://github.com/VictoKu1/babylonpiles.git /opt/babylonpiles
   cd /opt/babylonpiles/backend
   sudo -u babylonpiles python3 -m venv venv
   sudo -u babylonpiles venv/bin/pip install -r requirements.txt
   ```

5. **Configure systemd service**
   ```bash
   sudo cp scripts/babylonpiles.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable babylonpiles
   ```

6. **Start service**
   ```bash
   sudo systemctl start babylonpiles
   ```

## Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```bash
# Application
DEBUG=false
HOST=0.0.0.0
PORT=8080

# Database
DATABASE_URL=sqlite:///babylonpiles.db

# Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Storage
DATA_DIR=/mnt/babylonpiles
PILES_DIR=/mnt/babylonpiles/piles
TEMP_DIR=/tmp/babylonpiles

# Network
WIFI_SSID=BabylonPiles
WIFI_PASSWORD=babylonpiles123

# Mode
DEFAULT_MODE=store
AUTO_UPDATE_ENABLED=false

# Content Sources
KIWIX_LIBRARY_URL=https://library.kiwix.org
OSM_PLANET_URL=https://planet.openstreetmap.org
```

### Network Configuration

#### WiFi Hotspot Setup

1. **Install hostapd and dnsmasq**
   ```bash
   sudo apt install -y hostapd dnsmasq
   ```

2. **Configure hostapd**
   ```bash
   sudo nano /etc/hostapd/hostapd.conf
   ```

   ```ini
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
   ```

3. **Configure dnsmasq**
   ```bash
   sudo nano /etc/dnsmasq.conf
   ```

   ```ini
   interface=wlan0
   dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
   dhcp-option=3,192.168.4.1
   dhcp-option=6,192.168.4.1
   server=8.8.8.8
   server=8.8.4.4
   ```

4. **Enable services**
   ```bash
   sudo systemctl enable hostapd dnsmasq
   sudo systemctl start hostapd dnsmasq
   ```

### Storage Configuration

#### Auto-mount External Drives

1. **Create mount point**
   ```bash
   sudo mkdir -p /mnt/external
   ```

2. **Add to fstab**
   ```bash
   echo "/dev/sda1 /mnt/external auto defaults,noatime 0 0" | sudo tee -a /etc/fstab
   ```

3. **Create symlink**
   ```bash
   sudo ln -sf /mnt/external /mnt/babylonpiles
   ```

## Troubleshooting

### Common Issues

#### Service won't start

1. **Check service status**
   ```bash
   sudo systemctl status babylonpiles
   sudo journalctl -u babylonpiles -f
   ```

2. **Check permissions**
   ```bash
   sudo chown -R babylonpiles:babylonpiles /opt/babylonpiles /mnt/babylonpiles
   ```

3. **Check Python environment**
   ```bash
   sudo -u babylonpiles /opt/babylonpiles/backend/venv/bin/python --version
   ```

#### Network issues

1. **Check WiFi interface**
   ```bash
   iwconfig
   ifconfig wlan0
   ```

2. **Check hostapd status**
   ```bash
   sudo systemctl status hostapd
   sudo journalctl -u hostapd -f
   ```

3. **Check firewall**
   ```bash
   sudo ufw status
   sudo ufw allow 8080/tcp
   ```

#### Storage issues

1. **Check disk space**
   ```bash
   df -h
   du -sh /mnt/babylonpiles/*
   ```

2. **Check mount points**
   ```bash
   mount | grep babylonpiles
   ls -la /mnt/babylonpiles
   ```

3. **Check permissions**
   ```bash
   ls -la /mnt/babylonpiles
   sudo chown -R babylonpiles:babylonpiles /mnt/babylonpiles
   ```

### Log Files

- **Application logs**: `/var/log/babylonpiles/`
- **System logs**: `/var/log/syslog`
- **Service logs**: `sudo journalctl -u babylonpiles`

### Getting Help

1. **Check the logs**
   ```bash
   sudo journalctl -u babylonpiles -f
   tail -f /var/log/babylonpiles/*.log
   ```

2. **Test the API**
   ```bash
   curl http://localhost:8080/health
   curl http://localhost:8080/api/v1/system/status
   ```

3. **Check system resources**
   ```bash
   htop
   df -h
   free -h
   ```

4. **Create issue on GitHub**
   - Include system information
   - Include relevant log files
   - Describe steps to reproduce

## Next Steps

After installation:

1. **Access the web interface** at http://localhost:8080
2. **Create your first pile** using the admin interface
3. **Switch to Learn mode** to download content
4. **Switch to Store mode** for offline access
5. **Configure automatic updates** if desired

For more information, see the [User Guide](USER_GUIDE.md) and [API Documentation](API.md). 