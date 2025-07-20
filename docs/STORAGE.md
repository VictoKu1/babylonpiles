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

## Configuration

### Default Setup

BabylonPiles uses `./storage/info` in the current directory by default:

```yaml
storage:
  volumes:
    - ./storage/info:/mnt/hdd1
  environment:
    - MAX_DRIVES=1
```

### Add More Drives

Edit `docker-compose.yml` and add your drives:

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

Then restart:
```bash
docker-compose down
docker-compose up -d
```

## Management

### Web Interface

Access storage management at http://localhost:3000 → Storage

### API Endpoints

- **Status**: `GET /api/v1/storage/status`
- **Drives**: `GET /api/v1/storage/drives`
- **Scan**: `POST /api/v1/storage/drives/scan`

### Logs

```bash
docker-compose logs storage
```

## Troubleshooting

- **Drives not detected**: Check mount paths and permissions
- **MAX_DRIVES mismatch**: Ensure it matches the number of volume mounts
- **Permission errors**: Ensure Docker has access to the drives 