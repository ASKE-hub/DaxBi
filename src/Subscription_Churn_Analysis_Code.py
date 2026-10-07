"""Subscription churn analysis by Abubkr Sami.

Run from the repository root:
    python src/Subscription_Churn_Analysis_Code.py --input data/raw/subscriptions-churn.csv

The Arabic source column names are preserved for Power BI compatibility.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import chi2_contingency, ttest_ind
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, average_precision_score, confusion_matrix, f1_score,
    precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parents[1]
TARGET = "ألغى الاشتراك"
ONBOARDING = "حضر التهيئة"
NUMERIC = ["السعر الشهري", "أشهر البقاء", "تذاكر الدعم", "متوسط الجلسات الشهرية", "نسبة الخصم"]
CATEGORICAL = ["الباقة", "دورة الفوترة", "وسيلة الدفع"]
REQUIRED = ["معرف المشترك", "تاريخ الاشتراك", *NUMERIC, *CATEGORICAL, ONBOARDING, TARGET]


def load_and_clean(path: Path) -> pd.DataFrame:
    """Validate the source schema, then parse dates and Arabic binary labels."""
    if not path.is_file():
        raise ValueError(f"Dataset not found: {path}. See data/README.md for the required file.")
    df = pd.read_csv(path, encoding="utf-8-sig")
    missing = sorted(set(REQUIRED) - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    if df.empty or df[REQUIRED].isna().any().any():
        raise ValueError("The dataset must contain rows and have no missing required values.")
    if df.duplicated().any() or df["معرف المشترك"].duplicated().any():
        raise ValueError("Expected one unique row per subscriber; duplicate records were found.")
    for col in CATEGORICAL + ["معرف المشترك"]:
        if df[col].astype(str).str.strip().eq("").any():
            raise ValueError(f"Blank values are not allowed in {col}.")
    df["تاريخ الاشتراك"] = pd.to_datetime(df["تاريخ الاشتراك"], errors="coerce")
    if df["تاريخ الاشتراك"].isna().any():
        raise ValueError("Invalid subscription dates were found.")
    for col in [TARGET, ONBOARDING]:
        if not df[col].isin(["نعم", "لا"]).all():
            raise ValueError(f"{col} must contain only the Arabic values نعم or لا.")
        df[col] = df[col].map({"لا": 0, "نعم": 1})
    for col in NUMERIC:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if not np.isfinite(df[col]).all() or (df[col] < 0).any():
            raise ValueError(f"{col} must contain finite, non-negative numeric values.")
    if (df["نسبة الخصم"] > 100).any():
        raise ValueError("Discount percentages must fall between 0 and 100.")
    if df[TARGET].nunique() != 2 or df[TARGET].value_counts().min() < 4:
        raise ValueError("Both churn classes need at least four observations for a stratified split.")
    return df


def numeric_effects(df: pd.DataFrame) -> pd.DataFrame:
    """Welch tests and pooled-SD Cohen's d (churned minus retained)."""
    rows = []
    for col in NUMERIC:
        stayed = df.loc[df[TARGET] == 0, col]
        churned = df.loc[df[TARGET] == 1, col]
        _, p = ttest_ind(churned, stayed, equal_var=False)
        pooled_sd = np.sqrt(
            ((len(churned) - 1) * churned.var() + (len(stayed) - 1) * stayed.var())
            / (len(churned) + len(stayed) - 2)
        )
        effect = (churned.mean() - stayed.mean()) / pooled_sd if pooled_sd else np.nan
        rows.append([col, churned.mean(), stayed.mean(), effect, p])
    return pd.DataFrame(rows, columns=["feature", "churned_mean", "retained_mean", "cohens_d", "p_value"])


def categorical_effects(df: pd.DataFrame) -> pd.DataFrame:
    """Chi-square tests with SciPy's default continuity correction for 2x2 tables."""
    rows = []
    for col in CATEGORICAL + [ONBOARDING]:
        table = pd.crosstab(df[col], df[TARGET])
        if min(table.shape) < 2:
            raise ValueError(f"At least two categories are required in {col}.")
        chi2, p, _, expected = chi2_contingency(table)
        v = np.sqrt(chi2 / (table.values.sum() * (min(table.shape) - 1)))
        rows.append([col, v, p, expected.min()])
    return pd.DataFrame(rows, columns=["feature", "cramers_v", "p_value", "minimum_expected_count"])


def adjusted_odds(df: pd.DataFrame) -> pd.DataFrame:
    """Full-sample explanatory model, separate from held-out predictive evaluation."""
    model_df = df.rename(columns={
        "الباقة": "plan", "دورة الفوترة": "billing", "أشهر البقاء": "tenure",
        "وسيلة الدفع": "payment", "تذاكر الدعم": "support",
        "متوسط الجلسات الشهرية": "sessions", "نسبة الخصم": "discount",
        ONBOARDING: "onboarding", TARGET: "churn",
    }).copy()
    scale_cols = ["tenure", "support", "sessions", "discount"]
    model_df[[c + "_z" for c in scale_cols]] = StandardScaler().fit_transform(model_df[scale_cols])
    x = model_df[["tenure_z", "support_z", "sessions_z", "discount_z", "onboarding", "plan", "billing", "payment"]]
    x = pd.get_dummies(x, columns=["plan", "billing", "payment"], drop_first=True, dtype=int)
    x = sm.add_constant(x)
    result = sm.Logit(model_df["churn"], x).fit(disp=False)
    if not result.mle_retvals["converged"]:
        raise ValueError("The explanatory logistic regression did not converge.")
    ci = result.conf_int()
    return pd.DataFrame({
        "odds_ratio": np.exp(result.params), "ci_lower": np.exp(ci[0]),
        "ci_upper": np.exp(ci[1]), "p_value": result.pvalues,
    }).drop("const").rename_axis("feature").reset_index()


def evaluate_model(df: pd.DataFrame) -> dict:
    """Fit preprocessing on training data only; evaluate at the 0.5 threshold."""
    features = CATEGORICAL + NUMERIC + [ONBOARDING]
    prep = ColumnTransformer([
        ("num", StandardScaler(), NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
        ("bin", "passthrough", [ONBOARDING]),
    ])
    model = Pipeline([
        ("prep", prep),
        ("model", LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)),
    ])
    x_train, x_test, y_train, y_test = train_test_split(
        df[features], df[TARGET], test_size=0.25, stratify=df[TARGET], random_state=42,
    )
    model.fit(x_train, y_train)
    predicted = model.predict(x_test)
    probability = model.predict_proba(x_test)[:, 1]
    return {
        "test_size": len(y_test), "test_churned": int(y_test.sum()),
        "random_state": 42, "decision_threshold": 0.5,
        "accuracy": float(accuracy_score(y_test, predicted)),
        "precision": float(precision_score(y_test, predicted, zero_division=0)),
        "recall": float(recall_score(y_test, predicted, zero_division=0)),
        "f1": float(f1_score(y_test, predicted, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, probability)),
        "average_precision": float(average_precision_score(y_test, probability)),
        "confusion_matrix": confusion_matrix(y_test, predicted, labels=[0, 1]).tolist(),
        "always_retained_accuracy": float((y_test == 0).mean()),
        "test_churn_prevalence": float(y_test.mean()),
    }


def export_power_bi(df: pd.DataFrame, path: Path) -> None:
    """Create the same Arabic fields used by the supplied Power BI dashboard."""
    pbi = df.copy()
    pbi["حالة الاشتراك"] = pbi[TARGET].map({0: "مستمر", 1: "ملغي"})
    pbi["حالة التهيئة"] = pbi[ONBOARDING].map({0: "لم يحضر", 1: "حضر"})
    pbi["سنة الاشتراك"] = pbi["تاريخ الاشتراك"].dt.year
    pbi["شهر الاشتراك"] = pbi["تاريخ الاشتراك"].dt.month
    path.parent.mkdir(parents=True, exist_ok=True)
    pbi.to_csv(path, index=False, encoding="utf-8-sig")


def make_overview(df: pd.DataFrame, path: Path) -> None:
    """Generate a portfolio visual from observed rates, not a Power BI screenshot."""
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
    fig = plt.figure(figsize=(14, 8), facecolor="#f4f7fb")
    fig.text(0.065, 0.935, "SUBSCRIPTION CHURN", fontsize=27, weight="bold", color="#13263e")
    fig.text(0.065, 0.89, "Python analysis  /  Power BI reporting  /  Abubkr Sami", color="#51647a", fontsize=12)
    cards = [("SUBSCRIPTIONS", f"{len(df):,}"), ("CHURNED", f"{int(df[TARGET].sum()):,}"),
             ("CHURN RATE", f"{df[TARGET].mean():.2%}"), ("RETAINED", f"{int((df[TARGET] == 0).sum()):,}")]
    for i, (label, value) in enumerate(cards):
        x = 0.065 + i * 0.237
        fig.text(x, 0.79, label, fontsize=10, color="#51647a", weight="bold")
        fig.text(x, 0.725, value, fontsize=28, color="#147d92", weight="bold")
    ax = fig.add_axes([0.21, 0.17, 0.70, 0.46], facecolor="#f4f7fb")
    specs = [("الباقة", "أساسي", "Basic plan"), ("الباقة", "أعمال", "Business plan"),
             ("الباقة", "متقدم", "Advanced plan"), ("دورة الفوترة", "شهري", "Monthly billing"),
             ("دورة الفوترة", "سنوي", "Annual billing"), (ONBOARDING, 0, "No onboarding"),
             (ONBOARDING, 1, "Attended onboarding")]
    rates = [df.loc[df[col] == value, TARGET].mean() * 100 for col, value, _ in specs]
    if any(pd.isna(rates)):
        plt.close(fig)
        raise ValueError("The overview requires the original plan, billing and onboarding categories.")
    ax.barh(range(len(specs)), rates, height=0.60, color=["#147d92", "#91bdc7", "#91bdc7", "#147d92", "#91bdc7", "#147d92", "#91bdc7"])
    ax.set_yticks(range(len(specs)), [label for _, _, label in specs])
    ax.invert_yaxis()
    upper = max(max(rates), df[TARGET].mean() * 100) * 1.27
    ax.set_xlim(0, upper)
    ax.set_xlabel("Observed churn rate (%)", labelpad=10, color="#51647a")
    ax.set_title("Where churn is higher", loc="left", fontsize=15, pad=16, weight="bold", color="#13263e")
    baseline = df[TARGET].mean() * 100
    ax.axvline(baseline, color="#de7a50", linestyle="--", linewidth=1.5, label=f"Overall: {baseline:.2f}%")
    for i, value in enumerate(rates):
        ax.text(value + upper * 0.012, i, f"{value:.2f}%", va="center", color="#13263e", weight="bold")
    ax.legend(loc="lower right", frameon=False, fontsize=10)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis="both", length=0, labelcolor="#33465d")
    ax.grid(axis="x", alpha=0.12)
    ax.set_axisbelow(True)
    fig.text(0.065, 0.055, "Observed associations support retention experiments; they do not establish causation.", fontsize=11, color="#51647a")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)


def run_analysis(input_path: Path, output_dir: Path, power_bi_path: Path) -> dict:
    df = load_and_clean(input_path)
    numeric = numeric_effects(df)
    categorical = categorical_effects(df)
    odds = adjusted_odds(df)
    metrics = evaluate_model(df)
    output_dir.mkdir(parents=True, exist_ok=True)
    numeric.to_csv(output_dir / "numeric_effects.csv", index=False, encoding="utf-8-sig")
    categorical.to_csv(output_dir / "categorical_effects.csv", index=False, encoding="utf-8-sig")
    odds.to_csv(output_dir / "adjusted_odds_ratios.csv", index=False, encoding="utf-8-sig")
    segments = []
    for col in CATEGORICAL + [ONBOARDING]:
        table = df.groupby(col)[TARGET].agg(subscribers="count", churned="sum", churn_rate="mean")
        table = table.rename_axis("segment").reset_index()
        table.insert(0, "feature", col)
        segments.append(table)
    pd.concat(segments, ignore_index=True).to_csv(output_dir / "segment_churn.csv", index=False, encoding="utf-8-sig")
    summary = {
        "subscribers": len(df), "churned": int(df[TARGET].sum()),
        "retained": int((df[TARGET] == 0).sum()), "churn_rate": float(df[TARGET].mean()),
        "model": metrics,
    }
    (output_dir / "metrics.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    export_power_bi(df, power_bi_path)
    make_overview(df, output_dir / "churn_overview.png")
    return summary


def main() -> None:
    plt.switch_backend("Agg")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=ROOT / "data/raw/subscriptions-churn.csv")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports/results")
    parser.add_argument("--power-bi-output", type=Path, default=ROOT / "data/processed/subscriptions_churn_clean.csv")
    args = parser.parse_args()
    destinations = [args.power_bi_output] + [args.output_dir / name for name in [
        "numeric_effects.csv", "categorical_effects.csv", "adjusted_odds_ratios.csv",
        "segment_churn.csv", "metrics.json", "churn_overview.png",
    ]]
    if args.input.resolve() in [p.resolve() for p in destinations]:
        parser.error("An output path cannot overwrite the input dataset.")
    try:
        summary = run_analysis(args.input, args.output_dir, args.power_bi_output)
    except (ValueError, OSError, np.linalg.LinAlgError) as exc:
        parser.exit(1, f"Analysis could not complete: {exc}\n")
    print(json.dumps(summary, indent=2))
    print(f"Analysis saved to: {args.output_dir.resolve()}")
    print(f"Power BI data saved to: {args.power_bi_output.resolve()}")


if __name__ == "__main__":
    main()
