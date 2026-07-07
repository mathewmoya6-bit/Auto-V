# app/api/v1/endpoints/upload.py
# =============================================================================
# AUTO-V API - File upload to Supabase Storage
#
# Matches the frontend's uploadFile() exactly: multipart form with fields
# `file`, `type` ("image" or "document"), and `slot` (e.g. "front",
# "logbook"), Bearer-authenticated, returning {"url": ...}.
# =============================================================================

import logging
import os
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from supabase import Client, create_client

from app.api.v1.endpoints.auth import get_current_user
from app.core.config import settings
from app.models.user import UserProfile as User
from app.schemas.valuation import UploadResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Reuses whatever Supabase credentials the rest of the app already has
# configured (see app/core/config.py) -- no new env vars required here.
_SUPABASE_URL = getattr(settings, "supabase_url", None) or os.getenv("SUPABASE_URL")
_SUPABASE_KEY = (
    getattr(settings, "supabase_service_role_key", None)
    or getattr(settings, "supabase_anon_key", None)
    or os.getenv("SUPABASE_KEY")
)

_STORAGE_BUCKET = getattr(settings, "storage_bucket", None) or os.getenv("STORAGE_BUCKET", "autov-storage")

_supabase_client: Client | None = None
if _SUPABASE_URL and _SUPABASE_KEY:
    _supabase_client = create_client(_SUPABASE_URL, _SUPABASE_KEY)
else:
    logger.warning(
        "Supabase Storage not configured (missing URL/key) -- "
        "POST /upload will fail until SUPABASE_URL and a service role key are available."
    )

_MAX_UPLOAD_BYTES = int(getattr(settings, "max_image_size", 10 * 1024 * 1024))  # 10MB default
_ALLOWED_CONTENT_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/heic",
    "application/pdf",
}


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    type: Literal["image", "document"] = Form(...),
    slot: str = Form(...),
    current_user: User = Depends(get_current_user),
):
    """Upload a single image or document to Supabase Storage and return its
    public URL. Requires authentication -- files are namespaced under the
    uploading user's ID so uploads from different users never collide or
    overwrite each other."""

    if _supabase_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File storage is not configured on this server.",
        )

    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {file.content_type}",
        )

    contents = await file.read()
    if len(contents) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {_MAX_UPLOAD_BYTES // (1024 * 1024)}MB",
        )
    if not contents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    extension = (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else "bin"
    storage_path = f"{current_user.id}/{type}/{slot}-{uuid.uuid4().hex}.{extension}"

    try:
        _supabase_client.storage.from_(_STORAGE_BUCKET).upload(
            storage_path,
            contents,
            {"content-type": file.content_type},
        )
        public_url = _supabase_client.storage.from_(_STORAGE_BUCKET).get_public_url(storage_path)
    except Exception:
        logger.exception("Supabase Storage upload failed for %s", storage_path)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="File storage upload failed. Please try again.")

    logger.info("Uploaded %s (%s, slot=%s) for user %s -> %s", file.filename, type, slot, current_user.id, storage_path)

    return UploadResponse(url=public_url, type=type, slot=slot)
