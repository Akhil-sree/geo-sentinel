"""Post-processing: thresholding, morphological cleanup, connected components, contours."""
import numpy as np

from .config import VISION_CONFIDENCE_THRESHOLD, VISION_MIN_REGION_AREA


def process_mask(raw_mask: np.ndarray, confidence_map: np.ndarray = None) -> dict:
    """Clean up raw segmentation mask and extract landslide regions.

    Returns:
        binary_mask, affected_pixel_ratio, contour polygons, bbox, severity
    """
    from scipy import ndimage

    if confidence_map is not None:
        binary = (confidence_map >= VISION_CONFIDENCE_THRESHOLD).astype(np.uint8)
    else:
        binary = (raw_mask > 0).astype(np.uint8)

    # Morphological cleanup: remove small isolated pixels
    struct = ndimage.generate_binary_structure(2, 2)
    cleaned = ndimage.binary_opening(binary, structure=struct, iterations=1)
    cleaned = ndimage.binary_closing(cleaned, structure=struct, iterations=1)

    # Connected components
    labeled, num_features = ndimage.label(cleaned)
    regions = []
    total_affected = 0

    for i in range(1, num_features + 1):
        component = (labeled == i)
        area = int(component.sum())
        if area < VISION_MIN_REGION_AREA:
            continue
        total_affected += area
        contours = _extract_contours(component)
        bbox = _bounding_box(component)
        regions.append({
            "area_pixels": area,
            "contours": contours,
            "bbox": bbox,
        })

    total_pixels = raw_mask.shape[0] * raw_mask.shape[1]
    affected_ratio = total_affected / total_pixels if total_pixels > 0 else 0.0

    # Overall bounding box
    all_bboxes = [r["bbox"] for r in regions]
    overall_bbox = _merge_bboxes(all_bboxes) if all_bboxes else [0, 0, 0, 0]

    # Merge all contours into a single polygon set
    all_contours = []
    for r in regions:
        all_contours.extend(r["contours"])

    return {
        "binary_mask": cleaned.astype(np.uint8),
        "affected_pixel_ratio": round(affected_ratio, 4),
        "regions": regions,
        "bbox": overall_bbox,
        "contours": all_contours,
        "num_regions": len(regions),
    }


def _extract_contours(binary_component: np.ndarray) -> list:
    """Extract contour polygons from a binary component using OpenCV."""
    try:
        import cv2
        component_uint8 = binary_component.astype(np.uint8) * 255
        contours, _ = cv2.findContours(component_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        polygons = []
        for contour in contours:
            if len(contour) >= 3:
                pts = contour.squeeze().tolist()
                if isinstance(pts[0], (int, float)):
                    continue  # single point
                polygons.append(pts)
        return polygons
    except ImportError:
        return []


def _bounding_box(binary_component: np.ndarray) -> list:
    """Return [y_min, x_min, y_max, x_max] of the component."""
    ys, xs = np.where(binary_component)
    if len(ys) == 0:
        return [0, 0, 0, 0]
    return [int(ys.min()), int(xs.min()), int(ys.max()), int(xs.max())]


def _merge_bboxes(bboxes: list) -> list:
    """Merge multiple bboxes into one encompassing bbox."""
    if not bboxes:
        return [0, 0, 0, 0]
    y_min = min(b[0] for b in bboxes)
    x_min = min(b[1] for b in bboxes)
    y_max = max(b[2] for b in bboxes)
    x_max = max(b[3] for b in bboxes)
    return [y_min, x_min, y_max, x_max]
