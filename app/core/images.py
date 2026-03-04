"""Image validation utilities."""
from __future__ import annotations

from io import BytesIO

from PIL import Image, UnidentifiedImageError


MAX_IMAGE_PIXELS = 25_000_000


def verify_image_upload(buffer: bytes, *, max_pixels: int = MAX_IMAGE_PIXELS) -> tuple[int, int]:
    """Verify image header and enforce max pixel limit."""

    Image.MAX_IMAGE_PIXELS = max_pixels
    try:
        with Image.open(BytesIO(buffer)) as img:
            img.verify()
        with Image.open(BytesIO(buffer)) as img:
            width, height = img.size
    except Image.DecompressionBombError as exc:
        raise ValueError(f"이미지는 최대 {max_pixels // 1_000_000}MP까지 업로드할 수 있습니다.") from exc
    except UnidentifiedImageError as exc:
        raise ValueError("이미지 파일을 읽을 수 없습니다.") from exc
    except Exception as exc:  # pragma: no cover - unexpected PIL error
        raise ValueError("이미지 파일을 읽을 수 없습니다.") from exc

    if width * height > max_pixels:
        raise ValueError(f"이미지는 최대 {max_pixels // 1_000_000}MP까지 업로드할 수 있습니다.")

    return width, height
