# API Documentation

## Access

The API is available at http://localhost:8080 when running with Docker Compose.

## Interactive Documentation

Visit http://localhost:8080/docs for interactive API documentation with:
- All available endpoints
- Request/response examples
- Try-it-out functionality
- Authentication testing

## Key Endpoints

### System Management
- **System Status**: `GET /api/v1/system/status`
- **System Metrics**: `GET /api/v1/system/metrics`
- **Mode Management**: `POST /api/v1/system/mode`

### Storage Management
- **Storage Status**: `GET /api/v1/storage/status`
- **Storage Drives**: `GET /api/v1/storage/drives`
- **Scan Drives**: `POST /api/v1/storage/drives/scan`

### File Management
- **List Files**: `GET /api/v1/files`
- **Upload Files**: `POST /api/v1/files/upload`
- **Download Files**: `GET /api/v1/files/download/{file_id}`
- **Move Files**: `POST /api/v1/files/move`
- **Delete Files**: `DELETE /api/v1/files/{file_id}`

### Pile Management
- **List Piles**: `GET /api/v1/piles`
- **Create Pile**: `POST /api/v1/piles`
- **Update Pile**: `PUT /api/v1/piles/{pile_id}`
- **Delete Pile**: `DELETE /api/v1/piles/{pile_id}`
- **Download Pile**: `POST /api/v1/piles/{pile_id}/download`

### Authentication
- **Login**: `POST /api/v1/auth/login`
- **Logout**: `POST /api/v1/auth/logout`
- **Refresh Token**: `POST /api/v1/auth/refresh`

### Updates
- **List Updates**: `GET /api/v1/updates`
- **Create Update**: `POST /api/v1/updates`
- **Update Status**: `GET /api/v1/updates/{update_id}/status`

## Storage System

BabylonPiles uses Docker volumes for storage, which provides:
- **Fast access** without bind mount overhead
- **Persistent data** across container restarts
- **Easy management** via access script

### Data Access

Use the provided access script to manage Docker volume data:
- **Linux/macOS**: `./access_storage.sh`
- **Windows**: Use Git Bash, WSL, or PowerShell with Docker commands

### Volume Information

The system uses four main Docker volumes:
- `babylonpiles_data`: Backend data (SQLite database, logs)
- `babylonpiles_piles`: ZIM files and other pile content
- `babylonpiles_storage`: Storage service data and metadata
- `babylonpiles_service_data`: Storage service internal data

## Authentication

Most endpoints require authentication. Use the login endpoint to get a JWT token:

```bash
curl -X POST "http://localhost:8080/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'
```

Include the token in subsequent requests:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8080/api/v1/system/status"
```

## Response Format

All API responses follow a consistent format:

```json
{
  "status": "success",
  "data": {
    // Response data
  },
  "message": "Optional message"
}
```

## Error Handling

Errors return appropriate HTTP status codes and error details:

```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field": "error description"
    }
  }
}
```

## Rate Limiting

API requests are rate-limited to prevent abuse. Check response headers for rate limit information.

## WebSocket Support

Real-time updates are available via WebSocket connections for:
- System status changes
- Download progress updates
- File operation notifications

Connect to: `ws://localhost:8080/ws` 