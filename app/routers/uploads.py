"""Image/file upload endpoint. Saves to the configured upload dir and returns
a served URL that can be stored as a complaint image / proof image."""
import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.config import settings
from app.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/uploads", tags=["Uploads"])

_ALLOWED = {"image/jpeg", "image/png", "image/webp", "image/gif", "video/mp4"}
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_EXT = {
    "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
    "image/gif": ".gif", "video/mp4": ".mp4",
}


@router.post("", status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    if file.content_type not in _ALLOWED:
        raise HTTPException(415, f"Unsupported file type: {file.content_type}")

    contents = await file.read()
    if len(contents) > _MAX_BYTES:
        raise HTTPException(413, "File too large (max 10 MB)")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    ext = _EXT.get(file.content_type, "")
    fname = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(settings.UPLOAD_DIR, fname)
    with open(path, "wb") as f:
        f.write(contents)

    return {"url": f"/media/{fname}", "filename": fname, "size": len(contents)}
