"""Offline event-notification tests. No ntfy HTTP requests or broker calls."""
import datetime as dt
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch
from scripts import paper_trade as bot
from scripts import notify_paper_events as push

class PaperNotificationTests(unittest.TestCase):
    def test_one_event_per_virtual_trade_and_no_duplicate(self):
        state=bot.new_state()
        day=dt.date(2026,11,18)
        self.assertTrue(bot.trade(state,day,"VT","BUY",0.2,100.0,"test only"))
        self.assertEqual([e["kind"] for e in state["notification_outbox"]],["PAPER_BUY"])
        event=state["notification_outbox"][0]
        bot.add_notification(state,event)
        self.assertEqual(len(state["notification_outbox"]),1)
        self.assertTrue(bot.trade(state,day,"VT","SELL",0.2,101.0,"exit test"))
        self.assertEqual(len(state["notification_outbox"]),2)

    def test_sender_deduplication_and_no_resend(self):
        state=bot.new_state()
        bot.add_notification(state,{"id":"paper:2026-11-18:VT:BUY","kind":"PAPER_BUY",
                                  "ticker":"VT","date":"2026-11-18","qty":0.2,
                                  "price_usd":100.0,"reason":"test"})
        sent=[]
        with tempfile.TemporaryDirectory() as folder:
            output=pathlib.Path(folder)/"paper.json"
            with patch.object(push,"PORTFOLIO",output):
                n=push.dispatch(state,"placeholder_topic",lambda *args:sent.append(args))
                self.assertEqual(n,1)
                self.assertTrue(output.exists())
                self.assertEqual(push.dispatch(state,"placeholder_topic",lambda *args:sent.append(args)),0)
        self.assertEqual(len(sent),1)
        self.assertIn("Nur virtuell",sent[0][2])

    def test_no_live_mode_or_invalid_topic(self):
        state=bot.new_state()
        state["mode"]="LIVE"
        with self.assertRaises(ValueError):
            push.dispatch(state,"placeholder_topic",lambda *args:None)
        for topic in ("http://ntfy.sh/foo","https://evil.example/topic","abc/def",""):
            with self.assertRaises(ValueError):
                push.topic_from_secret(topic)
        self.assertEqual(push.topic_from_secret("https://ntfy.sh/valid_channel"),"valid_channel")

    def test_risk_event_is_distinct_and_high_priority(self):
        event={"id":"paper:riskstop:drawdown10","kind":"PAPER_RISK_STOP",
               "date":"2026-11-18","drawdown_pct":-10.2}
        title,text,priority=push.message(event)
        self.assertEqual(priority,"high")
        self.assertIn("virtuell",text)

if __name__=="__main__":
    unittest.main()
