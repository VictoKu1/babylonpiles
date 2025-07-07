# API Documentation

## Access

The API is available at http://localhost:8080 when running with Docker Compose.

## Interactive Documentation

Visit http://localhost:8080/docs for interactive API documentation with:
- All available endpoints
- Request/response examples
- Try-it-out functionality

## Key Endpoints

- **Storage Status**: `GET /api/v1/storage/status`
- **Storage Drives**: `GET /api/v1/storage/drives`
- **Scan Drives**: `POST /api/v1/storage/drives/scan`

## Authentication

Most endpoints require authentication. Use the login endpoint to get a token 