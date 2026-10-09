# DAX query pack

[Open the DAX source](../powerbi/dax/churn-analysis.dax) to review nine reusable measures and four result sets: headline KPIs, plan comparisons, monthly-billing comparisons, and 20 baseline/edge-case assertions.

This is an extension for the supplied subscription-churn model. The measures are newly written examples; they are not extracted from the PBIX. The original PBIX remains unchanged.

## Run it in Power BI Desktop

1. Open [SubscriptionChurn.pbix](../powerbi/SubscriptionChurn.pbix).
2. Confirm the table is named `subscriptions_churn_clean`. The numeric columns `ألغى الاشتراك` and `حضر التهيئة` must use 0/1, as produced by the Python export. Retain the Arabic columns listed in the [data dictionary](DATA_DICTIONARY.md).
3. Open **DAX query view**, create a query tab, and paste the entire `.dax` file, including `DEFINE` and all `EVALUATE` sections.
4. Select **Run** and inspect all four result sets. Running a query evaluates its definitions for that query; saving model measures is a separate action. [Microsoft's query-view guide](https://learn.microsoft.com/en-us/power-bi/transform-model/dax-query-view) explains both actions.
5. To use the measures in visuals, review the definitions, then use **Update model: Add new measure** or **Update model with changes**. The `DaxBi` prefix distinguishes these examples from the original Arabic measures. Save your working copy after reviewing the results.

Report-page slicers do not supply the context for these standalone queries. The third result set applies monthly billing explicitly with `TREATAS`. Row-level security, if configured in a different model, still applies.

## Measure reference

| Measure | Purpose | Suggested model format |
|---|---|---|
| DaxBi Subscribers | Count rows in the current context | Whole number |
| DaxBi Churned | Count churned rows while respecting existing filters | Whole number |
| DaxBi Retained | Count retained rows while respecting existing filters | Whole number |
| DaxBi Churn Rate | Churned / subscribers | Percentage, 2 decimals |
| DaxBi Retention Rate | Retained / subscribers | Percentage, 2 decimals |
| DaxBi Average Support Tickets | Mean support demand in the segment | Decimal, 2 places |
| DaxBi Average Monthly Sessions | Mean engagement in the segment | Decimal, 2 places |
| DaxBi Plan Baseline Churn Rate | Churn rate after removing the plan-column filter | Percentage, 2 decimals |
| DaxBi Plan Gap pp | Segment rate minus plan baseline, in percentage points | Decimal, 2 places; label axis with `pp` |

Counts assume one row per subscriber. Do not reuse this row-count approach on a transaction table without reviewing its grain. The Python input checks enforce unique subscriber IDs.

## Filter behavior that matters

- `KEEPFILTERS` intersects the churn condition with existing filters. Selecting retained customers therefore gives zero churned customers, rather than replacing that selection. See [KEEPFILTERS](https://learn.microsoft.com/en-us/dax/keepfilters-function-dax).
- An empty selection returns zero counts and blank rates. A blank rate distinguishes "no subscribers" from an observed 0% cancellation rate. This differs intentionally from the older illustrative Arabic measure that supplies zero as `DIVIDE`'s alternate result.
- The plan baseline removes only the `الباقة` filter. Billing, payment, status, signup-date, and other filters remain. It compares against all plans available under those remaining filters, including plans excluded by a plan slicer; it is not a selected-plans-only benchmark. See [REMOVEFILTERS](https://learn.microsoft.com/en-us/dax/removefilters-function-dax).
- Do not average subgroup percentages to obtain the total. Divide total churned by total subscribers. The basic-plan gap is approximately **+2.50 percentage points**, not a 2.50% relative increase.
- Filtering to churned customers makes their churn rate 100%. For a retention-comparison page, avoid a churn-status slicer unless that conditional interpretation is intended.

## Expected original-sample results

| Scope | Subscribers | Churned | Churn rate |
|---|---:|---:|---:|
| All subscribers | 2,400 | 223 | 9.2917% |
| Basic plan | 738 | 87 | 11.7886% |
| Annual billing | 907 | 67 | 7.3870% |
| Monthly billing | 1,493 | 156 | 10.4488% |
| Attended onboarding | 1,314 | 98 | 7.4581% |

These expectations come from the committed [metrics](../reports/results/metrics.json) and [segment results](../reports/results/segment_churn.csv). They are comparison values in the fourth query, not hard-coded values in the nine measures. The fourth result set should have 20 `TRUE` values in its `Pass` column for the original, unrestricted model.

The checks cover totals, segment filters, plan-baseline behavior, conflicting status filters, and empty selections. If the dataset changes, review expected values instead of treating a failed historical baseline as proof that the DAX is wrong.

## Suggested report extension

Create a **Retention comparisons** page in your working PBIX:

- Cards: subscribers, churned, and churn rate.
- Matrix: plan rows; subscriber count, churn rate, baseline rate, and gap in percentage points as values.
- Slicers: billing cycle and payment method.
- Tooltips: average support tickets and monthly sessions.

Use a positive gap to flag a segment for investigation, with its sample size visible. This is an observational comparison, not a prediction or a measured benefit from a retention intervention. Signup dates do not represent cancellation dates, so the model does not support a monthly cancellation trend.

## Validation status

The source, column references, and published aggregate results are checked by `python scripts/validate_portfolio.py`. The existing Python tests use synthetic data. Neither check executes DAX. Native Power BI execution of this new query pack remains pending; use the fourth result set and review the first three before adding the measures to a report.

Further reference: [DAX query syntax](https://learn.microsoft.com/en-us/dax/dax-queries).
