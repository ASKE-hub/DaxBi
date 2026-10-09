# Validation notes

Validation date: **2026-09-27**. Environment: Windows, Python **3.13.9**, with the installed package versions recorded in `requirements.txt` and `requirements-notebook.txt`. A separate fresh-environment installation was not tested.

## Checks

- Run the portable Python script against the source CSV referenced by the supplied project.
- Compare record counts, churn prevalence, model metrics, the confusion matrix, and adjusted odds ratios with the original Arabic report and saved notebook results.
- Compare the 16-column Power BI export with the existing cleaned CSV, normalizing date strings to actual dates before comparison. The existing CSV uses month/day/year strings; the script exports ISO dates.
- Execute the notebook from top to bottom and validate its notebook structure.
- Run seven automated input-validation/export checks using a small synthetic fixture.
- Check local Markdown links and inspect the generated overview chart.
- Compare SHA-256 hashes of the copied PDF and PBIX with the originals; inspect PBIX archive integrity and report definitions.

## Reproduced results

| Check | Result |
|---|---|
| Records / churned / retained | 2,400 / 223 / 2,177 |
| Churn rate | 9.2917% |
| Test records / churn cases | 600 / 56 |
| Confusion matrix | TN = 350, FP = 194, FN = 29, TP = 27 |
| Accuracy / precision / recall | 0.628 / 0.122 / 0.482 |
| F1 / ROC-AUC / average precision | 0.195 / 0.628 / 0.135 |
| Adjusted odds ratios | Match the PDF at three decimal places |

To rerun the dataset-independent checks from the repository root:

```bash
python -m unittest discover -s tests -v
```

To reproduce analytical results, provide the original dataset as described in [data/README.md](../data/README.md) and run the analysis script or notebook. The generated fixture in the unit tests is only for input validation; it is never used for the project findings.

## DaxBi source extension — 2026-10-09

The repository now includes nine query-scoped DAX measures, segment comparisons, and 20 assertions for native Power BI review. Expected counts and rates are grounded in the committed aggregate results. These assertions have not been executed in a DAX engine here.

`python scripts/validate_portfolio.py` checks segment partitions and rates, confusion-matrix-derived metrics, local Markdown links, and DAX field/measure references. GitHub Actions runs this script and the existing seven synthetic-data tests. These are source and Python checks, not Power BI runtime verification.

Local verification on 2026-10-09: all seven Python tests passed; 10 segment rows reconciled; 27 local links resolved; and nine DAX measure definitions referenced known fields. The checker also rejected a deliberately inconsistent churn rate and a broken link in temporary test copies. The workflow YAML parsed successfully. Native DAX execution remains pending.

## Scope

The Power BI archive was inspected, but the report was not opened or refreshed in Power BI Desktop here. No automated test establishes the correctness of every dashboard calculation or interaction. The PDF and PBIX were preserved unchanged. The project reports observed associations and a held-out classification baseline; it does not claim production readiness or measured business impact.
