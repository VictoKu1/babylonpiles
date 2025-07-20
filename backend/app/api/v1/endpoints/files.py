from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse, HTMLResponse
import os
import json
from typing import List, Dict, Any
import urllib.parse
from datetime import datetime
from fastapi import status

router = APIRouter()

DATA_ROOT = "/mnt/babylonpiles/data"
PERMISSIONS_FILE = os.path.join(DATA_ROOT, ".permissions.json")
METADATA_FILE = os.path.join(DATA_ROOT, ".metadata.json")

def load_permissions() -> Dict[str, bool]:
    """Load file/folder permissions from the permissions file"""
    try:
        if os.path.exists(PERMISSIONS_FILE):
            with open(PERMISSIONS_FILE, 'r') as f:
                return json.load(f)
        return {}
    except Exception:
        return {}

def save_permissions(permissions: Dict[str, bool]):
    """Save file/folder permissions to the permissions file"""
    try:
        os.makedirs(os.path.dirname(PERMISSIONS_FILE), exist_ok=True)
        with open(PERMISSIONS_FILE, 'w') as f:
            json.dump(permissions, f, indent=2)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving permissions: {str(e)}"
        )

def load_metadata() -> Dict[str, Dict[str, Any]]:
    """Load file/folder metadata from the metadata file"""
    try:
        if os.path.exists(METADATA_FILE):
            with open(METADATA_FILE, 'r') as f:
                return json.load(f)
        return {}
    except Exception:
        return {}

def save_metadata(metadata: Dict[str, Dict[str, Any]]):
    """Save file/folder metadata to the metadata file"""
    try:
        os.makedirs(os.path.dirname(METADATA_FILE), exist_ok=True)
        with open(METADATA_FILE, 'w') as f:
            json.dump(metadata, f, indent=2)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving metadata: {str(e)}"
        )

def get_file_metadata(file_path: str) -> Dict[str, Any]:
    """Get metadata for a file or folder"""
    metadata = load_metadata()
    return metadata.get(file_path, {})

def set_file_metadata(file_path: str, metadata: Dict[str, Any]):
    """Set metadata for a file or folder"""
    all_metadata = load_metadata()
    all_metadata[file_path] = metadata
    save_metadata(all_metadata)

def update_file_metadata(file_path: str, creator: str = "admin"):
    """Update metadata for a file or folder with current timestamp"""
    current_time = datetime.now().isoformat()
    existing_metadata = get_file_metadata(file_path)
    
    metadata = {
        "creator": creator,
        "created_at": existing_metadata.get("created_at", current_time),
        "modified_at": current_time,
        "size": existing_metadata.get("size", 0),
        "is_dir": existing_metadata.get("is_dir", False)
    }
    
    set_file_metadata(file_path, metadata)

def get_file_permission(file_path: str) -> bool:
    """Get the public/private status of a file or folder"""
    permissions = load_permissions()
    return permissions.get(file_path, False)  # Default to private

def set_file_permission(file_path: str, is_public: bool):
    """Set the public/private status of a file or folder"""
    permissions = load_permissions()
    permissions[file_path] = is_public
    save_permissions(permissions)

@router.get("")
def list_files(path: str = "") -> Dict[str, Any]:
    """List files and directories under the given path (relative to DATA_ROOT)."""
    abs_path = os.path.abspath(os.path.join(DATA_ROOT, path))
    if not abs_path.startswith(os.path.abspath(DATA_ROOT)):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="Path not found")
    
    items = []
    for entry in os.scandir(abs_path):
        # Skip the metadata and permissions files
        if entry.name in [".permissions.json", ".metadata.json"]:
            continue
            
        item_path = os.path.relpath(entry.path, DATA_ROOT)
        stat = entry.stat()
        
        # Get metadata
        metadata = get_file_metadata(item_path)
        
        items.append({
            "name": entry.name,
            "is_dir": entry.is_dir(),
            "size": entry.stat().st_size if not entry.is_dir() else None,
            "is_public": get_file_permission(item_path),
            "metadata": {
                "creator": metadata.get("creator", "admin"),
                "created_at": metadata.get("created_at", datetime.fromtimestamp(stat.st_ctime).isoformat()),
                "modified_at": metadata.get("modified_at", datetime.fromtimestamp(stat.st_mtime).isoformat()),
                "size": metadata.get("size", stat.st_size if not entry.is_dir() else 0),
                "is_dir": metadata.get("is_dir", entry.is_dir())
            }
        })
    return {"success": True, "path": path, "items": items}

@router.get("/download")
def download_file(path: str = Query(..., description="Path relative to data root")):
    """Download or view a file from the data directory."""
    abs_path = os.path.abspath(os.path.join(DATA_ROOT, path))
    if not abs_path.startswith(os.path.abspath(DATA_ROOT)):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(abs_path, filename=os.path.basename(abs_path))

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    path: str = Form("")
) -> Dict[str, Any]:
    """Upload a file to the specified path (relative to DATA_ROOT)."""
    abs_path = os.path.abspath(os.path.join(DATA_ROOT, path))
    if not abs_path.startswith(os.path.abspath(DATA_ROOT)):
        raise HTTPException(status_code=400, detail="Invalid path")
    
    # Create directory if it doesn't exist
    os.makedirs(abs_path, exist_ok=True)
    
    # Save file
    file_path = os.path.join(abs_path, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Update metadata for the uploaded file
        relative_file_path = os.path.relpath(file_path, DATA_ROOT)
        update_file_metadata(relative_file_path, creator="admin")
        
        return {
            "success": True,
            "message": f"File {file.filename} uploaded successfully",
            "file_path": os.path.relpath(file_path, DATA_ROOT)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

@router.post("/mkdir")
async def create_folder(
    folder_name: str = Form(...),
    path: str = Form("")
) -> Dict[str, Any]:
    """Create a new folder in the specified path (relative to DATA_ROOT)."""
    abs_path = os.path.abspath(os.path.join(DATA_ROOT, path))
    if not abs_path.startswith(os.path.abspath(DATA_ROOT)):
        raise HTTPException(status_code=400, detail="Invalid path")
    
    # Create parent directory if it doesn't exist
    os.makedirs(abs_path, exist_ok=True)
    
    # Create new folder
    new_folder_path = os.path.join(abs_path, folder_name)
    try:
        os.makedirs(new_folder_path, exist_ok=False)
        
        # Update metadata for the created folder
        relative_folder_path = os.path.relpath(new_folder_path, DATA_ROOT)
        update_file_metadata(relative_folder_path, creator="admin")
        
        return {
            "success": True,
            "message": f"Folder {folder_name} created successfully",
            "folder_path": os.path.relpath(new_folder_path, DATA_ROOT)
        }
    except FileExistsError:
        raise HTTPException(status_code=400, detail=f"Folder {folder_name} already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating folder: {str(e)}")

@router.delete("/delete")
async def delete_item(
    path: str = Query(..., description="Path relative to data root")
) -> Dict[str, Any]:
    """Delete a file or folder from the data directory."""
    abs_path = os.path.abspath(os.path.join(DATA_ROOT, path))
    if not abs_path.startswith(os.path.abspath(DATA_ROOT)):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="Item not found")
    
    try:
        if os.path.isdir(abs_path):
            import shutil
            shutil.rmtree(abs_path)
            message = f"Folder {os.path.basename(abs_path)} deleted successfully"
        else:
            os.remove(abs_path)
            message = f"File {os.path.basename(abs_path)} deleted successfully"
        
        return {
            "success": True,
            "message": message
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting item: {str(e)}")

@router.get("/view/{file_path:path}")
async def view_file(file_path: str) -> Dict[str, Any]:
    """View a file in the browser - returns file info and viewing options"""
    try:
        # Decode the file path
        decoded_path = urllib.parse.unquote(file_path)
        full_path = os.path.join(DATA_ROOT, decoded_path)
        
        if not os.path.exists(full_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        if not os.path.isfile(full_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Path is not a file"
            )
        
        # Get file info
        stat = os.stat(full_path)
        file_size = stat.st_size
        file_extension = os.path.splitext(full_path)[1].lower()
        
        # Determine file type and viewing capabilities
        file_info = {
            "path": decoded_path,
            "name": os.path.basename(full_path),
            "size": file_size,
            "size_formatted": format_file_size(file_size),
            "extension": file_extension,
            "mime_type": get_mime_type(file_extension),
            "can_view": can_view_in_browser(file_extension),
            "view_type": get_view_type(file_extension),
            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
        }
        
        return {
            "success": True,
            "data": file_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting file info: {str(e)}"
        )

@router.get("/preview/{file_path:path}")
async def preview_file(file_path: str):
    """Preview a file in the browser - serves file content with appropriate headers"""
    try:
        # Decode the file path
        decoded_path = urllib.parse.unquote(file_path)
        full_path = os.path.join(DATA_ROOT, decoded_path)
        
        if not os.path.exists(full_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        if not os.path.isfile(full_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Path is not a file"
            )
        
        file_extension = os.path.splitext(full_path)[1].lower()
        
        # For ZIM files, ensure we support range requests
        if file_extension == '.zim':
            return FileResponse(
                full_path,
                media_type='application/x-zim',
                filename=os.path.basename(full_path),
                headers={
                    'Accept-Ranges': 'bytes',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
                    'Access-Control-Allow-Headers': 'Range, Content-Range'
                }
            )
        
        # For images, PDFs, and other viewable files, serve directly
        if can_view_in_browser(file_extension):
            return FileResponse(
                full_path,
                media_type=get_mime_type(file_extension),
                filename=os.path.basename(full_path)
            )
        
        # For other files, return file info
        else:
            stat = os.stat(full_path)
            return {
                "success": True,
                "data": {
                    "message": "File cannot be previewed in browser",
                    "file_name": os.path.basename(full_path),
                    "file_size": format_file_size(stat.st_size),
                    "extension": file_extension
                }
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error previewing file: {str(e)}"
        )

@router.get("/zim-viewer/{file_path:path}")
async def zim_viewer(file_path: str):
    """Serve ZIM file viewer HTML page"""
    try:
        # Decode the file path
        decoded_path = urllib.parse.unquote(file_path)
        full_path = os.path.join(DATA_ROOT, decoded_path)
        
        if not os.path.exists(full_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ZIM file not found"
            )
        
        if not full_path.lower().endswith('.zim'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is not a ZIM file"
            )
        
        # Create a simple ZIM viewer HTML page
        zim_viewer_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>ZIM Viewer - {os.path.basename(full_path)}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 20px;
                    padding-bottom: 10px;
                    border-bottom: 1px solid #eee;
                }}
                .file-info {{
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 5px;
                    margin-bottom: 20px;
                }}
                .viewer-frame {{
                    width: 100%;
                    height: 600px;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                }}
                .download-btn {{
                    background: #007bff;
                    color: white;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    text-decoration: none;
                    display: inline-block;
                }}
                .download-btn:hover {{
                    background: #0056b3;
                }}
                .back-btn {{
                    background: #6c757d;
                    color: white;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    text-decoration: none;
                    display: inline-block;
                }}
                .back-btn:hover {{
                    background: #545b62;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>ZIM File Viewer</h1>
                    <div>
                        <a href="/api/v1/files/download/{file_path}" class="download-btn">Download</a>
                        <a href="javascript:history.back()" class="back-btn">Back</a>
                    </div>
                </div>
                
                <div class="file-info">
                    <h3>File Information</h3>
                    <p><strong>Name:</strong> {os.path.basename(full_path)}</p>
                    <p><strong>Size:</strong> {format_file_size(os.path.getsize(full_path))}</p>
                    <p><strong>Type:</strong> ZIM Archive (Offline Wikipedia/Knowledge Base)</p>
                </div>
                
                <div>
                    <h3>ZIM File Content</h3>
                    <p>This is a ZIM file containing offline content. To view the contents, you can:</p>
                    <ul>
                        <li>Use <a href="https://kiwix.org/en/downloads/" target="_blank">Kiwix</a> to open this file</li>
                        <li>Download and extract the ZIM file</li>
                        <li>Use online ZIM viewers (if available)</li>
                    </ul>
                    <p><strong>Note:</strong> ZIM files are compressed archives containing web content. They require special software to view properly.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return HTMLResponse(content=zim_viewer_html)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error serving ZIM viewer: {str(e)}"
        )

@router.get("/download-status")
async def get_download_status() -> Dict[str, Any]:
    """Get status of currently downloading files"""
    try:
        from app.models.pile import Pile
        from sqlalchemy import select
        from app.core.database import get_db
        
        # Get database session
        async for db in get_db():
            # Get all piles that are currently downloading
            result = await db.execute(
                select(Pile).where(Pile.is_downloading == True)
            )
            downloading_piles = result.scalars().all()
            
            # Create a map of file paths to download status
            download_status = {}
            for pile in downloading_piles:
                if pile.file_path:
                    # Extract just the filename from the full path
                    filename = os.path.basename(pile.file_path)
                    download_status[filename] = {
                        "pile_id": pile.id,
                        "pile_name": pile.name,
                        "progress": pile.download_progress or 0.0,
                        "is_downloading": pile.is_downloading,
                        "file_path": pile.file_path
                    }
            
            return {
                "success": True,
                "data": download_status
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting download status: {str(e)}"
        )

@router.get("/permission/{file_path:path}")
async def get_file_permission_status(file_path: str) -> Dict[str, Any]:
    """Get the public/private status of a specific file or folder"""
    try:
        # Decode the file path
        decoded_path = urllib.parse.unquote(file_path)
        full_path = os.path.join(DATA_ROOT, decoded_path)
        
        if not os.path.exists(full_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File or folder not found"
            )
        
        is_public = get_file_permission(decoded_path)
        
        return {
            "success": True,
            "data": {
                "path": decoded_path,
                "name": os.path.basename(full_path),
                "is_public": is_public,
                "is_dir": os.path.isdir(full_path)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting file permission: {str(e)}"
        )

@router.post("/permission/{file_path:path}/toggle")
async def toggle_file_permission(file_path: str) -> Dict[str, Any]:
    """Toggle the public/private status of a specific file or folder"""
    try:
        # Decode the file path
        decoded_path = urllib.parse.unquote(file_path)
        full_path = os.path.join(DATA_ROOT, decoded_path)
        
        if not os.path.exists(full_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File or folder not found"
            )
        
        current_status = get_file_permission(decoded_path)
        new_status = not current_status
        
        set_file_permission(decoded_path, new_status)
        
        return {
            "success": True,
            "message": f"{'Made public' if new_status else 'Made private'}: {os.path.basename(full_path)}",
            "data": {
                "path": decoded_path,
                "name": os.path.basename(full_path),
                "is_public": new_status,
                "is_dir": os.path.isdir(full_path)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error toggling file permission: {str(e)}"
        )

@router.post("/permission/{file_path:path}")
async def set_file_permission_status(
    file_path: str,
    is_public: bool = Form(...)
) -> Dict[str, Any]:
    """Set the public/private status of a specific file or folder"""
    try:
        # Decode the file path
        decoded_path = urllib.parse.unquote(file_path)
        full_path = os.path.join(DATA_ROOT, decoded_path)
        
        if not os.path.exists(full_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File or folder not found"
            )
        
        set_file_permission(decoded_path, is_public)
        
        return {
            "success": True,
            "message": f"{'Made public' if is_public else 'Made private'}: {os.path.basename(full_path)}",
            "data": {
                "path": decoded_path,
                "name": os.path.basename(full_path),
                "is_public": is_public,
                "is_dir": os.path.isdir(full_path)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error setting file permission: {str(e)}"
        )

@router.get("/metadata/{file_path:path}")
async def get_file_metadata_info(file_path: str) -> Dict[str, Any]:
    """Get detailed metadata information for a specific file or folder"""
    try:
        # Decode the file path
        decoded_path = urllib.parse.unquote(file_path)
        full_path = os.path.join(DATA_ROOT, decoded_path)
        
        if not os.path.exists(full_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File or folder not found"
            )
        
        # Get file stats
        stat = os.stat(full_path)
        
        # Get metadata
        metadata = get_file_metadata(decoded_path)
        
        # Get permission status
        is_public = get_file_permission(decoded_path)
        
        # Format dates
        created_at = metadata.get("created_at", datetime.fromtimestamp(stat.st_ctime).isoformat())
        modified_at = metadata.get("modified_at", datetime.fromtimestamp(stat.st_mtime).isoformat())
        
        # Calculate time differences
        created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        modified_dt = datetime.fromisoformat(modified_at.replace('Z', '+00:00'))
        now = datetime.now()
        
        created_ago = now - created_dt
        modified_ago = now - modified_dt
        
        def format_time_ago(td):
            if td.days > 0:
                return f"{td.days} day{'s' if td.days != 1 else ''} ago"
            elif td.seconds > 3600:
                hours = td.seconds // 3600
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
            elif td.seconds > 60:
                minutes = td.seconds // 60
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            else:
                return "Just now"
        
        detailed_metadata = {
            "path": decoded_path,
            "name": os.path.basename(full_path),
            "is_dir": os.path.isdir(full_path),
            "is_public": is_public,
            "size": stat.st_size if not os.path.isdir(full_path) else 0,
            "size_formatted": format_file_size(stat.st_size) if not os.path.isdir(full_path) else "0 B",
            "creator": metadata.get("creator", "admin"),
            "created_at": created_at,
            "created_ago": format_time_ago(created_ago),
            "modified_at": modified_at,
            "modified_ago": format_time_ago(modified_ago),
            "permissions": {
                "owner_read": True,
                "owner_write": True,
                "owner_execute": os.access(full_path, os.X_OK),
                "public_read": is_public,
                "public_write": False
            },
            "file_info": {
                "extension": os.path.splitext(full_path)[1].lower() if not os.path.isdir(full_path) else "",
                "mime_type": get_mime_type(os.path.splitext(full_path)[1].lower()) if not os.path.isdir(full_path) else "inode/directory",
                "inode": stat.st_ino,
                "device": stat.st_dev
            }
        }
        
        return {
            "success": True,
            "data": detailed_metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting file metadata: {str(e)}"
        )

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def get_mime_type(extension: str) -> str:
    """Get MIME type for file extension"""
    mime_types = {
        '.pdf': 'application/pdf',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.svg': 'image/svg+xml',
        '.webp': 'image/webp',
        '.html': 'text/html',
        '.htm': 'text/html',
        '.txt': 'text/plain',
        '.md': 'text/markdown',
        '.json': 'application/json',
        '.xml': 'application/xml',
        '.csv': 'text/csv',
        '.mp4': 'video/mp4',
        '.avi': 'video/x-msvideo',
        '.mov': 'video/quicktime',
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.zip': 'application/zip',
        '.rar': 'application/x-rar-compressed',
        '.7z': 'application/x-7z-compressed',
        '.tar': 'application/x-tar',
        '.gz': 'application/gzip',
        '.zim': 'application/x-zim',
        '.epub': 'application/epub+zip',
        '.mobi': 'application/x-mobipocket-ebook',
        '.azw3': 'application/vnd.amazon.ebook'
    }
    return mime_types.get(extension.lower(), 'application/octet-stream')

def can_view_in_browser(extension: str) -> bool:
    """Check if file can be viewed in browser"""
    viewable_extensions = {
        '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp',
        '.html', '.htm', '.txt', '.md', '.json', '.xml', '.csv',
        '.mp4', '.avi', '.mov', '.mp3', '.wav'
    }
    return extension.lower() in viewable_extensions

def get_view_type(extension: str) -> str:
    """Get the type of viewer needed for the file"""
    extension = extension.lower()
    
    if extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp']:
        return 'image'
    elif extension == '.pdf':
        return 'pdf'
    elif extension in ['.html', '.htm']:
        return 'html'
    elif extension in ['.txt', '.md', '.json', '.xml', '.csv']:
        return 'text'
    elif extension in ['.mp4', '.avi', '.mov']:
        return 'video'
    elif extension in ['.mp3', '.wav']:
        return 'audio'
    elif extension == '.zim':
        return 'zim'
    else:
        return 'download'

@router.post("/move")
async def move_item(
    src_path: str = Form(...),
    dest_path: str = Form(...)
) -> Dict[str, Any]:
    """Move or rename a file or folder."""
    abs_src = os.path.abspath(os.path.join(DATA_ROOT, src_path))
    abs_dest = os.path.abspath(os.path.join(DATA_ROOT, dest_path))
    if not abs_src.startswith(os.path.abspath(DATA_ROOT)) or not abs_dest.startswith(os.path.abspath(DATA_ROOT)):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not os.path.exists(abs_src):
        raise HTTPException(status_code=404, detail="Source not found")
    if os.path.exists(abs_dest):
        raise HTTPException(status_code=400, detail="Destination already exists")
    try:
        os.rename(abs_src, abs_dest)
        return {
            "success": True,
            "message": f"Moved {src_path} to {dest_path}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error moving item: {str(e)}") 