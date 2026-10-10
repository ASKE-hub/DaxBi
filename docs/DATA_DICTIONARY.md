# Data dictionary

The input has one row per subscriber. Column names remain in Arabic to match the original analysis and Power BI model.

| Source column | Meaning | Type / observed values | Analytical role |
|---|---|---|---|
| معرف المشترك | Subscriber ID | Unique text identifier | Quality checks only; excluded from models |
| تاريخ الاشتراك | Subscription date | Date | Parsed and used for Power BI year/month fields |
| الباقة | Subscription plan | أساسي (Basic), متقدم (Advanced), أعمال (Business) | Categorical feature |
| السعر الشهري | Monthly price | 39, 89, or 189 in the supplied sample; currency unspecified | Descriptive analysis and predictive model |
| دورة الفوترة | Billing cycle | شهري (Monthly), سنوي (Annual) | Categorical feature |
| أشهر البقاء | Tenure in months | Numeric, observed 1–30 | Numeric feature |
| وسيلة الدفع | Payment method | بطاقة (Card), تحويل (Transfer), محفظة (Wallet) | Categorical feature |
| تذاكر الدعم | Support-ticket count | Numeric, observed 0–11 | Numeric feature |
| متوسط الجلسات الشهرية | Average monthly sessions | Numeric, observed 2–59 | Numeric feature |
| نسبة الخصم | Discount percentage | Numeric, observed 0–25; stored in percentage points | Numeric feature |
| حضر التهيئة | Attended onboarding | نعم / لا, mapped to 1 / 0 | Binary feature |
| ألغى الاشتراك | Churn status | نعم / لا, mapped to 1 / 0 | Target |

## Subscriber identifier handling

The Python script explicitly loads `معرف المشترك` as text. Values such as `001` and `1`, or `1e3` and `1000`, remain distinct identifiers; long numeric-looking IDs also remain strings. Their text is preserved in the exported CSV. Empty IDs, whitespace-only IDs, and duplicate IDs are rejected. Default pandas missing-value markers such as `NULL` still count as missing values.

CSV files do not carry column types. When importing the export into Power BI, keep this column as **Text**, including in the query's first type-conversion step. Converting it to a number can remove leading zeros before a later conversion back to text. See the [refresh guide](POWER_BI.md).

## Derived Power BI fields

| Column | Derivation |
|---|---|
| حالة الاشتراك | مستمر for 0, ملغي for 1 |
| حالة التهيئة | لم يحضر for 0, حضر for 1 |
| سنة الاشتراك | Year of subscription date |
| شهر الاشتراك | Month number of subscription date |

Subscription year/month describe signup timing. They are not cancellation dates. Feature collection windows and the churn observation horizon are unspecified.

## Model coding

In the explanatory model, tenure, support, sessions, and discount are standardized using the full sample. The observed dummy-variable reference categories are Basic plan (`أساسي`), Annual billing (`سنوي`), and Transfer (`تحويل`). Onboarding is binary, with non-attendance as the reference.

In the predictive model, numeric scaling and categorical encoding are fitted on training records only. The subscriber ID and signup date are excluded. Full-sample explanatory coefficients are not used as inputs to the predictive model.
