# Installation

## Prerequisites

- Docker (with Docker Compose support)

## Quick Start

### 1. Clone and Start
```bash
git clone https://github.com/VictoKu1/babylonpiles.git
cd babylonpiles
docker-compose up -d
```

### 2. Access Services
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8080
- **API Docs**: http://localhost:8080/docs

## Management Commands

```bash
docker-compose down           # Stop services
docker-compose restart        # Restart services
docker-compose logs -f        # View logs
docker-compose up --build -d  # Rebuild and start
```

## Storage Configuration

By default, BabylonPiles uses `./storage/info` in the current directory.

To add more drives, edit `docker-compose.yml`:

**Windows:**
```yaml
storage:
  volumes:
    - ./storage/info:/mnt/hdd1  # Default
    - D:\:/mnt/hdd2
    - E:\:/mnt/hdd3
  environment:
    - MAX_DRIVES=3  # Match number of drives
```

**Linux:**
```yaml
storage:
  volumes:
    - ./storage/info:/mnt/hdd1  # Default
    - /media/hdd1:/mnt/hdd2
    - /mnt/storage:/mnt/hdd3
  environment:
    - MAX_DRIVES=3  # Match number of drives
```

Then restart: `docker-compose down && docker-compose up -d`

## Raspberry Pi Setup

BabylonPiles is optimized for Raspberry Pi and includes WiFi hotspot functionality. Follow these steps to set up your Raspberry Pi for optimal performance.

### Prerequisites

1. **Raspberry Pi OS** (Raspbian) with desktop environment
2. **WiFi adapter** (built-in or USB)
3. **Internet connection** for initial setup
4. **Docker and Docker Compose** installed

### System Requirements Installation

Install the required packages for WiFi hotspot functionality:

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required packages for WiFi hotspot
sudo apt install -y hostapd dnsmasq iw

# Install Docker (if not already installed)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install -y python3-pip
sudo pip3 install docker-compose

# Reboot to apply changes
sudo reboot
```

### WiFi Hotspot Configuration

After reboot, configure your WiFi interface:

```bash
# Check available WiFi interfaces
iwconfig

# Configure WiFi interface (replace wlan0 with your interface)
sudo nano /etc/dhcpcd.conf

# Add these lines at the end:
interface wlan0
static ip_address=192.168.4.1/24
nohook wpa_supplicant
```

### Enable Required Services

```bash
# Stop services that might interfere
sudo systemctl stop wpa_supplicant
sudo systemctl stop dhcpcd

# Configure hostapd
sudo nano /etc/hostapd/hostapd.conf

# Add this configuration:
interface=wlan0
driver=nl80211
ssid=BabylonPiles
hw_mode=g
channel=6
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=babylon123
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP

# Configure hostapd to use this file
sudo nano /etc/default/hostapd

# Add this line:
DAEMON_CONF="/etc/hostapd/hostapd.conf"

# Configure dnsmasq
sudo nano /etc/dnsmasq.conf

# Add this configuration:
interface=wlan0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
dhcp-option=3,192.168.4.1
dhcp-option=6,192.168.4.1
log-queries
log-dhcp

# Enable services
sudo systemctl enable hostapd
sudo systemctl enable dnsmasq
```

### Network Configuration

```bash
# Configure network interfaces
sudo nano /etc/network/interfaces

# Add these lines:
auto lo
iface lo inet loopback

auto eth0
iface eth0 inet dhcp

auto wlan0
iface wlan0 inet static
    address 192.168.4.1
    netmask 255.255.255.0
    network 192.168.4.0
    broadcast 192.168.4.255
```

### Firewall Configuration

```bash
# Install and configure UFW firewall
sudo apt install -y ufw

# Allow SSH, HTTP, and hotspot traffic
sudo ufw allow ssh
sudo ufw allow 3000
sudo ufw allow 8080
sudo ufw allow from 192.168.4.0/24

# Enable firewall
sudo ufw enable
```

### Performance Optimization

```bash
# Overclock settings (optional - for better performance)
sudo nano /boot/config.txt

# Add these lines:
over_voltage=2
arm_freq=1400
gpu_freq=500

# GPU memory split (adjust based on your needs)
gpu_mem=128

# Enable hardware acceleration
sudo nano /boot/config.txt

# Add these lines:
dtoverlay=vc4-kms-v3d
max_framebuffers=2
```

### Storage Setup

For optimal storage performance on Raspberry Pi:

```bash
# Create storage directories
sudo mkdir -p /mnt/babylonpiles/data
sudo mkdir -p /mnt/babylonpiles/piles
sudo mkdir -p /tmp/babylonpiles

# Set permissions
sudo chown -R $USER:$USER /mnt/babylonpiles
sudo chmod -R 755 /mnt/babylonpiles

# If using external storage
sudo mkdir -p /mnt/external
sudo mount /dev/sda1 /mnt/external  # Adjust device as needed
```

### Docker Configuration

```bash
# Create docker-compose override for Raspberry Pi
nano docker-compose.override.yml

# Add this configuration:
version: '3.8'
services:
  backend:
    environment:
      - PYTHONUNBUFFERED=1
    volumes:
      - /mnt/babylonpiles/data:/mnt/babylonpiles/data
      - /mnt/babylonpiles/piles:/mnt/babylonpiles/piles
      - /tmp/babylonpiles:/tmp/babylonpiles
    devices:
      - /dev/vchiq:/dev/vchiq  # For hardware acceleration
    privileged: true  # Required for WiFi hotspot
    network_mode: host  # For better network performance

  storage:
    volumes:
      - /mnt/babylonpiles/data:/mnt/hdd1
      - /mnt/external:/mnt/hdd2  # If using external storage
    environment:
      - MAX_DRIVES=2
```

### Final Setup Steps

```bash
# Clone and start BabylonPiles
git clone https://github.com/VictoKu1/babylonpiles.git
cd babylonpiles

# Start services
docker-compose up -d

# Check service status
docker-compose ps
docker-compose logs -f

# Test hotspot functionality
curl http://localhost:8080/api/v1/system/hotspot/requirements
```

### Troubleshooting Raspberry Pi

**WiFi Hotspot Issues:**
```bash
# Check WiFi interface
iwconfig
ip addr show wlan0

# Restart network services
sudo systemctl restart networking
sudo systemctl restart hostapd
sudo systemctl restart dnsmasq

# Check service status
sudo systemctl status hostapd
sudo systemctl status dnsmasq

# View logs
sudo journalctl -u hostapd -f
sudo journalctl -u dnsmasq -f
```

**Performance Issues:**
```bash
# Monitor system resources
htop
df -h
free -h

# Check Docker resource usage
docker stats

# Optimize Docker settings
sudo nano /etc/docker/daemon.json

# Add these settings:
{
  "storage-driver": "overlay2",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

**Storage Issues:**
```bash
# Check disk space
df -h

# Clean up Docker
docker system prune -a

# Check storage permissions
ls -la /mnt/babylonpiles/
```

### Recommended Hardware

- **Raspberry Pi 4** (4GB or 8GB RAM recommended)
- **Class 10 SD card** (32GB minimum, 64GB+ recommended)
- **External USB 3.0 storage** for content
- **USB WiFi adapter** (if not using built-in WiFi)
- **Active cooling** for sustained performance

### Security Considerations

```bash
# Change default passwords
sudo passwd pi
sudo passwd root

# Update SSH configuration
sudo nano /etc/ssh/sshd_config

# Set these options:
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes

# Restart SSH
sudo systemctl restart ssh
```

## Troubleshooting

- **Port conflicts**: Ensure ports 8080 and 3000 are free
- **Permission issues**: Run Docker as administrator (Windows) or add user to docker group (Linux)
- **Services not starting**: Check logs with `docker-compose logs -f`
- **WiFi hotspot not working**: Check hostapd and dnsmasq services
- **Performance issues**: Monitor system resources and optimize Docker settings

---

## FAQ

**Q: Can I run BabylonPiles without Docker?**
A: No. Docker Compose is now the only supported way to run BabylonPiles. This ensures a consistent, cross-platform experience.

**Q: How do I update the app?**
A: Pull the latest code and re-run `docker-compose up --build -d`.

---

For more details, see the [README.md](../README.md), [Storage Guide](STORAGE.md), or [API documentation](API.md). 