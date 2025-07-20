# Storage

## Overview

BabylonPiles uses a distributed storage system that can manage multiple drives. Files are automatically chunked and distributed across available drives.

## Download Functionality

### Overview

BabylonPiles includes robust download functionality for acquiring content from various sources (HTTP, Kiwix, Torrent). The system ensures reliable downloads with real-time progress tracking and comprehensive error handling.

### Download Process

#### 1. Download Initiation
- Downloads are initiated from the Piles page
- System prevents duplicate downloads of the same content
- Downloads use temporary files during transfer to prevent corruption

#### 2. Progress Tracking
- Real-time progress updates every 512KB
- Progress bars displayed in Browse and Piles sections
- Dashboard shows currently downloading piles
- 2-second polling for status updates

#### 3. Completion Verification
- Downloads use temporary files (.tmp extension) during transfer
- Files are only moved to final location after successful completion
- System verifies file integrity before marking as complete
- Failed downloads are automatically cleaned up

### Download Sources

#### HTTP/HTTPS Downloads
- Direct file downloads from web URLs
- Supports large files with timeout handling
- Progress tracking with content-length headers

#### Kiwix Downloads
- ZIM file downloads from Kiwix repositories
- Automatic metadata extraction
- Optimized for offline content

#### Torrent Downloads
- BitTorrent protocol support
- Uses transmission-cli for torrent handling
- Automatic file discovery and organization

### User Interface

#### Browse Files Section
- Shows download progress indicators for active downloads
- Pulsing download icons for visual feedback
- Progress bars with percentage completion
- Real-time updates every 2 seconds

#### Piles Page
- Download buttons show current status
- Prevents duplicate download attempts
- Real-time progress updates
- Enhanced error messaging

#### Dashboard
- Currently downloading section
- Progress tracking for active downloads
- Storage usage statistics
- System status indicators

### Error Handling

#### Download Failures
- Automatic cleanup of temporary files
- Status reset on failure
- User-friendly error messages
- Retry mechanisms for network issues

#### Network Interruptions
- Timeout handling (1 hour for large files)
- Partial download detection
- Automatic retry on connection loss
- Progress preservation where possible

#### File Integrity
- Download size verification
- File existence checks
- Format validation
- Metadata verification

### API Endpoints

#### Download Management
- `POST /api/v1/piles/{pile_id}/download-source` - Start download
- `GET /api/v1/files/download-status` - Get download status
- `GET /api/v1/piles/{pile_id}` - Get pile status

#### File Operations
- `GET /api/v1/files` - List files
- `GET /api/v1/files/download` - Download file
- `GET /api/v1/files/view/{file_path}` - View file info

### Configuration

#### Timeout Settings
```yaml
download:
  timeout: 3600  # 1 hour timeout for large files
  chunk_size: 8192  # 8KB chunks for progress tracking
  progress_interval: 524288  # 512KB progress updates
```

#### Storage Settings
```yaml
storage:
  temp_dir: ./temp  # Temporary download directory
  data_dir: ./data  # Final file storage directory
  cleanup_on_failure: true  # Auto-cleanup failed downloads
```

### Troubleshooting

#### Common Issues

**Downloads stopping unexpectedly:**
- Check network connectivity
- Verify source URL accessibility
- Review system logs for errors
- Ensure sufficient disk space

**Incomplete downloads:**
- System automatically cleans up partial files
- Check storage permissions
- Verify source file integrity
- Review download logs

**Progress not updating:**
- Refresh the page to reconnect
- Check browser console for errors
- Verify API endpoint accessibility
- Restart the application if needed

#### Logs and Debugging

```bash
# View download logs
docker-compose logs backend

# Check storage status
curl http://localhost:8080/api/v1/storage/status

# Monitor download progress
curl http://localhost:8080/api/v1/files/download-status
```

### File Permissions

#### Public/Private Access Control

BabylonPiles includes a permission system that allows users to control access to files and folders. Each file and folder can be marked as either public or private.

#### Permission Features

**Default Behavior:**
- All new files and folders are private by default
- Private files are only accessible to the owner
- Public files can be accessed by other users

**Permission Management:**
- Toggle permissions directly from the file browser
- Visual indicators show current permission status
- Permissions are stored in a `.permissions.json` file
- Changes take effect immediately

#### User Interface

**File Browser:**
- Permission toggle switches on each file/folder row
- Visual icons: 🌐 for public, 🔒 for private
- Hover tooltips show current status and action
- Click to toggle between public and private

**Permission Indicators:**
- **Public (🌐)**: File/folder is accessible to other users
- **Private (🔒)**: File/folder is only accessible to owner
- Hover effects provide visual feedback
- Smooth transitions when toggling

#### API Endpoints

**Get Permission Status:**
```bash
GET /api/v1/files/permission/{file_path}
```

**Set Permission:**
```bash
POST /api/v1/files/permission/{file_path}
Content-Type: application/x-www-form-urlencoded

is_public=true
```

**Toggle Permission:**
```bash
POST /api/v1/files/permission/{file_path}/toggle
```

#### Usage Examples

**Making a file public:**
1. Navigate to the file in the browser
2. Click the 🔒 icon next to the file
3. Icon changes to 🌐 indicating public access
4. File is now accessible to other users

**Making a folder private:**
1. Navigate to the folder in the browser
2. Click the 🌐 icon next to the folder
3. Icon changes to 🔒 indicating private access
4. Folder and contents are now private

**Bulk permission management:**
- Permissions are inherited by default
- Child files/folders can have different permissions
- Parent folder permissions don't override child permissions

#### Security Considerations

**Permission Storage:**
- Permissions stored in `.permissions.json` file
- File is hidden from normal browsing
- JSON format for easy backup and restore
- Automatic cleanup when files are deleted

**Access Control:**
- Private files are completely hidden from other users
- Public files appear in shared listings
- No intermediate permission levels (only public/private)
- Permissions apply to both files and folders

**Best Practices:**
- Use private for personal or sensitive content
- Use public for shared resources and collaboration
- Regularly review and update permissions
- Consider folder-level permissions for organization

### File Metadata

#### Information Tracking

BabylonPiles tracks comprehensive metadata for all files and folders, providing administrators with detailed information about content creation and modification.

#### Metadata Features

**Tracked Information:**
- **Creator**: Who added the file/folder
- **Creation Date**: When the file/folder was created
- **Modification Date**: When the file/folder was last modified
- **File Size**: Size in bytes and human-readable format
- **File Type**: Extension and MIME type information
- **Permissions**: Current public/private status
- **System Info**: Inode, device, and other system details

**Metadata Storage:**
- Stored in `.metadata.json` file
- Hidden from normal file browsing
- JSON format for easy backup and restore
- Automatic cleanup when files are deleted

#### User Interface

**Information Button:**
- ℹ️ icon on each file/folder row
- Click to view detailed metadata
- Modal popup with comprehensive information
- Organized sections for different data types

**Metadata Modal Sections:**
- **Basic Information**: Name, type, size, access status
- **Creator Information**: Who created, when created/modified
- **File Details**: Extension, MIME type (files only)
- **Permissions**: Read/write permissions for owner and public
- **System Information**: Inode, device numbers

#### API Endpoints

**Get File Metadata:**
```bash
GET /api/v1/files/metadata/{file_path}
```

**Response Example:**
```json
{
  "success": true,
  "data": {
    "path": "example.txt",
    "name": "example.txt",
    "is_dir": false,
    "is_public": false,
    "size": 1024,
    "size_formatted": "1.0 KB",
    "creator": "admin",
    "created_at": "2024-01-15T10:30:00",
    "created_ago": "2 days ago",
    "modified_at": "2024-01-15T10:30:00",
    "modified_ago": "2 days ago",
    "permissions": {
      "owner_read": true,
      "owner_write": true,
      "owner_execute": false,
      "public_read": false,
      "public_write": false
    },
    "file_info": {
      "extension": ".txt",
      "mime_type": "text/plain",
      "inode": 12345,
      "device": 67890
    }
  }
}
```

#### Usage Examples

**Viewing File Information:**
1. Navigate to the file in the browser
2. Click the ℹ️ icon next to the file
3. View detailed metadata in the modal
4. Close modal when finished

**Administrator Features:**
- Track who created each file/folder
- Monitor creation and modification dates
- View file permissions and access status
- Check system-level file information
- Export metadata for reporting

**Metadata Management:**
- Automatic tracking for new files/folders
- Creator information stored with each item
- Timestamp tracking for audit trails
- Permission status integration
- System information for troubleshooting

#### Security and Privacy

**Metadata Access:**
- Only administrators can view detailed metadata
- Creator information helps with accountability
- Timestamps provide audit trail
- Permission tracking ensures access control

**Data Retention:**
- Metadata persists with files
- Automatic cleanup on file deletion
- Backup-friendly JSON format
- No sensitive data in metadata

### WiFi Hotspot

#### Overview

BabylonPiles includes a built-in WiFi hotspot feature that allows devices to connect and access public content. This feature is designed to work on any system with WiFi capabilities, with Raspberry Pi being a common and well-suited use case. The hotspot provides a secure way to share content without requiring internet connectivity.

#### Cross-Platform Support

**Supported Systems:**
- **Raspberry Pi**: Primary target platform, excellent performance
- **Linux**: Full support on most distributions
- **macOS**: Limited support (requires additional setup)
- **Windows**: Limited support (requires WSL or similar)

**System Requirements:**
- WiFi interface (USB or built-in)
- hostapd package
- dnsmasq package
- Root privileges for network configuration
- Linux-based system (recommended)

#### Hotspot Features

**Network Configuration:**
- **SSID**: BabylonPiles (configurable)
- **Password**: babylon123 (configurable)
- **IP Range**: 192.168.4.0/24
- **Channel**: 6 (configurable)
- **Security**: WPA2-PSK
- **Gateway**: 192.168.4.1

**Automatic Detection:**
- WiFi interface auto-detection
- System requirement validation
- Platform-specific configuration
- Error handling and recovery

**Device Management:**
- Real-time connected device tracking
- MAC address and IP address logging
- Connection timestamp recording
- Device hostname detection
- Multiple detection methods (DHCP leases, ARP table)

#### Administrator Interface

**Dashboard Integration:**
- Hotspot start/stop controls
- Real-time status monitoring
- Connected device list
- Pending upload requests
- Network information display

**Hotspot Controls:**
- One-click start/stop
- Status indicators
- Error handling and recovery
- Process monitoring

**Device Monitoring:**
- Connected device count
- Device information display
- Connection timestamps
- IP and MAC address tracking

#### Upload Request System

**Request Process:**
1. Device connects to hotspot
2. User submits upload request with name
3. Request appears in admin dashboard
4. Administrator reviews and approves/rejects
5. User receives notification of decision

**Request Information:**
- **Filename**: Requested file name
- **Editor Name**: Person requesting upload
- **Client IP**: Device IP address
- **Client MAC**: Device MAC address
- **Request Timestamp**: When request was made
- **Status**: Pending/Approved/Rejected

**Administrator Actions:**
- **Approve**: Allow file upload
- **Reject**: Deny with optional reason
- **View Details**: See full request information
- **Bulk Actions**: Handle multiple requests

#### Client Interface

**Public Content Browser:**
- List of all public files and folders
- File size and type information
- Creator and creation date
- Direct download links

**Upload Request Form:**
- Simple file name input
- User name/identifier
- Request submission
- Status tracking

**User Experience:**
- Clean, mobile-friendly interface
- No authentication required
- Instant feedback
- Error handling

#### API Endpoints

**Hotspot Management:**
```bash
POST /api/v1/hotspot/start          # Start hotspot
POST /api/v1/hotspot/stop           # Stop hotspot
GET  /api/v1/hotspot/status         # Get status
```

**Content Access:**
```bash
GET  /api/v1/hotspot/public-content # List public files
GET  /api/v1/hotspot/download/{file} # Download file
```

**Upload Requests:**
```bash
POST /api/v1/hotspot/request-upload # Submit request
POST /api/v1/hotspot/approve-request/{id} # Approve request
POST /api/v1/hotspot/reject-request/{id}  # Reject request
```

#### Usage Examples

**Starting the Hotspot:**
1. Navigate to Dashboard
2. Click "Start Hotspot" button
3. Wait for confirmation
4. Share SSID and password with users

**Managing Upload Requests:**
1. View pending requests in Dashboard
2. Click "Approve" or "Reject" for each request
3. Provide rejection reason if needed
4. Monitor request status

**Client Access:**
1. Connect to "BabylonPiles" WiFi network
2. Enter password: "babylon123"
3. Open browser to hotspot IP
4. Browse public content or request uploads

#### Security Considerations

**Network Security:**
- WPA2 encryption
- Isolated network segment
- No internet access by default
- Controlled content access

**Access Control:**
- Public content only
- No direct file uploads
- Administrator approval required
- Request tracking and logging

**Privacy Protection:**
- Device information logging
- Request audit trail
- No personal data collection
- Secure request handling

#### Configuration

**Hotspot Settings:**
```python
HOTSPOT_CONFIG = {
    "ssid": "BabylonPiles",
    "password": "babylon123",
    "interface": "wlan0",
    "channel": "6",
    "ip_range": "192.168.4.0/24"
}
```

**System Requirements:**
- WiFi interface support
- hostapd package
- dnsmasq package
- Root privileges for network configuration

#### Troubleshooting

**Common Issues:**
- **Hotspot won't start**: Check WiFi interface and permissions
- **No devices connect**: Verify SSID and password
- **No internet access**: Normal behavior for security
- **Upload requests not appearing**: Check API connectivity

**Debug Steps:**
1. Check hotspot status in Dashboard
2. Verify WiFi interface is available
3. Test API endpoints directly
4. Check system logs for errors

#### System Compatibility

**Raspberry Pi (Recommended):**
- **Hardware**: Built-in WiFi or USB WiFi adapter
- **OS**: Raspberry Pi OS, Ubuntu, other Linux distributions
- **Installation**: `sudo apt-get install hostapd dnsmasq`
- **Performance**: Excellent, low power consumption
- **Use Cases**: Portable content sharing, offline access points

**Linux Systems:**
- **Distributions**: Ubuntu, Debian, CentOS, Fedora, Arch Linux
- **Hardware**: Any WiFi-capable system
- **Installation**: Platform-specific package managers
- **Performance**: Good to excellent depending on hardware
- **Use Cases**: Server deployments, desktop sharing

**macOS Systems:**
- **Limitations**: Requires additional setup and tools
- **Hardware**: Built-in WiFi or USB adapter
- **Installation**: `brew install hostapd dnsmasq`
- **Performance**: Limited by macOS networking restrictions
- **Use Cases**: Development and testing

**Windows Systems:**
- **Limitations**: Requires WSL or virtualization
- **Hardware**: WiFi adapter with Linux driver support
- **Installation**: Install Linux subsystem first
- **Performance**: Limited by virtualization overhead
- **Use Cases**: Development and testing only

**System Detection:**
- **WiFi Interface**: Auto-detects wlan0, wlan1, wlp2s0, etc.
- **Requirements**: Validates hostapd, dnsmasq, root privileges
- **Configuration**: Platform-specific network setup
- **Error Handling**: Graceful fallbacks and user feedback

#### Installation Guide

**Raspberry Pi Setup:**
```bash
# Update system
sudo apt update && sudo apt upgrade

# Install required packages
sudo apt install hostapd dnsmasq

# Configure WiFi interface
sudo raspi-config  # Enable WiFi if needed

# Start BabylonPiles with hotspot support
sudo python3 main.py
```

**Linux Setup:**
```bash
# Ubuntu/Debian
sudo apt install hostapd dnsmasq

# CentOS/RHEL
sudo yum install hostapd dnsmasq

# Arch Linux
sudo pacman -S hostapd dnsmasq

# Start BabylonPiles
sudo python3 main.py
```

**macOS Setup:**
```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required packages
brew install hostapd dnsmasq

# Note: Additional configuration may be required
```

**System Requirements Check:**
- Dashboard includes "System Requirements" button
- Validates all required components
- Provides installation instructions
- Shows platform-specific recommendations

#### User Personalization

**User Name Configuration:**
- **Personalized Hotspot**: Users can set their name to customize the hotspot SSID
- **Naming Convention**: `{UserName}BabylonPiles` (e.g., "JamesBabylonPiles")
- **Dashboard Display**: User name appears in the top-left corner of the dashboard
- **Configuration Button**: Gear icon (⚙️) next to the user name for easy access

**User Interface:**
- **Configuration Modal**: Simple form to enter user name
- **Validation**: Names are cleaned and validated automatically
- **Character Limits**: Maximum 20 characters, alphanumeric only
- **Real-time Preview**: Shows how the hotspot will be named

**API Endpoints:**
```bash
GET  /api/v1/user/config     # Get current user configuration
POST /api/v1/user/config     # Update user name
```

**Configuration Features:**
- **Name Cleaning**: Removes special characters and spaces
- **Length Truncation**: Automatically limits to 20 characters
- **Validation**: Ensures names contain valid characters
- **Persistence**: Configuration saved to file and persists across restarts

**Example Usage:**
1. Click the gear icon (⚙️) next to the user name in dashboard
2. Enter your name (e.g., "James")
3. Click "Update Name"
4. Hotspot will be named "JamesBabylonPiles"
5. Other users can easily identify your hotspot

#### Network Isolation

**Content-Only Access:**
- **No Internet**: Hotspot provides access to local content only
- **Isolated Network**: Connected devices cannot access external internet
- **Content Sharing**: Users can browse and download public files
- **Secure Access**: WPA2 encryption with controlled permissions

**Network Configuration:**
- **IP Range**: 192.168.4.0/24 (isolated subnet)
- **Gateway**: 192.168.4.1 (BabylonPiles system)
- **DHCP**: Automatic IP assignment for connected devices
- **DNS**: Local resolution only, no external queries

**Security Features:**
- **WPA2-PSK**: Strong encryption for network access
- **Content Permissions**: Public/private file access control
- **Request Approval**: Upload requests require administrator approval
- **Device Tracking**: Logs connected devices for monitoring 