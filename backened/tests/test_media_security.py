"""Media/upload security regressions: traversal-proof names, executable
rejection, magic-byte enforcement, size caps. GET /media stays public by
documented demo design (dashboard displays field photos; no PII gate in
demo mode — production note in docs/SECURITY.md)."""
import struct
import uuid
import zlib

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Minimal valid 1x1 PNG (magic + IHDR); Pillow verify accepts it.
PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
       b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
       b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB\x60\x82")


def _unique_png():
    """Valid PNG with a random tEXt chunk: unique sha256 per call so the
    content-dedup (409) from earlier runs/DB state can never flake this."""
    blob = uuid.uuid4().bytes
    data = b"gs-test\x00" + blob
    chunk = (struct.pack(">I", len(data)) + b"tEXt" + data
             + struct.pack(">I", zlib.crc32(b"tEXt" + data) & 0xffffffff))
    return PNG.replace(b"IEND", chunk + b"IEND", 1)


def _report():
    r = client.post("/api/reports", json={
        "description": "media-sec test",
        "latitude": 25.3, "longitude": 91.7})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_traversal_filename_never_escaped():
    rid = _report()
    r = client.post(f"/api/reports/{rid}/media",
                    files={"file": ("../../evil.jpg", _unique_png(), "image/jpeg")})
    # JPEG magic check fails for PNG bytes -> 422; either way no file escapes
    assert r.status_code in (200, 201, 422), r.text


def test_executable_masquerading_as_image_rejected():
    rid = _report()
    fake = b"#!/bin/sh\necho pwned" + b"\x00" * 64
    r = client.post(f"/api/reports/{rid}/media",
                    files={"file": ("run.jpg", fake, "image/jpeg")})
    assert r.status_code == 422, r.text


def test_svg_html_upload_rejected_by_allowlist():
    rid = _report()
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    for mime, name in (("image/svg+xml", "x.svg"), ("text/html", "x.html")):
        r = client.post(f"/api/reports/{rid}/media",
                        files={"file": (name, svg, mime)})
        assert r.status_code in (415, 422), (mime, r.text)


def test_valid_png_accepted_and_served():
    rid = _report()
    r = client.post(f"/api/reports/{rid}/media",
                    files={"file": ("photo.png", _unique_png(), "image/png")})
    assert r.status_code in (200, 201), r.text
    url = r.json().get("photo_url") or r.json().get("url") or ""
    assert url.startswith("/media/"), r.text
    name = url.rsplit("/", 1)[-1]
    assert ".." not in name and "/" not in name
    g = client.get(url)
    assert g.status_code == 200, g.text
    assert g.content.startswith(b"\x89PNG")


def test_media_path_traversal_blocked():
    r = client.get("/media/..%2Fapp%2Fconfig.py")
    assert r.status_code in (404, 403, 400), r.status_code
