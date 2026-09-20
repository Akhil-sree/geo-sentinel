"""SegFormer model singleton — loads once, reuses across requests."""
import logging
from .config import VISION_MODEL, VISION_CHECKPOINT, VISION_MODE

log = logging.getLogger(__name__)

_model = None
_processor = None


def get_model():
    """Lazy-load SegFormer model + processor. Returns (model, processor)."""
    global _model, _processor
    if _model is not None:
        return _model, _processor

    try:
        from transformers import SegformerForSemanticSegmentation

        # segformer feature extractor was renamed in newer transformers
        try:
            from transformers import SegformerImageProcessor as ProcessorClass
        except ImportError:
            from transformers import SegformerFeatureExtractor as ProcessorClass

        if VISION_CHECKPOINT:
            log.info("Loading SegFormer from checkpoint: %s", VISION_CHECKPOINT)
            _processor = ProcessorClass.from_pretrained(VISION_CHECKPOINT)
            _model = SegformerForSemanticSegmentation.from_pretrained(VISION_CHECKPOINT)
        else:
            model_name = "nvidia/segformer-b0-finetuned-ade-512-512"
            log.info("Loading pretrained SegFormer: %s (DEMO mode)", model_name)
            _processor = ProcessorClass.from_pretrained(model_name)
            _model = SegformerForSemanticSegmentation.from_pretrained(model_name)

        import torch
        _model.eval()
        log.info("SegFormer loaded successfully on %s", "CPU")

    except ImportError:
        log.warning("transformers/torch not installed — vision module in stub mode")
        _model = "STUB"
        _processor = None
    except Exception as e:
        log.warning("Failed to load SegFormer: %s — stub mode", e)
        _model = "STUB"
        _processor = None

    return _model, _processor


def model_info():
    status = "LOADED" if _model is not None and _model != "STUB" else ("STUB" if _model == "STUB" else "NOT_LOADED")
    return {
        "model": VISION_MODEL,
        "mode": VISION_MODE,
        "checkpoint": VISION_CHECKPOINT or "nvidia/segformer-b0-finetuned-ade-512-512",
        "status": status,
        "trained_landslide": bool(VISION_CHECKPOINT),
    }
