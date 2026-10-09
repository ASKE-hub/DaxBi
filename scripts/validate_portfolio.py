"""Check published aggregates, local documentation links, and DAX references.

Uses only the Python standard library and committed aggregate results.
This is not a DAX parser or runtime test; execute the query pack in Power BI.
"""

from collections import defaultdict
import csv
import json
import math
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def equal(actual, expected, label):
    require(math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-12),
            f"{label}: expected {expected}, got {actual}")


def check_aggregates():
    results = ROOT / "reports/results"
    metrics = json.loads((results / "metrics.json").read_text(encoding="utf-8-sig"))
    total, churned, retained = (metrics[k] for k in ("subscribers", "churned", "retained"))
    require(all(type(n) is int and n >= 0 for n in (total, churned, retained)) and total > 0,
            "Headline counts must be non-negative integers with a positive total")
    equal(churned + retained, total, "Headline counts")
    equal(metrics["churn_rate"], churned / total, "Overall churn rate")

    groups = defaultdict(list)
    seen = set()
    with (results / "segment_churn.csv").open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            key = (row["feature"], row["segment"])
            require(key not in seen, f"Duplicate segment: {key}")
            seen.add(key)
            n, c = int(row["subscribers"]), int(row["churned"])
            require(n > 0 and 0 <= c <= n, f"Invalid counts for {key}")
            equal(float(row["churn_rate"]), c / n, f"Segment rate for {key}")
            groups[row["feature"]].append((n, c))
    require(set(groups) == {"الباقة", "دورة الفوترة", "وسيلة الدفع", "حضر التهيئة"},
            "Expected plan, billing, payment, and onboarding segment results")
    for feature, rows in groups.items():
        equal(sum(n for n, _ in rows), total, f"Subscriber partition for {feature}")
        equal(sum(c for _, c in rows), churned, f"Churn partition for {feature}")

    model = metrics["model"]
    matrix = model["confusion_matrix"]
    require(len(matrix) == 2 and all(len(row) == 2 for row in matrix),
            "Expected a 2x2 confusion matrix")
    require(all(type(n) is int and n >= 0 for row in matrix for n in row),
            "Confusion-matrix entries must be non-negative integers")
    (tn, fp), (fn, tp) = matrix
    n = tn + fp + fn + tp
    require(n > 0 and tp + fp > 0 and tp + fn > 0, "Undefined baseline model metrics")
    equal(n, model["test_size"], "Test size")
    equal(tp + fn, model["test_churned"], "Test churn cases")
    equal((tn + tp) / n, model["accuracy"], "Accuracy")
    equal(tp / (tp + fp), model["precision"], "Precision")
    equal(tp / (tp + fn), model["recall"], "Recall")
    equal(2 * tp / (2 * tp + fp + fn), model["f1"], "F1")
    equal((tn + fp) / n, model["always_retained_accuracy"], "Majority baseline")
    equal((tp + fn) / n, model["test_churn_prevalence"], "Test prevalence")
    return len(seen)


def check_links():
    count = 0
    for path in ROOT.rglob("*.md"):
        if any(part.startswith(".") for part in path.relative_to(ROOT).parts):
            continue
        content = path.read_text(encoding="utf-8-sig")
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", content):
            url = urlsplit(target.strip().strip("<>"))
            if url.scheme or url.netloc or not url.path:
                continue
            resolved = (path.parent / unquote(url.path)).resolve()
            require(resolved.is_relative_to(ROOT) and resolved.exists(),
                    f"Broken local link in {path.relative_to(ROOT)}: {target}")
            count += 1
    return count


def check_dax_references():
    source = (ROOT / "powerbi/dax/churn-analysis.dax").read_text(encoding="utf-8")
    dictionary = (ROOT / "docs/DATA_DICTIONARY.md").read_text(encoding="utf-8")
    columns = set(re.findall(r"^\| ([^|\n]+?) \|", dictionary, re.MULTILINE))
    definitions = re.findall(r"MEASURE 'subscriptions_churn_clean'\[(DaxBi [^]]+)\]", source)
    require(definitions and len(definitions) == len(set(definitions)), "Missing or duplicate DAX measures")
    for name in re.findall(r"'subscriptions_churn_clean'\[([^]]+)\]", source):
        require(name in columns or name in definitions, f"Unknown DAX table field: {name}")
    for name in re.findall(r"\[(DaxBi [^]]+)\]", source):
        require(name in definitions, f"Undefined DAX measure: {name}")
    return len(definitions)


def main():
    try:
        segments = check_aggregates()
        links = check_links()
        measures = check_dax_references()
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: {segments} segment rows reconcile with headline and model metrics.")
    print(f"PASS: {links} local documentation links resolve.")
    print(f"PASS: {measures} DAX measure definitions have known field references.")
    print("DAX execution is a separate Power BI check; it was not run by this script.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
