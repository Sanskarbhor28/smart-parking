"""Print the saved evaluation metrics in a readable form.  Run: python -m ml.evaluate"""
from ml.predict import load_metrics
from ml.train import DEFAULT_MODEL_DIR


def main() -> None:
    m = load_metrics(DEFAULT_MODEL_DIR)
    print(f"Model version: {m['model_version']}\n{m['data_note']}\nRows: {m['rows']}\n")
    for h, r in m["regression"].items():
        print(f"== Occupancy in {h} (selected: {r['selected']}) ==")
        print(f"  {'baseline (no change)':22s} {r['baseline_no_change']['test']}")
        for name, v in r["models"].items():
            print(f"  {name:22s} {v['test']}")
    c = m["classification"]
    print(f"\n== Demand level (selected: {c['selected']}) ==  rule: {c['rule']}")
    for name, v in c["models"].items():
        print(f"  {name:22s} {v['test']}")
        print(f"    confusion matrix (rows=actual, cols=predicted, order {c['labels']}): {v['confusion_matrix']}")


if __name__ == "__main__":
    main()
