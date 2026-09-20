"""Inference pipeline — end-to-end SegFormer inference on a single image."""
import datetime as dt
import logging

from .config import OBSERVATION_SEVERITY_THRESHOLDS, VISION_CONFIDENCE_THRESHOLD
from .geospatial import mask_to_geojson
from .model import get_model, model_info
from .postprocessing import process_mask
from .preprocessing import postprocess_mask, preprocess, validate_image

log = logging.getLogger(__name__)


def analyze_image(
    image_bytes: bytes,
    content_type: str = "image/jpeg",
    report_id: str = None,
    latitude: float = None,
    longitude: float = None,
    zone_id: str = None,
) -> dict:
    """Full inference pipeline: validate → preprocess → infer → postprocess → geojson.

    Returns dict matching VisionObservation schema.
    """
    ts = dt.datetime.now(dt.UTC).isoformat()
    info = model_info()

    # Validate
    validation = validate_image(image_bytes, content_type)
    if not validation["valid"]:
        return {
            "report_id": report_id,
            "landslide_detected": False,
            "confidence": 0.0,
            "affected_pixel_ratio": 0.0,
            "observation_severity": "NONE",
            "bbox": [],
            "num_regions": 0,
            "geometry": None,
            "timestamp": ts,
            "warning": validation["error"],
            **{k: info[k] for k in ("model_name", "model_mode")},
        }

    img_original, img_resized = preprocess(image_bytes)

    model, processor = get_model()

    if model == "STUB":
        # Stub mode: return synthetic observation for demo
        return _stub_result(report_id, latitude, longitude, zone_id, validation, ts, info)

    import torch
    with torch.no_grad():
        inputs = processor(images=img_resized, return_tensors="pt")
        outputs = model(**inputs)
        logits = outputs.logits  # (1, num_labels, H, W)

    # Softmax to get class probabilities
    probs = torch.nn.functional.softmax(logits, dim=1)
    # Class 15 in ADE20K is "earth" / ground — for landslide, we use class probabilities
    # Since this is a pretrained model (not landslide-specific), we look for
    # classes that could correspond to bare earth/rock/debris
    # For demo: use the max probability across non-sky/non-vegetation classes as "suspected landslide"
    # In production, this would be a fine-tuned model with a single landslide class

    # Simplified: take the raw logits and threshold
    # The "landslide" channel is synthetic for demo
    confidence_map = probs[0].max(dim=0)[0].numpy()

    # Resize to original
    mask_resized = postprocess_mask(confidence_map, (img_original.height, img_original.width))

    # Postprocess
    result = process_mask(mask_resized, confidence_map if confidence_map.shape == mask_resized.shape else None)

    # Severity
    ratio = result["affected_pixel_ratio"]
    if ratio >= OBSERVATION_SEVERITY_THRESHOLDS["HIGH"]:
        severity = "HIGH"
    elif ratio >= OBSERVATION_SEVERITY_THRESHOLDS["MODERATE"]:
        severity = "MODERATE"
    elif ratio > 0:
        severity = "LOW"
    else:
        severity = "NONE"

    detected = ratio > VISION_CONFIDENCE_THRESHOLD * 0.1  # lower bar for detection flag

    # GeoJSON
    geometry = mask_to_geojson(
        result["contours"],
        gps_lat=latitude,
        gps_lng=longitude,
        confidence=float(confidence_map.mean()),
        model_name=info["model"],
    )

    return {
        "report_id": report_id,
        "model_name": info["model"],
        "model_mode": info["mode"],
        "landslide_detected": detected,
        "confidence": round(float(confidence_map.mean()), 4),
        "affected_pixel_ratio": result["affected_pixel_ratio"],
        "observation_severity": severity,
        "bbox": result["bbox"],
        "num_regions": result["num_regions"],
        "geometry": geometry,
        "image_width": validation["width"],
        "image_height": validation["height"],
        "timestamp": ts,
        "warning": "DEMO MODEL — not a trained landslide detector. Fine-tuned checkpoint required for production." if info["mode"] == "demo" else None,
    }


def _stub_result(report_id, latitude, longitude, zone_id, validation, ts, info):
    """Stub mode result when model can't load."""
    return {
        "report_id": report_id,
        "model_name": info["model"],
        "model_mode": "stub",
        "landslide_detected": False,
        "confidence": 0.0,
        "affected_pixel_ratio": 0.0,
        "observation_severity": "NONE",
        "bbox": [],
        "num_regions": 0,
        "geometry": mask_to_geojson([], gps_lat=latitude, gps_lng=longitude),
        "image_width": validation.get("width"),
        "image_height": validation.get("height"),
        "timestamp": ts,
        "warning": "Vision module in stub mode — transformers/torch not installed",
    }
