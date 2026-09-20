# SegFormer — BLOCKED

SEGFORMER_STATUS = BLOCKED

Automated gate refuses training until: non_constant_input == true, valid_mask_exists == true, image_mask_alignment == true, valid_pixel_ratio > threshold (configurable).

Current gate evidence:
```json
{
  "status": "BLOCKED",
  "checks": {
    "manifest_events": 13,
    "constant_optical_patches": "49/49",
    "masks_present": false,
    "non_constant_input": false,
    "valid_mask_exists": false
  }
}
```

49/49 optical patches are constant-0; 11/11 QA patches constant-1; no masks exist. Do not fabricate masks.
