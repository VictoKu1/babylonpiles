# API Documentation

## Access

The API is available at http://localhost:8080 when running with Docker Compose.

## Interactive Documentation

Visit http://localhost:8080/docs for interactive API documentation with:
- All available endpoints
- Request/response examples
- Try-it-out functionality

## Key Endpoints

### File Management
- **List Files**: `GET /api/v1/files?path={path}`
- **Upload File**: `POST /api/v1/files/upload`
- **Download File**: `GET /api/v1/files/download?path={path}`
- **Delete File**: `DELETE /api/v1/files/delete?path={path}`
- **Move File**: `POST /api/v1/files/move`
- **Set Permission**: `POST /api/v1/files/permission/{file_path:path}`
- **Toggle Permission**: `POST /api/v1/files/permission/{file_path:path}/toggle`

### Storage Management
- **Storage Status**: `GET /api/v1/storage/status`
- **Storage Drives**: `GET /api/v1/storage/drives`
- **Scan Drives**: `POST /api/v1/storage/drives/scan`

### System Management
- **System Metrics**: `GET /api/v1/system/metrics`
- **System Status**: `GET /api/v1/system/status`
- **System Mode**: `GET /api/v1/system/mode`

### Pile Management
- **List Piles**: `GET /api/v1/piles/`
- **Create Pile**: `POST /api/v1/piles/`
- **Update Pile**: `PUT /api/v1/piles/{pile_id}`
- **Delete Pile**: `DELETE /api/v1/piles/{pile_id}`

### User Management
- **User Config**: `GET /api/v1/system/user/config`
- **Update User Config**: `POST /api/v1/system/user/config`

### Hotspot Management
- **Hotspot Status**: `GET /api/v1/system/hotspot/status`
- **Start Hotspot**: `POST /api/v1/system/hotspot/start`
- **Stop Hotspot**: `POST /api/v1/system/hotspot/stop`
- **Hotspot Requirements**: `GET /api/v1/system/hotspot/requirements`

## Recent Improvements

### File Upload Enhancements
- **Drag and Drop Support**: Files can be uploaded via drag and drop from desktop to browser
- **Progress Tracking**: Upload progress is tracked and displayed to users
- **Error Handling**: Improved error messages and user feedback
- **Visual Feedback**: Upload overlays and progress indicators

### Permission Management
- **Toggle Permissions**: Easy toggle between public and private file permissions
- **Enhanced Error Handling**: Better error parsing and user-friendly notifications
- **Fixed Routing**: Resolved endpoint conflicts for permission operations
- **User-Friendly Messages**: Clear success and error notifications

### Dashboard Storage Accuracy
- **Content Storage Metrics**: Dashboard now shows actual content storage instead of system disk usage
- **Real-time Updates**: Storage metrics update automatically after file operations
- **Accurate Calculations**: File sizes are calculated correctly for dashboard display
- **Content vs System Storage**: Clear distinction between user content and system storage

### System Monitoring
- **Real-time Metrics**: CPU, memory, and disk usage monitoring
- **Storage Analytics**: Detailed storage reporting and analysis
- **Health Monitoring**: System status and performance tracking
- **Visual Indicators**: Progress bars and status indicators

## Authentication

Most endpoints require authentication. Use the login endpoint to get a token:

```bash
curl -X POST "http://localhost:8080/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'
```

## Error Handling

The API returns standardized error responses:

```json
{
  "detail": "Error message",
  "status_code": 400
}
```

### Common Error Codes
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

## Response Formats

### Success Response
```json
{
  "success": true,
  "data": {
    // Response data
  }
}
```

### Error Response
```json
{
  "success": false,
  "detail": "Error message"
}
```

## Rate Limiting

API requests are rate-limited to prevent abuse:
- **Default**: 100 requests per minute per IP
- **File Uploads**: 10 uploads per minute per user
- **System Operations**: 5 operations per minute per user

## Testing

Test the API using the provided test suite:

```bash
# Run all API tests
python tests/run_all_tests.py

# Run specific API tests
python tests/test_storage_api.py
python tests/test_permissions.py
```

## Examples

### Upload a File
```bash
curl -X POST "http://localhost:8080/api/v1/files/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/file.txt" \
  -F "path="
```

### Toggle File Permission
```bash
curl -X POST "http://localhost:8080/api/v1/files/permission/test.txt/toggle" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Get System Metrics
```bash
curl -X GET "http://localhost:8080/api/v1/system/metrics" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Move a File
```bash
curl -X POST "http://localhost:8080/api/v1/files/move" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source": "old/path.txt", "destination": "new/path.txt"}'
```

## WebSocket Support

Some endpoints support WebSocket connections for real-time updates:
- **File Upload Progress**: Real-time upload progress
- **System Metrics**: Live system monitoring
- **Storage Updates**: Real-time storage changes

## Security

- **JWT Authentication**: Secure token-based authentication
- **CORS Support**: Cross-origin resource sharing
- **Input Validation**: Comprehensive request validation
- **Error Sanitization**: Safe error message handling
- **Rate Limiting**: Protection against abuse

## Performance

- **Async Operations**: Non-blocking request handling
- **Connection Pooling**: Efficient database connections
- **Caching**: Response caching for frequently accessed data
- **Compression**: Gzip compression for large responses
- **Streaming**: File streaming for large uploads/downloads 