"""Image validation and preprocessing for SegFormer input."""
from io import BytesIO
from .config import VISION_ALLOWED_MIME, VISION_MAX_FILE_SIZE_MB, VISION_INPUT_SIZE


def validate_image(content: bytes, content_type: str) -> dict:
    """Validate uploaded image. Returns {valid, error, width, height}."""
    if content_type not in VISION_ALLOWED_MIME:
        return {"valid": False, "error": f"Invalid MIME: {content_type}. Allowed: {VISION_ALLOWED_MIME}"}

    if len(content) > VISION_MAX_FILE_SIZE_MB * 1024 * 1024:
        return {"valid": False, "error": f"File too large: {len(content) / 1024 / 1024:.1f}MB > {VISION_MAX_FILE_SIZE_MB}MB"}

    try:
        from PIL import Image
        img = Image.open(BytesIO(content))
        img.verify()
        img = Image.open(BytesIO(content))  # re-open after verify
        return {"valid": True, "width": img.width, "height": img.height, "format": img.format}
    except Exception as e:
        return {"valid": False, "error": f"Malformed image: {e}"}


def preprocess(content: bytes):
    """Convert image bytes to model-ready tensor. Returns (pil_image, input_tensor)."""
    from PIL import Image
    import numpy as np

    img = Image.open(BytesIO(content)).convert("RGB")
    img_resized = img.resize(VISION_INPUT_SIZE, Image.BILINEAR)
    return img, img_resized


def postprocess_mask(mask, original_size: tuple) -> "np.ndarray":
    """Upsample model output mask back to original image size."""
    import numpy as np
    from PIL import Image

    if hasattr(mask, "numpy"):
        mask = mask.numpy()
    if hasattr(mask, "squeeze"):
        mask = mask.squeeze()

    mask_pil = Image.fromarray(mask.astype(np.uint8))
    mask_resized = mask_pil.resize((original_size[1], original_size[0]), Image.NEAREST)
    return np.array(mask_resized)
