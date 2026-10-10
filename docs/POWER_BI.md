# Power BI report guide

Open [SubscriptionChurn.pbix](../powerbi/SubscriptionChurn.pbix) with Power BI Desktop. The supplied report has one Arabic page named **تحليل انسحاب العملاء**. The PBIX is preserved byte-for-byte from the original file; it has not been redesigned or re-saved in Power BI Desktop.

## What to review

1. Start with the four KPI cards: total subscribers, retained subscribers, churned subscribers, and churn rate.
2. Compare churn by plan, onboarding attendance, and billing cycle.
3. Compare average support tickets and average monthly sessions between churned and retained customers.
4. Use the plan, billing, and payment-method slicers to inspect segments. Reset all slicers before comparing the totals with the README.

## Refresh with a local CSV

1. Run the Python analysis to generate `data/processed/subscriptions_churn_clean.csv`.
2. Open the PBIX in Power BI Desktop and inspect the existing `subscriptions_churn_clean` query.
3. Update its file-source path to your generated CSV. The original source points to the author's local computer, so it may need to be changed before refresh.
4. Retain the Arabic column names and existing transformations; confirm the source uses UTF-8 and the promoted headers match the data dictionary. Keep `معرف المشترك` as **Text** from the first type-conversion step so numeric-looking identifiers retain their exact spelling. If an automatic step already converted it to a number, edit that step and reload from the CSV; changing the type back afterward cannot recover lost zeros.
5. Apply the change and refresh the report.
6. With all slicers cleared, verify **2,400 total**, **2,177 retained**, **223 churned**, and **9.29% churn** against the supplied dataset.

The exact placement of source settings can vary with Power BI Desktop version. Review the current query before editing it rather than creating a second table with a different name.

## DAX query pack

The [DAX guide](DAX_GUIDE.md) introduces nine new measures, plan comparisons, and 20 checks in [churn-analysis.dax](../powerbi/dax/churn-analysis.dax). Run that complete file in DAX query view to inspect the calculations before adding measures to a working copy. It includes explicit filter-context examples and handles empty selections with blank rates. The original PBIX has not been changed to include these measures.

## Suggested measure definitions

The report definition references the following measure names. These are equivalent suggested definitions for a model with one row per subscriber; they were not extracted from the binary semantic model and should not be treated as a verbatim export of its existing DAX. Add each measure separately if rebuilding the report.

```dax
إجمالي العملاء = COUNTROWS('subscriptions_churn_clean')
```

```dax
العملاء الملغين =
CALCULATE(
    [إجمالي العملاء],
    KEEPFILTERS('subscriptions_churn_clean'[ألغى الاشتراك] = 1)
)
```

```dax
العملاء المستمرين =
CALCULATE(
    [إجمالي العملاء],
    KEEPFILTERS('subscriptions_churn_clean'[ألغى الاشتراك] = 0)
)
```

```dax
نسبة الإلغاء = DIVIDE([العملاء الملغين], [إجمالي العملاء], 0)
```

Format the last measure as a percentage. Compare rates together with segment sizes; a high rate in a small subgroup may be unstable.

## Preview and validation scope

GitHub cannot run the report's slicers directly. Download the PBIX for interactive review. The README image is a Python-generated summary, not a screenshot of the Power BI report.

The PBIX archive and report definitions were inspected successfully. Interactive rendering, semantic-model calculation, and refresh were not tested in Power BI Desktop in this environment.
