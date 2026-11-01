import datetime as dt
import unittest
import multi_league_agents as mla

class MultiLeagueTests(unittest.TestCase):
    def fixtures(self, label):
        start=dt.date(2026,1,1)
        teams=[f"{label} A",f"{label} B",f"{label} C",f"{label} D"]
        out=[]
        for i in range(82):
            home=teams[i%4];away=teams[(i+1+(i//4)%2)%4]
            out.append({"utcDate":(start+dt.timedelta(days=i)).isoformat()+"T15:00:00Z",
                        "status":"FINISHED","homeTeam":{"name":home},"awayTeam":{"name":away},
                        "score":{"fullTime":{"home":i%3,"away":(i+1)%3}}})
        out.append({"utcDate":"2026-12-10T16:00:00Z","status":"SCHEDULED",
                    "homeTeam":{"name":teams[0]},"awayTeam":{"name":teams[1]},"score":{}})
        return out

    def test_separate_leagues(self):
        pl=mla.analyse_league("PL","Premier League",self.fixtures("English"),today=dt.date(2026,11,1))
        pd=mla.analyse_league("PD","La Liga",self.fixtures("Spanish"),today=dt.date(2026,11,1))
        self.assertEqual(pl["status"],"ok")
        self.assertEqual(pd["status"],"ok")
        self.assertEqual(pl["historical_matches"],82)
        self.assertEqual(pd["historical_matches"],82)
        self.assertEqual(pl["fixtures_evaluated"],1)
        self.assertTrue(pl["fixtures"][0]["home"].startswith("English"))
        self.assertTrue(pd["fixtures"][0]["home"].startswith("Spanish"))
        self.assertEqual(len(pd["fixtures"][0]["agents"]),4)

    def test_empty_history_fails_safely(self):
        result=mla.analyse_league("SA","Serie A",[],today=dt.date(2026,11,1))
        self.assertEqual(result["historical_matches"],0)
        self.assertEqual(result["fixtures_evaluated"],0)
        self.assertIsNone(result["backtest"]["brier_multiclass"])

if __name__=="__main__":
    unittest.main()
