"""Offline safety & comparison tests; no broker, network or order calls."""
import ast
import pathlib
import unittest
from scripts import ibkr_historical_compare as history

class HistoricalReadOnlyTests(unittest.TestCase):
    def test_fixed_demo_endpoint_and_local_output(self):
        self.assertEqual(history.HOST,"127.0.0.1")
        self.assertEqual(history.PORT,7497)
        self.assertEqual(history.SYMBOLS,("QQQ","SMH"))
        self.assertEqual(history.OUTPUT_FILE.parent,pathlib.Path.home()/"IBKR-Test")
        self.assertTrue(history.OUTPUT_FILE.name.endswith(".json"))

    def test_zero_trade_or_account_requests(self):
        source=pathlib.Path(history.__file__).read_text(encoding="utf-8")
        tree=ast.parse(source)
        calls={node.func.attr for node in ast.walk(tree) if isinstance(node,ast.Call)
               and isinstance(node.func,ast.Attribute)}
        banned={"placeOrder","cancelOrder","reqAccountSummary","reqPositions",
                "reqExecutions","reqOpenOrders","reqAccountUpdates","reqMktData",
                "reqRealTimeBars","reqPnL","reqCompletedOrders"}
        self.assertFalse(calls.intersection(banned))
        self.assertIn("reqHistoricalData",calls)
        self.assertNotIn("git push",source)

    def test_same_date_only_and_nonadjusted_warning(self):
        rows=[{"date":"2026-11-17","close_usd":656.66},
              {"date":"2026-11-18","close_usd":660.0}]
        reference={"QQQ":{"date":"2026-11-17","close_usd":656.95}}
        item=history.compare("QQQ",rows,reference)
        self.assertEqual(item["same_date_comparison"]["date"],"2026-11-17")
        self.assertAlmostEqual(item["same_date_comparison"]["difference_usd"],-0.29)
        newer=history.compare("QQQ",rows,{"QQQ":{"date":"2026-11-16","close_usd":656.95}})
        self.assertIsNone(newer["same_date_comparison"])
        self.assertEqual(item["last_ibkr_bar"]["date"],"2026-11-18")

    def test_missing_data_never_synthesizes_bars(self):
        x=history.compare("SMH",[],{"SMH":{"date":"2026-11-17","close_usd":460.10}})
        self.assertEqual(x["bars_received"],0)
        self.assertIsNone(x["same_date_comparison"])

if __name__=="__main__":
    unittest.main()
