"""Offline guardrail tests for the alternate 30-session historical cooldown."""
import datetime as dt
import pathlib
import sys
import unittest

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"scripts"))
from historical_portfolio_cooldown import simulate, COOLDOWN_SESSIONS
from seasonal_scan import SYMBOLS

class CooldownTests(unittest.TestCase):
    @staticmethod
    def synthetic_market():
        day=dt.date(2015,1,1)
        end=dt.date(2023,12,31)
        series={s:{} for s in SYMBOLS}
        idx=0
        while day<=end:
            if day.weekday()<5:
                for s in SYMBOLS:
                    series[s][day]=100+idx*.02
                idx+=1
            day+=dt.timedelta(days=1)
        return series

    def test_research_capital_and_pause_policy(self):
        prices=self.synthetic_market()
        baseline=simulate(prices,first=2021,last=2023)
        first_buy=next(t for t in baseline["trades"] if t["side"]=="BUY")
        entered=dt.date.fromisoformat(first_buy["date"])
        # Target a position actually opened by the strategy. An arbitrary
        # crash date may have no exposure and is not a valid guardrail test.
        trading_days=sorted(d for d in prices[first_buy["ticker"]] if d>entered)
        shock_day=trading_days[3]
        prices[first_buy["ticker"]][shock_day]*=.05
        state=simulate(prices,first=2021,last=2023)
        self.assertEqual(state["starting_cash_usd"],500)
        self.assertEqual(state["cooldown_sessions"],COOLDOWN_SESSIONS)
        self.assertTrue(all(c["cash_usd"]>=-.001 for c in state["curve"]))
        starts=[e for e in state["cooldown_events"] if e["event"]=="PAUSE_ENTRIES"]
        resumes=[e for e in state["cooldown_events"] if e["event"]=="RESUME_ENTRIES"]
        self.assertTrue(starts, "Targeted shock after actual simulated entry must invoke 10%-drawdown guard")
        self.assertTrue(resumes, "Cooldown must expire and resume entries")
        for event in starts:
            if event["resume_on_or_after"]:
                resume=next((r for r in resumes if r["date"]>=event["date"]),None)
                self.assertIsNotNone(resume)
                self.assertEqual(resume["date"],event["resume_on_or_after"])
                buys=[t for t in state["trades"] if t["side"]=="BUY" and event["date"]<=t["date"]<resume["date"]]
                self.assertEqual(buys,[])
        self.assertTrue(all(2015<=int(y)<2024 for y in state["selections"]))

if __name__=="__main__":
    unittest.main()
