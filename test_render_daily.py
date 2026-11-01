import datetime as dt
import unittest
from zoneinfo import ZoneInfo
from render_daily import render

class DailyVisualTests(unittest.TestCase):
    def test_only_today_included_no_padding_from_tomorrow(self):
        data={"leagues":{"PL":{"name":"Premier League","status":"ok","fixtures":[
          {"kickoff_utc":"2026-11-01T16:30:00Z","home":"Liverpool","away":"Arsenal","agents":[]},
          {"kickoff_utc":"2026-11-02T20:00:00Z","home":"Newcastle","away":"Everton","agents":[]}
        ]}}}
        svg,manifest=render(data,today=dt.date(2026,11,1))
        self.assertEqual(manifest["displayed"],1)
        self.assertIn("Liverpool",svg)
        self.assertNotIn("Newcastle",svg)
        self.assertIn("INGEN YTTERLIGARE MATCH",svg)

    def test_escapes_team_names(self):
        data={"leagues":{"PD":{"name":"La Liga","status":"ok","fixtures":[
          {"kickoff_utc":"2026-11-01T13:00:00Z","home":"A&B","away":"C<D","agents":[]}
        ]}}}
        svg,_=render(data,today=dt.date(2026,11,1))
        self.assertIn("A&amp;B",svg)
        self.assertIn("C&lt;D",svg)

if __name__=="__main__":
    unittest.main()
