"""Offline regression tests for US market day vs UTC midnight.

The expected market date must remain New York local to prevent post-midnight
GitHub manual runs from incorrectly expecting the next day's close.
"""
import datetime as dt
import unittest
from scripts import paper_trade as bot

UTC=dt.timezone.utc

class MarketDateSafetyTests(unittest.TestCase):
    def test_utc_midnight_does_not_advance_us_session(self):
        now=dt.datetime(2026,11,19,0,53,tzinfo=UTC)
        self.assertEqual(bot.us_market_date(now),dt.date(2026,11,18))
        self.assertEqual(bot.require_same_completed_market_close({
            "QQQ":(dt.date(2026,11,18),660.0),
            "SMH":(dt.date(2026,11,18),461.0)},now),dt.date(2026,11,18))

    def test_different_dst_times(self):
        self.assertEqual(bot.us_market_date(dt.datetime(2026,7,20,0,30,tzinfo=UTC)),
                         dt.date(2026,7,19))
        self.assertEqual(bot.us_market_date(dt.datetime(2026,11,19,23,30,tzinfo=UTC)),
                         dt.date(2026,11,19))

    def test_stale_missing_or_mixed_closes_rejected(self):
        now=dt.datetime(2026,11,19,0,53,tzinfo=UTC)
        for market in ({}, {"QQQ":(dt.date(2026,11,17),660.0)},
                       {"QQQ":(dt.date(2026,11,18),660.0),
                        "SMH":(dt.date(2026,11,17),461.0)}):
            with self.assertRaises(RuntimeError):
                bot.require_same_completed_market_close(market,now)

    def test_timezone_required(self):
        with self.assertRaises(ValueError):
            bot.us_market_date(dt.datetime(2026,11,19,1,0))

if __name__=="__main__":
    unittest.main()
