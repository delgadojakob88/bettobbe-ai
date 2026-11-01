import datetime as dt
import unittest
from validate_models import league_baseline, accuracy_metrics, compare, calibration

class ValidationTests(unittest.TestCase):
    def test_baseline_sums_to_one(self):
        history=[(dt.date(2026,1,1),"A","B",2,0),
                 (dt.date(2026,1,2),"B","A",0,0)]
        self.assertAlmostEqual(sum(league_baseline(history).values()),1.0)

    def test_perfect_predictions_score(self):
        rows=[{"truth":"1","probabilities":{"1":1.,"X":0.,"2":0.}}]
        self.assertEqual(accuracy_metrics(rows)["brier"],0.0)
        self.assertEqual(accuracy_metrics(rows)["accuracy"],1.0)
        self.assertEqual(sum(b["n"] for b in calibration(rows)),3)

    def test_empty_history(self):
        self.assertEqual(compare([])["status"],"insufficient_data")

    def test_same_day_not_used_as_training(self):
        day=dt.date(2026,1,1)
        h=[(day,"A","B",2,1)]
        self.assertEqual(compare(h,min_training=1)["tested"],0)

if __name__=="__main__":
    unittest.main()
