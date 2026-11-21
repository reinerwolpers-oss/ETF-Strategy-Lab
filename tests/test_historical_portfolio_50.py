"""Offline safety checks for isolated research-only historical simulation."""
import datetime as dt
import pathlib
import sys
import unittest

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"scripts"))
from historical_portfolio_50 import simulate
from seasonal_scan import SYMBOLS

class HistoricalPortfolioTests(unittest.TestCase):
    @staticmethod
    def synthetic():
        start=dt.date(2015,1,1)
        end=dt.date(2025,12,31)
        dates=[]
        while start<=end:
            if start.weekday()<5:
                dates.append(start)
            start+=dt.timedelta(days=1)
        # Monotone trend produces valid training windows, and trading still pays fees.
        return {s:{day:100+index*.01 for index,day in enumerate(dates)} for s in SYMBOLS}

    def test_isolated_walk_forward_and_capital(self):
        result=simulate(self.synthetic(),first=2021,last=2022)
        self.assertEqual(result["starting_cash_usd"],500)
        self.assertEqual(result["simulation_start"][:4],"2021")
        self.assertEqual(result["simulation_end"][:4],"2022")
        self.assertGreater(result["transactions"],0)
        self.assertTrue(all(row["cash_usd"]>=-0.001 for row in result["curve"]))
        for year,selections in result["selections"].items():
            for params in selections.values():
                self.assertLessEqual(params["training_samples"],int(year)-2015)
        self.assertLessEqual(max(row["positions"] for row in result["curve"]),len(SYMBOLS))
        self.assertTrue(all(trade["fee_usd"]==1 for trade in result["trades"]))

    def test_no_qqq_or_bad_years(self):
        with self.assertRaises(ValueError):
            simulate({},first=2021,last=2022)
        with self.assertRaises(ValueError):
            simulate(self.synthetic(),first=2025,last=2021)

if __name__=="__main__":
    unittest.main()
