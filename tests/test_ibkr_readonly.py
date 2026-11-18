"""Safe offline tests for the local IBKR read-only demo probe."""
import ast
import pathlib
import unittest
from scripts import ibkr_readonly_probe as probe

class IBKRReadOnlyTests(unittest.TestCase):
    def test_fixed_local_demo_address_and_disabled_orders(self):
        self.assertEqual(probe.HOST,"127.0.0.1")
        self.assertEqual(probe.PORT,7497)
        self.assertNotIn(probe.CLIENT_ID,(0,1))
        self.assertEqual(probe.SYMBOLS,("QQQ","SMH"))
        status=probe.safe_status()
        self.assertFalse(status["broker_orders_enabled"])
        self.assertFalse(status["account_data_collected"])
        self.assertFalse(status["published_to_github"])

    def test_never_import_or_call_trade_or_account_apis(self):
        source=pathlib.Path(probe.__file__).read_text(encoding="utf-8")
        parsed=ast.parse(source)
        banned={"placeOrder","cancelOrder","reqPositions","reqAccountUpdates",
                "reqExecutions","reqOpenOrders","reqAllOpenOrders",
                "reqAccountSummary","reqCompletedOrders","reqMktData"}
        calls={n.func.attr for n in ast.walk(parsed)
               if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)}
        self.assertFalse(banned.intersection(calls))
        self.assertEqual(probe.OUTPUT_FILE.parent, pathlib.Path.home()/"IBKR-Test")
        self.assertNotIn("github.com/",source)

    def test_report_schema(self):
        result=probe.safe_status(connected=True,handshake=True,
                        server_time="2026-11-18T16:00:00+00:00",
                        contracts={"QQQ":[]})
        self.assertEqual(result["mode"],"LOCAL_IBKR_DEMO_READ_ONLY")
        self.assertEqual(result["contract_details"],{"QQQ":[]})

if __name__=="__main__":
    unittest.main()
