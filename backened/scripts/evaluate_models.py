"""Evaluate ner models + run promotion gate (SIH PHASE 17-19 → §29/§31).

python scripts/evaluate_models.py --dataset ner_v1

Reads registry entries for the dataset, prints the model audit table, runs
evaluate_promotion() for each (records BLOCKED reasons, never auto-promotes).
Exit 0 with a report either way — a BLOCKED gate is a result, not a failure.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def main() -> dict:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="ner_v1")
    args = ap.parse_args()
    from app.ml import registry as reg
    rows = [m for m in reg.all_models()
            if m.get("dataset_version") == args.dataset and m["model_id"].startswith("ner_")]
    print(f"{'model':<12}{'n':>4}{'+':>4}{'-':>4}  {'CV-F1':>7} {'holdout-F1':>10} "
          f"{'rec':>5} {'PR-AUC':>7} {'Brier':>6}  status")
    out = []
    for m in rows:
        mt = m.get("metrics", {})
        gate = reg.evaluate_promotion(m["model_id"], m["version"])
        print(f"{m['model_id']:<12}{mt.get('n_samples', 0):>4}{mt.get('n_pos', 0):>4}"
              f"{mt.get('n_neg', 0):>4}  {str(mt.get('cv_f1_mean')):>7} "
              f"{str(mt.get('f1')):>10} {str(mt.get('recall')):>5} "
              f"{str(mt.get('pr_auc')):>7} {str(mt.get('brier')):>6}  "
              f"{m.get('promotion_status', '')[:60]}")
        out.append({"model": m["model_id"], "verdict": gate["verdict"],
                    "reasons": gate["reasons"]})
    return {"dataset": args.dataset, "models": out}


if __name__ == "__main__":
    main()
