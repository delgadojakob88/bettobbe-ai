#!/usr/bin/env python3
"""Factual multi-league football archive. Does not generate betting recommendations.

API coverage: PL (Premier League), PD (La Liga), SA (Serie A).
Allsvenskan (ALL) requires different API access; never silently label as free.
"""
import collections
import datetime as dt
import json
import os
import pathlib
import urllib.error
import urllib.request

ROOT=pathlib.Path(__file__).resolve().parent
API="https://api.football-data.org/v4"
TOKEN=os.environ.get("FOOTBALL_DATA_TOKEN","").strip()
LEAGUES={"PL":"Premier League","PD":"La Liga","SA":"Serie A"}

def league_summary(code,name,matches):
    finished=[]
    upcoming=[]
    for m in matches:
        home=(m.get("homeTeam") or {}).get("name")
        away=(m.get("awayTeam") or {}).get("name")
        utc=m.get("utcDate","")
        if not home or not away or not utc:
            continue
        score=(m.get("score") or {}).get("fullTime") or {}
        hg,ag=score.get("home"),score.get("away")
        if m.get("status")=="FINISHED" and isinstance(hg,int) and isinstance(ag,int):
            finished.append({"utc":utc,"home":home,"away":away,"home_goals":hg,"away_goals":ag})
        elif m.get("status") in ("SCHEDULED","TIMED"):
            upcoming.append({"utc":utc,"home":home,"away":away})
    finished.sort(key=lambda m:m["utc"])
    upcoming.sort(key=lambda m:m["utc"])
    teams=collections.defaultdict(lambda:{"played":0,"points":0,"goals_for":0,"goals_against":0})
    for m in finished:
        h,a=teams[m["home"]],teams[m["away"]]
        h["played"]+=1;a["played"]+=1
        h["goals_for"]+=m["home_goals"];h["goals_against"]+=m["away_goals"]
        a["goals_for"]+=m["away_goals"];a["goals_against"]+=m["home_goals"]
        if m["home_goals"]>m["away_goals"]:h["points"]+=3
        elif m["home_goals"]<m["away_goals"]:a["points"]+=3
        else:h["points"]+=1;a["points"]+=1
    return {"competition":code,"name":name,"historical_matches":len(finished),
            "future_fixtures":len(upcoming),"recent_results":finished[-10:][::-1],
            "upcoming_matches":upcoming[:12],
            "standings_from_loaded_results":sorted(
                [{"team":n,**v} for n,v in teams.items()],
                key=lambda x:(-x["points"],-(x["goals_for"]-x["goals_against"]),-x["goals_for"],x["team"]))}

def download(code):
    # Reuse the same API response across all scripts in a GitHub Actions run.
    # Cache lives only in the ephemeral runner workspace, not in the repository.
    if code not in LEAGUES:
        raise ValueError("Unsupported league code")
    cache = ROOT / f".api_matches_{code}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    req=urllib.request.Request(f"{API}/competitions/{code}/matches",
                               headers={"X-Auth-Token":TOKEN,"Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=35) as response:
        matches=json.load(response).get("matches",[])
    cache.write_text(json.dumps(matches), encoding="utf-8")
    return matches

def build():
    if not TOKEN:
        raise SystemExit("FOOTBALL_DATA_TOKEN is missing in GitHub Actions Secrets.")
    report={"generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
            "data_source":"football-data.org","leagues":{},
            "notes":["Raw match coverage depends on API subscription and season.",
                     "Standings derived solely from returned matches; points deductions omitted.",
                     "Allsvenskan is not included here because the API lists it in a paid tier.",
                     "This archive is factual, not betting advice."]}
    for code,name in LEAGUES.items():
        try:
            report["leagues"][code]={"status":"ok",**league_summary(code,name,download(code))}
        except urllib.error.HTTPError as e:
            report["leagues"][code]={"status":"unavailable","competition":code,"name":name,"http_status":e.code}
        except (TimeoutError,OSError,ValueError) as e:
            report["leagues"][code]={"status":"error","competition":code,"name":name,"error_type":type(e).__name__}
    (ROOT/"multi_league_archive.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    lines=["# BetTobbe AI – matcharkiv för tre ligor","",
           f"Skapat UTC: {report['generated_utc']}","",
           "Endast verifierade matchresultat från API-källa; inga spelrekommendationer.",""]
    for code,item in report["leagues"].items():
        lines += [f"## {item['name']}",f"Status: {item['status']}",""]
        if item["status"]!="ok":
            lines += ["Uppgifter saknas: kontrollera API-behörighet eller datatäckning.",""]
            continue
        lines += [f"Avslutade: {item['historical_matches']}; kommande: {item['future_fixtures']}",
                  "### Kommande matcher",""]
        for m in item["upcoming_matches"]:
            lines.append(f"- {m['utc']} UTC: {m['home']} – {m['away']}")
        lines += ["","### Senaste resultat",""]
        for m in item["recent_results"]:
            lines.append(f"- {m['utc'][:10]}: {m['home']} {m['home_goals']}–{m['away_goals']} {m['away']}")
        lines += [""]
    lines += ["## Databegränsningar",""]+["- "+note for note in report["notes"]]
    (ROOT/"multi_league_archive.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    for code,item in report["leagues"].items():
        print(f"{code}: {item['status']} ({item.get('historical_matches','?')} results)")
    return report

if __name__=="__main__":
    build()
