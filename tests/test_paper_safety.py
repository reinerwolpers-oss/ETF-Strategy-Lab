"""Offline checks for paper-only ETF simulator. Never contacts a broker."""
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch
from scripts import paper_trade as bot

class PaperSafetyTests(unittest.TestCase):
    def test_virtual_buy_and_sell_never_exceeds_cash(self):
        state=bot.new_state()
        self.assertEqual(state["mode"],"PAPER_ONLY")
        self.assertTrue(bot.trade(state,__import__("datetime").date(2026,11,17),"VT","BUY",0.5,100.0,"test"))
        self.assertLess(state["cash"],500)
        self.assertEqual(state["positions"]["VT"]["qty"],0.5)
        self.assertTrue(bot.trade(state,__import__("datetime").date(2026,11,18),"VT","SELL",0.5,101.0,"test"))
        self.assertNotIn("VT",state["positions"])
        self.assertEqual(len(state["trades"]),2)
        self.assertTrue(all(t["execution"]=="SYNTHETIC_DAILY_CLOSE_NOT_BROKER_ORDER" for t in state["trades"]))

    def test_paper_config_requires_explicit_mode(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg=pathlib.Path(folder)/"settings.json"
            cfg.write_text(json.dumps({"mode":"LIVE","enabled":True}))
            with patch.object(bot,"CONFIG",cfg):
                with self.assertRaises(RuntimeError):bot.paper_settings()
            cfg.write_text(json.dumps({"mode":"PAPER_ONLY","enabled":False}))
            with patch.object(bot,"CONFIG",cfg):
                self.assertFalse(bot.paper_settings()["enabled"])

    def test_cash_guard_and_no_order_packages(self):
        state=bot.new_state()
        self.assertFalse(bot.trade(state,__import__("datetime").date(2026,11,17),"SMH","BUY",20,100,"invalid"))
        self.assertEqual(len(state["trades"]),0)
        # No live trading module imports or network order API usage.
        text=pathlib.Path(bot.__file__).read_text()
        for forbidden in ("placeOrder(", "reqAccountUpdates(", "ib_insync", "ibapi.client", "ibkr_client"):
            self.assertNotIn(forbidden,text)

if __name__=="__main__":
    unittest.main()
