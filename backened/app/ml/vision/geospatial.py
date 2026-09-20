"""Geospatial output — convert pixel masks to GeoJSON where possible."""


def mask_to_geojson(
    contours: list,
    image_bbox: list = None,
    gps_lat: float = None,
    gps_lng: float = None,
    confidence: float = 0.0,
    model_name: str = "segformer-b0",
) -> dict:
    """Create GeoJSON from segmentation contours.

    If GPS coords are available (phone photo), we create a point feature
    with the observation. We do NOT pretend pixel contours map to precise
    geographic boundaries from an uncalibrated photo.

    If georeferencing data is available, we could transform pixel coords
    to geographic coords — but for field photos this is not available.
    """
    properties = {
        "source": "field_observation",
        "model": model_name,
        "confidence": round(confidence, 3),
        "geometry_type": "approximate",
    }

    if gps_lat is not None and gps_lng is not None:
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [gps_lng, gps_lat],
            },
            "properties": {
                **properties,
                "note": "Observation location; pixel mask does not represent precise geographic footprint",
            },
        }

    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [0, 0],
        },
        "properties": {
            **properties,
            "note": "No GPS data available",
        },
    }


def bbox_to_geojson(bbox: list, lat: float, lng: float, image_width: int, image_height: int) -> dict:
    """Approximate bbox as a geographic rectangle centered on the GPS point.

    Only used when we have GPS + image dimensions.
    Creates a rough local footprint (~100m scale for phone photos).
    """
    if lat == 0 and lng == 0:
        return None

    # Rough approximation: assume the photo covers ~200m x 150m at typical phone distance
    approx_scale_m = 200
    dy = (bbox[2] - bbox[0]) / image_height * approx_scale_m / 111000
    dx = (bbox[3] - bbox[1]) / image_width * approx_scale_m / (111000 * __import__('math').cos(__import__('math').radians(lat)))

    coords = [[
        [lng - dx, lat - dy],
        [lng + dx, lat - dy],
        [lng + dx, lat + dy],
        [lng - dx, lat + dy],
        [lng - dx, lat - dy],
    ]]

    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": coords,
        },
        "properties": {
            "source": "field_observation",
            "geometry_type": "approximate_footprint",
            "note": "Approximate observation area; not precise landslide boundary",
        },
    }
