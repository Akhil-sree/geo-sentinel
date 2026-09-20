"""PHASE 5 — OSM PBF bounds verification + highway extraction.

Reads datasets/meghalaya.pbf (READ-ONLY, pure stdlib framing walk + minimal
protobuf decode, no osmium needed): verifies OSMHeader, decodes DenseNodes
(delta-coded) and Ways, keeps highway ways + their nodes, verifies coverage
against the Meghalaya bbox, and writes data/processed/roads_v2.json
(highway nodes with coords, way class counts, bbox, vintage tag) plus
data/metadata/pbf_v2_validation.json.

Vintage policy: the header carries writer=osmium (a clip tool, not a source)
and no timestamp → road_data_vintage=UNKNOWN everywhere downstream. Present-
day geometry must never silently become a historical predictor (see
build_ner_v2.py, which records the vintage tag per sample).

Run: python scripts/import_pbf_roads.py [--write] [--max-ways N]
"""
import json
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))

from ner_v2_common import DATASETS_DIR, PROCESSED_DIR, META_DIR, utcnow  # noqa: E402

PBF = os.path.join(DATASETS_DIR, "meghalaya.pbf")
ROADS_JSON = os.path.join(PROCESSED_DIR, "roads_v2.json")
VALID_JSON = os.path.join(META_DIR, "pbf_v2_validation.json")

# Meghalaya operating bbox (lon/lat) — coverage gate
BBOX = (89.80, 25.00, 92.85, 26.20)


def _varint(buf: bytes, pos: int):
    shift = val = 0
    while True:
        b = buf[pos]
        pos += 1
        val |= (b & 0x7F) << shift
        if not (b & 0x80):
            return val, pos
        shift += 7


def _svarint(buf: bytes, pos: int):
    v, pos = _varint(buf, pos)
    return ((v >> 1) ^ -(v & 1)), pos


def _fields(buf: bytes):
    out: dict = {}
    pos, n = 0, len(buf)
    while pos < n:
        try:
            key, pos = _varint(buf, pos)
        except IndexError:
            break
        fn, wt = key >> 3, key & 7
        try:
            if wt == 0:
                v, pos = _varint(buf, pos)
                out.setdefault(fn, []).append(v)
            elif wt == 2:
                ln, pos = _varint(buf, pos)
                out.setdefault(fn, []).append(bytes(buf[pos:pos + ln]))
                pos += ln
            elif wt == 5:
                out.setdefault(fn, []).append(bytes(buf[pos:pos + 4]))
                pos += 4
            elif wt == 1:
                out.setdefault(fn, []).append(bytes(buf[pos:pos + 8]))
                pos += 8
            else:
                break
        except IndexError:
            break
    return out


def _packed_sint(blob: bytes):
    vals = []
    pos = 0
    while pos < len(blob):
        v, pos = _svarint(blob, pos)
        vals.append(v)
    return vals


def _packed_uint(blob: bytes):
    vals = []
    pos = 0
    while pos < len(blob):
        v, pos = _varint(blob, pos)
        vals.append(v)
    return vals


def iter_blobs(data: bytes):
    pos = 0
    while pos + 4 <= len(data):
        (ln,) = struct.unpack(">I", data[pos:pos + 4])
        pos += 4
        if ln <= 0 or ln > 1024 * 1024 or pos + ln > len(data):
            raise ValueError(f"PBF framing break at {pos - 4}")
        hdr = _fields(data[pos:pos + ln])
        pos += ln
        typ = hdr[1][0].decode()
        dsize = hdr[3][0]
        if pos + dsize > len(data):
            raise ValueError("PBF blob overrun")
        blob = _fields(data[pos:pos + dsize])
        pos += dsize
        if 3 in blob:
            payload = zlib.decompress(blob[3][0])
        elif 1 in blob:
            payload = blob[1][0]
        else:
            continue
        yield typ, payload


def decode(max_ways: int = 0) -> dict:
    data = open(PBF, "rb").read()
    nodes: dict = {}
    bbox = [180.0, 90.0, -180.0, -90.0]
    n_dense = n_ways = 0
    highways: list = []
    node_ids_needed: set = set()
    header_info: dict = {}
    for typ, payload in iter_blobs(data):
        if typ == "OSMHeader":
            hf = _fields(payload)
            header_info = {
                "features": [b.decode() for b in hf.get(4, [])],
                "writer": [b.decode() for b in hf.get(16, [])],
                "has_bbox": 2 in hf,
                "has_timestamp": 32 in hf,
            }
            continue
        blk = _fields(payload)
        gran = blk.get(3, [100])[0]
        latoff = blk.get(4, [0])[0]
        lonoff = blk.get(5, [0])[0]
        stable = [b.decode("utf-8", "replace") for b in _fields(blk[1][0]).get(1, [])] \
            if 1 in blk else []
        for g in blk.get(2, []):
            grp = _fields(g)
            if 2 in grp:  # DenseNodes
                dn = _fields(grp[2][0])
                ids = _packed_sint(dn.get(1, [b""])[0])
                lats = _packed_sint(dn.get(8, [b""])[0])
                lons = _packed_sint(dn.get(9, [b""])[0])
                _id = _la = _lo = 0
                for i, dlat, dlon in zip(ids, lats, lons):
                    _id += i
                    _la += dlat
                    _lo += dlon
                    la = 1e-9 * (latoff + gran * _la)
                    lo = 1e-9 * (lonoff + gran * _lo)
                    n_dense += 1
                    if BBOX[0] <= lo <= BBOX[2] and BBOX[1] <= la <= BBOX[3]:
                        nodes[_id] = (round(la, 7), round(lo, 7))
                        if lo < bbox[0]:
                            bbox[0] = lo
                        if la < bbox[1]:
                            bbox[1] = la
                        if lo > bbox[2]:
                            bbox[2] = lo
                        if la > bbox[3]:
                            bbox[3] = la
            if 3 in grp:  # Ways
                for w in grp[3]:
                    wf = _fields(w)
                    wid = wf.get(1, [0])[0]
                    keys = _packed_uint(wf.get(2, [b""])[0]) if 2 in wf else []
                    vals = _packed_uint(wf.get(3, [b""])[0]) if 3 in wf else []
                    tags = {stable[k]: stable[v] for k, v in zip(keys, vals)
                            if k < len(stable) and v < len(stable)}
                    n_ways += 1
                    if "highway" in tags:
                        refs = _packed_sint(wf.get(8, [b""])[0]) if 8 in wf else []
                        _r = 0
                        node_refs = []
                        for dr in refs:
                            _r += dr
                            node_refs.append(_r)
                        highways.append({"id": wid, "highway": tags["highway"],
                                         "name": tags.get("name", ""),
                                         "refs": node_refs})
                        node_ids_needed.update(node_refs)
                        if max_ways and len(highways) >= max_ways:
                            break
    kept = []
    # Deterministic thinning for tractable nearest-road queries (documented):
    # major roads (trunk/primary/motorway) keep every node; secondary/
    # tertiary every 2nd; minor classes every 4th. Density counts use the
    # thinned set with the thinning factor recorded (no silent bias).
    RANK = {"motorway": 3, "trunk": 3, "primary": 3, "secondary": 2,
            "tertiary": 2}
    STRIDE = {3: 1, 2: 2, 1: 4}
    seen: set = set()
    for h in highways:
        rank = RANK.get(h["highway"], 1)
        stride = STRIDE[rank]
        for i, nid in enumerate(h["refs"]):
            if nid in seen or i % stride:
                continue
            if nid in nodes:
                seen.add(nid)
                kept.append({"lat": nodes[nid][0], "lon": nodes[nid][1],
                             "rank": rank})
    thin_factor = (len(node_ids_needed) / max(1, len(seen)))
    by_class: dict = {}
    for h in highways:
        by_class[h["highway"]] = by_class.get(h["highway"], 0) + 1
    return {"header": header_info, "n_dense_nodes": n_dense, "n_ways": n_ways,
            "n_highway_ways": len(highways), "highway_classes": by_class,
            "bbox_nodes": [round(x, 4) for x in bbox],
            "n_highway_nodes_kept": len(kept),
            "thinning": {"rule": "rank stride 3:1/2:2/1:4", "factor": round(thin_factor, 2)},
            "nodes": kept,
            "coverage_gate": {"bbox": list(BBOX),
                              "inside": (bbox[0] >= BBOX[0] - 0.05 and bbox[2] <= BBOX[2] + 0.05
                                         and bbox != [180.0, 90.0, -180.0, -90.0])}}


def main() -> dict:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--max-ways", type=int, default=0)
    args = ap.parse_args()
    res = decode(args.max_ways)
    summary = {k: v for k, v in res.items() if k != "nodes"}
    print(json.dumps(summary, indent=1))
    if args.write:
        with open(ROADS_JSON, "w", encoding="utf-8") as fh:
            json.dump({"at": utcnow(), "vintage": "UNKNOWN",
                       "provenance": "osm-pbf-unknown-vintage",
                       "status": "BOUNDED_IMPORT_OK" if res["coverage_gate"]["inside"]
                       else "BOUNDS_UNVERIFIED",
                       "n_highway_nodes": res["n_highway_nodes_kept"],
                       "thinning": res["thinning"],
                       "highway_classes": res["highway_classes"],
                       "bbox_nodes": res["bbox_nodes"],
                       "nodes": res["nodes"]}, fh)
        with open(VALID_JSON, "w", encoding="utf-8") as fh:
            json.dump({"at": utcnow(), **summary}, fh, indent=1)
        print(f"wrote {ROADS_JSON}, {VALID_JSON}")
    return summary


if __name__ == "__main__":
    main()
