"""Data-contract and export checks. No private dataset is required.

Run: python -m unittest discover -s tests -v
"""

from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import Subscription_Churn_Analysis_Code as analysis


def fixture():
    """Small synthetic input for validation tests, not portfolio findings."""
    return pd.DataFrame({
        "معرف المشترك": [f"TEST-{i}" for i in range(8)],
        "تاريخ الاشتراك": ["2025-01-15"] * 8,
        "الباقة": ["أساسي", "متقدم"] * 4,
        "السعر الشهري": [39, 89] * 4,
        "دورة الفوترة": ["شهري", "سنوي"] * 4,
        "أشهر البقاء": list(range(1, 9)),
        "وسيلة الدفع": ["بطاقة", "محفظة"] * 4,
        "تذاكر الدعم": list(range(8)),
        "متوسط الجلسات الشهرية": list(range(10, 18)),
        "نسبة الخصم": [0, 10] * 4,
        "حضر التهيئة": ["نعم", "لا"] * 4,
        "ألغى الاشتراك": ["لا"] * 4 + ["نعم"] * 4,
    })


class DataContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "source.csv"

    def load(self, data):
        data.to_csv(self.path, index=False, encoding="utf-8-sig")
        return analysis.load_and_clean(self.path)

    def test_raw_source_unchanged_and_arabic_values_round_trip(self):
        original = fixture()
        original.to_csv(self.path, index=False, encoding="utf-8-sig")
        before = self.path.read_bytes()
        clean = analysis.load_and_clean(self.path)
        output = Path(self.tmp.name) / "nested/processed.csv"
        analysis.export_power_bi(clean, output)
        exported = pd.read_csv(output)
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual(exported.shape, (8, 16))
        self.assertEqual(exported["حالة الاشتراك"].tolist(), ["مستمر"] * 4 + ["ملغي"] * 4)
        self.assertEqual(exported["حالة التهيئة"].tolist(), ["حضر", "لم يحضر"] * 4)
        self.assertTrue(exported["سنة الاشتراك"].eq(2025).all())
        self.assertTrue(exported["شهر الاشتراك"].eq(1).all())

    def test_rejects_missing_column(self):
        with self.assertRaisesRegex(ValueError, "Missing required columns"):
            self.load(fixture().drop(columns=[analysis.TARGET]))

    def test_rejects_unrecognized_target_instead_of_silently_mapping_to_null(self):
        data = fixture()
        data.loc[0, analysis.TARGET] = "unknown"
        with self.assertRaises(ValueError):
            self.load(data)

    def test_rejects_invalid_dates(self):
        data = fixture()
        data.loc[0, "تاريخ الاشتراك"] = "not-a-date"
        with self.assertRaisesRegex(ValueError, "Invalid subscription dates"):
            self.load(data)

    def test_rejects_duplicate_subscribers(self):
        data = fixture()
        data.loc[1, "معرف المشترك"] = data.loc[0, "معرف المشترك"]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.load(data)

    def test_rejects_nonfinite_numeric_data(self):
        data = fixture()
        data["السعر الشهري"] = data["السعر الشهري"].astype(float)
        data.loc[0, "السعر الشهري"] = float("inf")
        with self.assertRaisesRegex(ValueError, "finite"):
            self.load(data)

    def test_rejects_single_class(self):
        data = fixture()
        data[analysis.TARGET] = "لا"
        with self.assertRaisesRegex(ValueError, "Both churn classes"):
            self.load(data)


if __name__ == "__main__":
    unittest.main()
