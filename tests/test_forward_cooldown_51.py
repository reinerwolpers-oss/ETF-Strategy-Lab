"""Offline tests for frozen, independent 5.1 forward paper variant."""
import datetime as dt
import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"scripts"))
from forward_cooldown_51 import init_state, apply_day, get_config

class ForwardVariantTests(unittest.TestCase):
    def setUp(self):
        self.cfg=get_config()
        self.state=init_state(self.cfg)
        self.start=dt.date.fromisoformat(self.cfg["start_date"])

    def test_frozen_mode_and_no_backfill(self):
        self.assertEqual(self.state["mode"],"PAPER_ONLY")
        self.assertEqual(self.cfg["cooldown_sessions"],30)
        self.assertFalse(self.cfg["broker_connection"])
        self.assertFalse(self.cfg["live_orders"])
        with self.assertRaises(ValueError):
            apply_day(self.state,self.cfg,self.start-dt.timedelta(days=1),{"QQQ":100,"SMH":100})

    def test_duplicate_day_not_replayed(self):
        self.assertTrue(apply_day(self.state,self.cfg,self.start,{"QQQ":100,"SMH":100}))
        previous=self.state["processed_sessions"]
        self.assertFalse(apply_day(self.state,self.cfg,self.start,{"QQQ":99,"SMH":99}))
        self.assertEqual(self.state["processed_sessions"],previous)

    def test_missing_market_quotes_fail_closed(self):
        with self.assertRaises(ValueError):
            apply_day(self.state,self.cfg,self.start,{"QQQ":100})
        self.assertEqual(self.state["processed_sessions"],0)

    def test_cooldown_blocks_entries_and_restarts_after_30_sessions(self):
        # Directly seed a well-defined open synthetic paper position for
        # the isolated risk-policy test, not the persisted live test state.
        self.state["positions"]={"QQQ":{"qty":1.0,"entry_price":100,
            "entry_date":self.start.isoformat(),
            "planned_exit_date":(self.start+dt.timedelta(days=200)).isoformat()}}
        self.state["cash"]=400
        self.state["risk_epoch_peak"]=500
        apply_day(self.state,self.cfg,self.start,{"QQQ":35,"SMH":100})
        self.assertEqual(self.state["cooldown_remaining"],30)
        self.assertEqual(self.state["cooldown_events"][0]["event"],"PAUSE_ENTRIES")
        for i in range(1,30):
            apply_day(self.state,self.cfg,self.start+dt.timedelta(days=i),{"QQQ":100,"SMH":100})
            self.assertGreater(self.state["cooldown_remaining"],0)
        apply_day(self.state,self.cfg,self.start+dt.timedelta(days=30),{"QQQ":100,"SMH":100})
        self.assertEqual(self.state["cooldown_remaining"],0)
        self.assertEqual(self.state["cooldown_events"][-1]["event"],"RESUME_ENTRIES")

if __name__=="__main__":
    unittest.main()
