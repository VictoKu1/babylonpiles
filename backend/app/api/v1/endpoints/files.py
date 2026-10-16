from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from starlette.concurrency import run_in_threadpool
import os
import json
import html
import stat as stat_types
from pathlib import Path
from typing import List, Dict, Any
import urllib.parse
from datetime import datetime
from fastapi import status
from app.core.config import settings
from app.core.paths import resolve_path, validate_name, _reject_symlinks
from app.core.transfers import save_upload, TransferTooLarge

router = APIRouter()

DATA_ROOT = settings.data_dir
PERMISSIONS_FILE = os.path.join(DATA_ROOT, ".permissions.json")
METADATA_FILE = os.path.join(DATA_ROOT, ".metadata.json")

def content_path(relative: str, allow_root: bool = False) -> Path:
    try:
        return resolve_path(DATA_ROOT, relative, allow_root=allow_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

def content_key(relative: str) -> str:
    return content_path(relative).relative_to(Path(DATA_ROOT).resolve()).as_posix()

def content_child(path: str, name: str) -> Path:
    parent = content_path(path, allow_root=True)
    try:
        validate_name(name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    relative = parent.relative_to(Path(DATA_ROOT).resolve()) / name
    return content_path(relative.as_posix())

def load_permissions() -> Dict[str, Any]:
    """Load file/folder permissions from the permissions file"""
    try:
        if os.path.exists(PERMISSIONS_FILE):
            _reject_symlinks(Path(PERMISSIONS_FILE))
            with open(PERMISSIONS_FILE, 'r') as f:
                permissions = json.load(f)
                return permissions if isinstance(permissions, dict) else {}
        return {}
    except Exception:
        return {}

def save_permissions(permissions: Dict[str, Any]):
    """Save file/folder permissions to the permissions file"""
    try:
        os.makedirs(os.path.dirname(PERMISSIONS_FILE), exist_ok=True)
        _reject_symlinks(Path(PERMISSIONS_FILE))
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
            _reject_symlinks(Path(METADATA_FILE))
            with open(METADATA_FILE, 'r') as f:
                return json.load(f)
        return {}
    except Exception:
        return {}

def save_metadata(metadata: Dict[str, Dict[str, Any]]):
    """Save file/folder metadata to the metadata file"""
    try:
        os.makedirs(os.path.dirname(METADATA_FILE), exist_ok=True)
        _reject_symlinks(Path(METADATA_FILE))
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
    return metadata.get(content_key(file_path), {})

def set_file_metadata(file_path: str, metadata: Dict[str, Any]):
    """Set metadata for a file or folder"""
    all_metadata = load_metadata()
    all_metadata[content_key(file_path)] = metadata
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
    """A share applies to the identified content, never a reusable pathname."""
    path = content_path(file_path)
    key = path.relative_to(Path(DATA_ROOT).resolve()).as_posix()
    try:
        return _permission_matches(load_permissions().get(key), path.stat())
    except (OSError, ValueError):
        return False

def set_file_permission(file_path: str, is_public: bool):
    """Bind an explicit share to the current file identity; old booleans are private."""
    path = content_path(file_path)
    key = path.relative_to(Path(DATA_ROOT).resolve()).as_posix()
    permissions = load_permissions()
    if is_public:
        permissions[key] = {"version": 1, "identity": _content_identity(path.stat())}
    else:
        permissions.pop(key, None)
    save_permissions(permissions)

def _content_identity(info) -> Dict[str, Any]:
    identity = {"device": info.st_dev, "inode": info.st_ino}
    if stat_types.S_ISDIR(info.st_mode):
        return {**identity, "kind": "directory"}
    if not stat_types.S_ISREG(info.st_mode):
        raise ValueError("Only regular files and directories can be shared")
    return {**identity, "kind": "file", "mtime_ns": info.st_mtime_ns,
            "ctime_ns": info.st_ctime_ns, "size": info.st_size}

def _permission_matches(record, info) -> bool:
    return (isinstance(record, dict) and record.get("version") == 1
            and record.get("identity") == _content_identity(info))

class PublicFileResponse(StreamingResponse):
    """Stream the authorized descriptor and close it even on disconnect/errors."""
    def __init__(self, source, identity, filename):
        self.source = source
        # Unlink/rename may update ctime while the already-open bytes stay valid.
        self.identity = {key: value for key, value in identity.items() if key != "ctime_ns"}
        headers = {
            "Content-Disposition": "attachment; filename*=UTF-8''" + urllib.parse.quote(filename, safe=""),
            "Content-Length": str(identity["size"]),
            "Cache-Control": "private, no-store",
        }
        super().__init__(self._chunks(), media_type="application/octet-stream", headers=headers)

    def _unchanged(self):
        identity = _content_identity(os.fstat(self.source.fileno()))
        identity.pop("ctime_ns", None)
        if identity != self.identity:
            raise RuntimeError("Shared file changed during download")

    async def _chunks(self):
        try:
            while True:
                self._unchanged()
                chunk = await run_in_threadpool(self.source.read, 64 * 1024)
                self._unchanged()
                if not chunk:
                    break
                yield chunk
        finally:
            self.source.close()

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            self.source.close()

def public_file_response(file_path: str) -> StreamingResponse:
    """Open first, authorize fstat, then stream that same descriptor."""
    path = content_path(file_path)
    key = path.relative_to(Path(DATA_ROOT).resolve()).as_posix()
    flags = (os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
             | getattr(os, "O_BINARY", 0))
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="File not found") from exc
    except OSError as exc:
        raise HTTPException(status_code=400, detail="File cannot be opened safely") from exc
    source = None
    try:
        info = os.fstat(descriptor)
        if not stat_types.S_ISREG(info.st_mode):
            raise HTTPException(status_code=404, detail="File not found")
        if not _permission_matches(load_permissions().get(key), info):
            raise HTTPException(status_code=403, detail="File is not public")
        source = os.fdopen(descriptor, "rb")
        return PublicFileResponse(source, _content_identity(info), path.name)
    except BaseException:
        if source is not None:
            source.close()
        else:
            os.close(descriptor)
        raise

@router.get("")
def list_files(path: str = "") -> Dict[str, Any]:
    """List files and directories under the given path (relative to DATA_ROOT)."""
    abs_path = content_path(path, allow_root=True)
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="Path not found")
    if not os.path.isdir(abs_path):
        raise HTTPException(status_code=400, detail="Path is not a directory")
    
    items = []
    for entry in os.scandir(abs_path):
        # Skip the metadata and permissions files
        if entry.is_symlink():
            continue
        try:
            item_path = content_key(Path(entry.path).relative_to(Path(DATA_ROOT).resolve()).as_posix())
        except HTTPException:
            continue
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
    abs_path = content_path(path)
    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(abs_path, filename=os.path.basename(abs_path))

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    path: str = Form("")
) -> Dict[str, Any]:
    """Upload a file to the specified path (relative to DATA_ROOT)."""
    file_path = content_child(path, file.filename)
    try:
        await save_upload(file, file_path, settings.max_upload_size)
        
        # Update metadata for the uploaded file
        relative_file_path = file_path.relative_to(Path(DATA_ROOT).resolve()).as_posix()
        update_file_metadata(relative_file_path, creator="admin")
        
        return {
            "success": True,
            "message": f"File {file.filename} uploaded successfully",
            "file_path": relative_file_path
        }
    except TransferTooLarge as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

@router.post("/mkdir")
async def create_folder(
    folder_name: str = Form(...),
    path: str = Form("")
) -> Dict[str, Any]:
    """Create a new folder in the specified path (relative to DATA_ROOT)."""
    new_folder_path = content_child(path, folder_name)
    try:
        os.makedirs(new_folder_path, exist_ok=False)
        
        # Update metadata for the created folder
        relative_folder_path = new_folder_path.relative_to(Path(DATA_ROOT).resolve()).as_posix()
        update_file_metadata(relative_folder_path, creator="admin")
        
        return {
            "success": True,
            "message": f"Folder {folder_name} created successfully",
            "folder_path": relative_folder_path
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
    abs_path = content_path(path)
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
        # Validate the canonical path (the framework already decoded the URL)
        decoded_path = content_key(file_path)
        full_path = content_path(decoded_path)
        
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
        # Validate the canonical path (the framework already decoded the URL)
        decoded_path = content_key(file_path)
        full_path = content_path(decoded_path)
        
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
        
        # Serve ZIM files using the authenticated same-origin download path.
        if file_extension == '.zim':
            return FileResponse(
                full_path,
                media_type='application/x-zim',
                filename=os.path.basename(full_path)
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
        # Validate the canonical path (the framework already decoded the URL)
        decoded_path = content_key(file_path)
        full_path = content_path(decoded_path)
        
        if not os.path.exists(full_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ZIM file not found"
            )
        
        if not str(full_path).lower().endswith('.zim'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is not a ZIM file"
            )
        
        safe_name = html.escape(os.path.basename(full_path), quote=True)
        download_url = html.escape("/api/v1/files/download?" + urllib.parse.urlencode({"path": decoded_path}), quote=True)
        # Escape display text independently from the encoded URL attribute.
        zim_viewer_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>ZIM Viewer - {safe_name}</title>
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
                        <a href="{download_url}" class="download-btn">Download</a>
                        <a href="javascript:history.back()" class="back-btn">Back</a>
                    </div>
                </div>
                
                <div class="file-info">
                    <h3>File Information</h3>
                    <p><strong>Name:</strong> {safe_name}</p>
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
        # Validate the canonical path (the framework already decoded the URL)
        decoded_path = content_key(file_path)
        full_path = content_path(decoded_path)
        
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
        # Validate the canonical path (the framework already decoded the URL)
        decoded_path = content_key(file_path)
        full_path = content_path(decoded_path)
        
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
        # Validate the canonical path (the framework already decoded the URL)
        decoded_path = content_key(file_path)
        full_path = content_path(decoded_path)
        
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
        # Validate the canonical path (the framework already decoded the URL)
        decoded_path = content_key(file_path)
        full_path = content_path(decoded_path)
        
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
    abs_src = content_path(src_path)
    abs_dest = content_path(dest_path)
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
