#!/usr/bin/env python3
"""Run four transparent statistical analysis modules separately for each league.

Leagues: PL, PD, SA. No synthetic odds, news, xG or gambling instructions.
"""
import datetime as dt
import json
import pathlib
import urllib.error
import agents
import bettobbe as core
from multi_league_archive import LEAGUES, download

ROOT=pathlib.Path(__file__).resolve().parent

def analyse_league(code, name, matches, today=None):
    today=today or dt.datetime.now(dt.timezone.utc).date()
    history, fixtures=core.normalized(matches)
    # Fit once at the current date, never on results after the fixture.
    training=[m for m in history if m[0] < today]
    model=core.fit(training,today)
    validation=core.backtest(training)
    reports=[]
    for utc,home,away in fixtures:
        # One current-day match or future fixture per league; no already-completed games
        asof=dt.date.fromisoformat(utc[:10])
        if asof < today:
            continue
        rossi=agents.betrossi(model,home,away)
        carrar=agents.betcarrar(training,home,away,asof)
        milad=agents.betmilad(training,model,home,away,asof)
        supervisor=agents.bettobbe(rossi,carrar,milad,validation)
        reports.append({"kickoff_utc":utc,"home":home,"away":away,
                        "agents":[rossi,carrar,milad,supervisor]})
    return {"competition":code,"name":name,"status":"ok",
            "historical_matches":len(training),"backtest":validation,
            "fixtures_evaluated":len(reports),"fixtures":reports[:20]}

def create_report():
    if not core.TOKEN:
        raise SystemExit("Configure FOOTBALL_DATA_TOKEN in GitHub Actions secrets")
    data={"generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
          "source":"football-data.org",
          "agents":"Four deterministic statistical Python modules (not autonomous LLMs)",
          "league_models":"Separate training and validation per league",
          "leagues":{}}
    for code,name in LEAGUES.items():
        try:
            data["leagues"][code]=analyse_league(code,name,download(code))
        except urllib.error.HTTPError as e:
            data["leagues"][code]={"status":"unavailable","name":name,"http_status":e.code}
        except (OSError,ValueError,KeyError,TypeError,ZeroDivisionError) as e:
            data["leagues"][code]={"status":"error","name":name,"error_type":type(e).__name__}
    (ROOT/"multi_league_agents.json").write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")
    lines=["# BetTobbe AI – fyragentsanalys per liga","",
           f"Rapport (UTC): {data['generated_utc']}","",
           "Fotbollsstatistik och osäkerhetsbedömning, inga spelrekommendationer.","",
           "Separata modeller och backtester för Premier League, La Liga och Serie A.",""]
    for code,item in data["leagues"].items():
        lines.extend([f"## {item['name']} – {code}","",f"Status: {item['status']}",""])
        if item["status"]!="ok":
            lines.extend(["Liga ej analyserad – se JSON för status.",""])
            continue
        bt=item["backtest"]
        lines.extend([f"Historik: {item['historical_matches']} | Backtestade: {bt['matches_tested']} | Multiklass-Brier: {bt['brier_multiclass']}",
                      f"Antal kommande matcher analyserade: {item['fixtures_evaluated']}",""])
        for m in item["fixtures"]:
            lines.extend([f"### {m['home']} – {m['away']} ({m['kickoff_utc']} UTC)",""])
            for a in m["agents"]:
                line=f"- **{a['agent']}**: {a['status']}"
                p=a.get("probabilities")
                if p:
                    line+=f" | 1 {p['1']*100:.1f}% / X {p['X']*100:.1f}% / 2 {p['2']*100:.1f}%"
                if a.get("warnings"): line+=" | "+", ".join(a["warnings"])
                lines.append(line)
            lines.append("")
    lines.extend(["---","Källan innehåller inte verifierade skador, xG, laguppställningar eller odds."])
    (ROOT/"multi_league_agents.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("League agent status:",{k:v["status"] for k,v in data["leagues"].items()})
    return data

if __name__=="__main__":
    create_report()
