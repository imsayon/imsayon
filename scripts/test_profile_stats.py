#!/usr/bin/env python3
"""No-network checks for the GitHub contribution dashboard generator."""
import unittest
from datetime import date, datetime, timezone
from unittest.mock import patch

import profile_stats as stats


class ProfileStatsTests(unittest.TestCase):
    def test_quarter_windows_cover_year_once(self):
        spans = list(stats.quarter_windows(2025, date(2026, 2, 8)))
        self.assertEqual(spans[0], (date(2025, 1, 1), date(2025, 3, 31)))
        self.assertEqual(spans[-1], (date(2026, 1, 1), date(2026, 2, 8)))
        self.assertEqual(sum((b-a).days+1 for a,b in spans), 365+39)

    def test_date_range_rejects_missing_day(self):
        with self.assertRaisesRegex(RuntimeError, 'Incomplete'):
            stats.parse_days({'weeks':[{'contributionDays':[{'date':'2026-01-01','contributionCount':3}]}]}, date(2026,1,1),date(2026,1,2))

    def test_current_streak_includes_yesterday_when_today_empty(self):
        data={date(2026,11,11):1,date(2026,11,12):2,date(2026,11,13):1,date(2026,11,14):0,date(2026,11,15):0}
        self.assertEqual(stats.streaks(data,date(2026,11,15)),(0,3))
        data[date(2026,11,14)]=5
        self.assertEqual(stats.streaks(data,date(2026,11,15)),(4,4))
        data[date(2026,11,13)]=0
        self.assertEqual(stats.streaks(data,date(2026,11,15)),(1,2))

    def test_render_numerical_values_and_escape(self):
        rendered=stats.render({'last_year':1258,'lifetime':1985,'current_streak':4,'longest_streak':33,'as_of':'2026 & <verified>'})
        self.assertIn('1,258',rendered)
        self.assertIn('1,985',rendered)
        self.assertIn('2026 &amp; &lt;verified&gt;',rendered)
        self.assertNotIn('2026 & <verified>',rendered)
        with self.assertRaises(ValueError):
            stats.render({'last_year':-1,'lifetime':100,'current_streak':0,'longest_streak':5,'as_of':'x'})

    def test_collect_rejects_token_for_another_account(self):
        with patch.object(stats,'graphql',return_value={'login':'another','createdAt':'2021-01-01T00:00:00Z'}):
            with self.assertRaisesRegex(RuntimeError,'expected imsayon'):
                stats.collect('test-token',datetime(2026,11,15,tzinfo=timezone.utc))

    def test_api_consistency_failure_wont_write(self):
        answers=[
            {'login':'imsayon','createdAt':'2026-11-01T00:00:00Z'},
            {'contributionsCollection':{'contributionCalendar':{'totalContributions':99,'weeks':[{'contributionDays':[
                {'date':f'2026-11-{d:02}','contributionCount':1} for d in range(1,16)
            ]}]}}}
        ]
        with patch.object(stats,'quarter_windows',return_value=iter([(date(2026,11,1),date(2026,11,15))])), patch.object(stats,'graphql',side_effect=answers):
            with self.assertRaisesRegex(RuntimeError,'mismatch'):
                stats.collect('test-token',datetime(2026,11,15,tzinfo=timezone.utc))


if __name__=='__main__':
    unittest.main()
