"""Offline checks for BetTobbe agent orchestration. Run: python -m unittest -v"""
import datetime as dt
import unittest
import agents
import bettobbe

class AgentTests(unittest.TestCase):
    def setUp(self):
        base=dt.date(2026,1,1)
        teams=["North","South","East","West"]
        self.history=[]
        for i in range(80):
            h=teams[i%4]
            a=teams[(i+1+(i//4)%2)%4]
            self.history.append((base+dt.timedelta(days=i),h,a,i%3,(i+1)%3))
        self.asof=base+dt.timedelta(days=90)
        self.model=bettobbe.fit(self.history,self.asof)

    def test_model_fits(self):
        self.assertIsNotNone(self.model)

    def test_probabilities_normalized(self):
        result=agents.betrossi(self.model,"North","South")
        p=result["probabilities"]
        self.assertAlmostEqual(p["1"]+p["X"]+p["2"],1,places=3)

    def test_unavailable_sources_not_fabricated(self):
        form=agents.betcarrar(self.history,"North","South",self.asof)
        self.assertEqual(form["injuries"],"EJ_VERIFIERAT")
        self.assertEqual(form["lineups"],"EJ_VERIFIERAT")

    def test_supervisor_with_missing_model(self):
        q={"probabilities":None}
        result=agents.bettobbe(q,{"status":"BEGRÄNSAD_DATA"},q,{"matches_tested":0})
        self.assertEqual(result["status"],"GRANSKNING_KRÄVS")
        self.assertIn("Huvudmodellen saknar prognos",result["warnings"])

    def test_form_uses_only_past(self):
        now=agents.recent_form(self.history,"North",self.asof)
        future=agents.recent_form(self.history+[ (self.asof+dt.timedelta(days=1),"North","South",99,0)],"North",self.asof)
        self.assertEqual(now,future)

if __name__=="__main__":
    unittest.main()
