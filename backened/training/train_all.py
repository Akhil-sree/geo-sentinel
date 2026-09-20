"""GEO-SENTINEL training entry point (SIH §14).

  python -m training.train_all --model {rf,mamba,fusion,segformer,all} [--smoke]

Reuses the audited gs_v1 pipeline stages (scripts/train_geosentinel.py) —
no duplicated training logic. Writes experiments/<utc-timestamp>/ records.
"""
import argparse
import datetime
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPERIMENTS_DIR = os.path.join(os.path.dirname(BACKEND_DIR), "experiments")


def _load_yaml(name):
    import yaml
    with open(os.path.join(BACKEND_DIR, "configs", name), encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _record_experiment(results, log_lines):
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = os.path.join(EXPERIMENTS_DIR, ts)
    os.makedirs(os.path.join(dest, "model"), exist_ok=True)
    for cfg in ("datasets.yaml", "training.yaml", "models.yaml"):
        shutil.copy(os.path.join(BACKEND_DIR, "configs", cfg), dest)
    json.dump(results.get("checksums", {}),
              open(os.path.join(dest, "dataset_hashes.json"), "w"), indent=2)
    metrics = {k: results.get(k) for k in
               ("tabular", "mamba", "fusion", "heldout", "gis", "terrain_cv")}
    json.dump(metrics, open(os.path.join(dest, "metrics.json"), "w"),
              indent=2, default=str)
    open(os.path.join(dest, "training_log.txt"), "w",
         encoding="utf-8").write("\n".join(log_lines) + "\n")
    json.dump({"experiment": results.get("experiment"), "seed": results.get("seed"),
               "models_dir": "backened/models", "report": "training_report.md"},
              open(os.path.join(dest, "model", "pointers.json"), "w"), indent=2)
    return dest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="all",
                    choices=["rf", "mamba", "fusion", "segformer", "all"])
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()

    import train_geosentinel as gs
    from gs_common import SEGFORMER_STATUS, segformer_gate

    gs._rng()
    results = {"experiment": gs.EXPERIMENT, "seed": gs.SEED}
    log = [f"train_all --model {args.model} smoke={args.smoke}"]

    if args.model == "segformer":
        gate = segformer_gate()
        msg = (f"SEGFORMER_STATUS={SEGFORMER_STATUS}: training refused — "
               f"{gate['checks']}. Masks + valid pixels required.")
        print(msg)
        log.append(msg)
        _record_experiment(results, log)
        return 0  # BLOCKED gate is a result, not a failure

    rf_rows = gs.step_validate(results)
    gs.step_rf_audit(rf_rows, results)
    oof_tab = None
    if args.model in ("rf", "fusion", "all"):
        oof_tab, _ = gs.step_tabular(rf_rows, results, smoke=args.smoke)
    X = y = groups = sids = feats = None
    mamba_oof = None
    if args.model in ("mamba", "fusion", "all"):
        X, y, groups, sids, feats = gs.step_mamba_data(results)
        mamba_oof = gs.step_train_mamba(X, y, groups, feats, results,
                                        smoke=args.smoke)
    if args.model in ("fusion", "all"):
        gs.step_fusion(rf_rows, oof_tab["gs_rf"], mamba_oof, sids, y, results)
    if args.model == "all":
        core = gs.step_heldout(rf_rows, results, smoke=args.smoke)
        gs.step_explain(results)
        gs.step_gis(core, results, smoke=args.smoke)
        gs.step_report(results)
    dest = _record_experiment(results, log + ["DONE"])
    print(f"experiment record -> {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
