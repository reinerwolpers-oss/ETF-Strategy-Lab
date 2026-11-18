"""Offline checks for IBKR 4.8 local status monitor. No network."""
import ast
import datetime as dt
import pathlib
import unittest
from scripts import ibkr_local_monitor as monitor

NOW=dt.datetime(2026,11,18,21,30,tzinfo=dt.timezone.utc)

def good_data():
    return {"handshake":True,"status":"BARS_RECEIVED","instruments":{
        s:{"last_ibkr_bar":{"date":"2026-11-18","close_usd":100.0},
           "bars_received":22,"reference_date":"2026-11-18",
           "same_date_comparison":{"date":"2026-11-18","difference_pct":0.0}}
        for s in ("QQQ","SMH")}}

class MonitorTests(unittest.TestCase):
    def test_good_equal_date_quotes(self):
        result=monitor.evaluate(good_data(),now=NOW)
        self.assertEqual(result["health"],"OK")
        self.assertFalse(result["broker_orders_sent"])
        self.assertFalse(result["github_upload"])
        self.assertFalse(result["paper_portfolio_changed"])
        self.assertIn("QQQ",monitor.create_html(result))

    def test_divergence_warning_at_threshold(self):
        data=good_data()
        data["instruments"]["QQQ"]["same_date_comparison"]["difference_pct"]=1.01
        result=monitor.evaluate(data,now=NOW)
        self.assertIn("QQQ:PRICE_DIVERGENCE_GE_1_PERCENT",result["warnings"])

    def test_old_and_missing_data_trigger_warning(self):
        data=good_data()
        data["instruments"]["QQQ"]["last_ibkr_bar"]["date"]="2026-11-10"
        data["instruments"]["SMH"]["reference_date"]=None
        data["instruments"]["SMH"]["same_date_comparison"]=None
        result=monitor.evaluate(data,now=NOW)
        self.assertIn("QQQ:IBKR_DATA_STALE",result["warnings"])
        self.assertIn("SMH:REFERENCE_NOT_AVAILABLE",result["warnings"])
        self.assertIn("SMH:NO_SAME_DATE_COMPARISON",result["warnings"])

    def test_html_escapes_input(self):
        data=good_data()
        data["instruments"]["QQQ"]["last_ibkr_bar"]["date"]="<script>alert(1)</script>"
        report=monitor.create_html(monitor.evaluate(data,now=NOW))
        self.assertNotIn("<script>",report)

    def test_no_trading_or_account_api_access(self):
        src=pathlib.Path(monitor.__file__).read_text(encoding="utf-8")
        calls={n.func.attr for n in ast.walk(ast.parse(src))
               if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)}
        forbidden={"placeOrder","cancelOrder","reqAccountSummary","reqPositions",
                   "reqExecutions","reqAccountUpdates","reqOpenOrders","reqMktData"}
        self.assertFalse(calls.intersection(forbidden))
        self.assertEqual(monitor.OUT,pathlib.Path.home()/"IBKR-Test")

if __name__=="__main__":
    unittest.main()
