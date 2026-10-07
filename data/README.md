# Dataset setup

The analysis expects the original **subscriptions-churn.csv**, containing 2,400 subscriber records and 12 Arabic columns. One row represents one subscriber. The source CSV is not included in this repository; the author's supplied Power BI file does contain an embedded data model.

Create `data/raw/` if necessary and place the original CSV there. Alternatively provide its path with the script's `--input` argument or the notebook's `CHURN_DATA_PATH` environment variable.

The script creates `data/processed/subscriptions_churn_clean.csv` with Arabic display labels and subscription year/month fields for Power BI. Both raw and processed subscriber-level CSVs are ignored by Git. Aggregate outputs are versioned in `reports/results/`.

Use UTF-8 encoding and retain the original Arabic labels. The binary input values are `نعم` and `لا`; a previously cleaned 0/1 CSV is not the raw input expected by the script. See [the data dictionary](../docs/DATA_DICTIONARY.md).

## Provenance

The supplied project folder identifies the Arab Data Community (مجتمع البيانات العربي). A dataset source URL, license, and confirmation of whether the data is synthetic were not supplied. These details should be established before redistributing a standalone dataset or treating the sample as representative of an actual business.
