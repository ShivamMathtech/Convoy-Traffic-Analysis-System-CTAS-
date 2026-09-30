"""Small shared helpers: filenames, hashing, masking secrets in logs."""
from __future__ import annotations

import re
import uuid
from pathlib import Path


def safe_filename(original: str) -> str:
    """Return a generated internal filename preserving only the extension."""
    ext = Path(original).suffix.lower()
    return f"{uuid.uuid4().hex}{ext}"


def mask_url_secret(url: str) -> str:
    """Mask password in rtsp://user:pass@host URLs for safe logging."""
    return re.sub(r"(://[^:/@]+:)[^@]+(@)", r"\1*****\2", url)


def new_id(prefix: str = "ses") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def fmt_time(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
