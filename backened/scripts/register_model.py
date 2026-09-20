"""Model registration reporter (SIH §31).

python scripts/register_model.py --model ner_rf --version ner_v1_v1

Runs the promotion gate for one registry entry and prints the verdict.
Registration itself happens in train_models.py; this script NEVER flips
status to PROMOTED (human decision after reading the audit reports).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def main() -> dict:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--version", required=True)
    args = ap.parse_args()
    from app.ml import registry as reg
    gate = reg.evaluate_promotion(args.model, args.version)
    entry = next((m for m in reg.all_models()
                  if m["model_id"] == args.model and m["version"] == args.version), {})
    print(f"model={args.model} version={args.version}")
    print(f"verdict={gate['verdict']}")
    for r in gate.get("reasons", []):
        print(f"  blocked: {r}")
    print(f"artifact={entry.get('artifact_hash')} calibration={entry.get('calibration_status')}")
    print("note: promotion to PROMOTED is a human decision — this script never auto-promotes.")
    return gate


if __name__ == "__main__":
    main()
