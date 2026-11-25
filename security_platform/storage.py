"""Private file storage abstraction for demonstration uploads.

Supports Vercel Blob Private Storage (when BLOB_READ_WRITE_TOKEN is set)
and falls back to private local filesystem storage in UPLOAD_FOLDER.
"""

import os
import requests

VERCEL_BLOB_API_BASE = "https://blob.vercel-storage.com"


def get_upload_folder() -> str:
    """Return the configured local upload directory."""
    folder = os.getenv("UPLOAD_FOLDER")
    if folder:
        return folder
    if os.getenv("VERCEL") == "1" or "VERCEL" in os.environ:
        return os.path.join("/tmp", "demonstration_uploads")
    return os.path.join("database", "demonstration_uploads")


def is_vercel_blob_configured() -> bool:
    """Return True when BLOB_READ_WRITE_TOKEN is configured."""
    return bool(os.getenv("BLOB_READ_WRITE_TOKEN", "").strip())


def store_demonstration_file(stored_name: str, file_bytes: bytes, mime_type: str = "application/octet-stream") -> str:
    """Persist demonstration file privately and return the stored reference.

    When BLOB_READ_WRITE_TOKEN is configured, uploads to Vercel Blob with
    private access (x-access: private). Otherwise writes to UPLOAD_FOLDER.
    """
    token = os.getenv("BLOB_READ_WRITE_TOKEN", "").strip()
    if token:
        resp = requests.put(
            f"{VERCEL_BLOB_API_BASE}/{stored_name}",
            data=file_bytes,
            headers={
                "Authorization": f"Bearer {token}",
                "x-api-version": "7",
                "x-content-type": mime_type or "application/octet-stream",
                "x-add-random-suffix": "0",
                "x-access": "private",
            },
            timeout=20,
        )
        resp.raise_for_status()
        payload = resp.json()
        return payload.get("url") or stored_name

    upload_dir = get_upload_folder()
    os.makedirs(upload_dir, exist_ok=True)
    dest_path = os.path.join(upload_dir, stored_name)
    with open(dest_path, "wb") as f:
        f.write(file_bytes)
    return stored_name


def delete_demonstration_file(stored_ref: str) -> None:
    """Delete a stored demonstration file from Vercel Blob or local disk."""
    if not stored_ref:
        return

    token = os.getenv("BLOB_READ_WRITE_TOKEN", "").strip()
    if token and stored_ref.startswith("https://"):
        try:
            requests.post(
                f"{VERCEL_BLOB_API_BASE}/delete",
                json={"urls": [stored_ref]},
                headers={
                    "Authorization": f"Bearer {token}",
                    "x-api-version": "7",
                },
                timeout=15,
            )
        except Exception:
            pass
        return

    upload_dir = get_upload_folder()
    file_path = os.path.join(upload_dir, stored_ref)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass
