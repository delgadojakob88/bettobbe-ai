#!/usr/bin/env python3
"""Leakage-aware comparative evaluation of football result probability models.

Uses past matches only for every evaluation date, same sample for every model,
and explicit abstention when any model lacks data.
"""
import datetime as dt
import json
import math
import pathlib
import urllib.error

import agents
import bettobbe as core
from multi_league_archive import LEAGUES, download

ROOT=pathlib.Path(__file__).resolve().parent
OUTCOMES=("1","X","2")

def league_baseline(past):
    counts={"1":0,"X":0,"2":0}
    for _,_,_,hg,ag in past:
        counts["1" if hg>ag else "X" if hg==ag else "2"]+=1
    n=len(past)
    # Laplace smoothing to avoid zero probabilities with small samples.
    return {k:(counts[k]+1)/(n+3) for k in OUTCOMES}

def accuracy_metrics(rows):
    if not rows:
        return {"n":0,"brier":None,"log_loss":None,"accuracy":None}
    brier=sum(sum((r["probabilities"][k]-(1. if r["truth"]==k else 0.))**2 for k in OUTCOMES) for r in rows)/len(rows)
    logloss=-sum(math.log(max(1e-12,r["probabilities"][r["truth"]])) for r in rows)/len(rows)
    accuracy=sum(max(OUTCOMES,key=lambda k:r["probabilities"][k])==r["truth"] for r in rows)/len(rows)
    return {"n":len(rows),"brier":round(brier,4),"log_loss":round(logloss,4),"accuracy":round(accuracy,4)}

def calibration(rows):
    bins=[{"range":"0–20%","sum_p":0.,"wins":0,"n":0},
          {"range":"20–40%","sum_p":0.,"wins":0,"n":0},
          {"range":"40–60%","sum_p":0.,"wins":0,"n":0},
          {"range":"60–80%","sum_p":0.,"wins":0,"n":0},
          {"range":"80–100%","sum_p":0.,"wins":0,"n":0}]
    for row in rows:
        for k in OUTCOMES:
            p=row["probabilities"][k]
            b=bins[min(int(p*5),4)]
            b["n"]+=1;b["sum_p"]+=p;b["wins"]+=int(k==row["truth"])
    return [{"range":b["range"],"n":b["n"],
             "mean_predicted":round(b["sum_p"]/b["n"],4) if b["n"] else None,
             "observed_frequency":round(b["wins"]/b["n"],4) if b["n"] else None}
            for b in bins]

def compare(history, last_n=60, min_training=35):
    history=sorted(history)
    dates=sorted(set(m[0] for m in history))
    if not dates:
        return {"status":"insufficient_data","reason":"No finished games","tested":0}
    test=history[-last_n:]
    by_model={"BetRossi":[],"BetMilad":[],"LeagueBaseline":[]}
    rejected=0
    # Refit only when evaluation date changes: never include same-date results.
    for day in sorted(set(m[0] for m in test)):
        past=[m for m in history if m[0]<day]
        if len(past)<min_training:
            rejected+=sum(m[0]==day for m in test)
            continue
        model=core.fit(past,day,min_matches=min_training)
        baseline=league_baseline(past)
        for _,home,away,hg,ag in (m for m in test if m[0]==day):
            rossi=agents.betrossi(model,home,away).get("probabilities")
            milad=agents.betmilad(past,model,home,away,day).get("probabilities")
            if rossi is None or milad is None:
                rejected+=1
                continue
            truth="1" if hg>ag else "2" if hg<ag else "X"
            for key,prob in (("BetRossi",rossi),("BetMilad",milad),("LeagueBaseline",baseline)):
                by_model[key].append({"probabilities":{k:prob[k] for k in OUTCOMES},"truth":truth})
    n=len(by_model["BetRossi"])
    if n==0:
        return {"status":"insufficient_data","tested":0,"excluded":rejected,"reason":"Not enough common test observations"}
    scores={k:accuracy_metrics(rows) for k,rows in by_model.items()}
    base=scores["LeagueBaseline"]["brier"]
    delta={k:round(scores[k]["brier"]-base,4) for k in ("BetRossi","BetMilad")}
    return {"status":"ok","tested":n,"excluded":rejected,
            "methods":"Expanding-window chronological backtest, date cutoff, common test set; smoothed league-prior baseline",
            "models":scores,"brier_difference_vs_baseline":delta,
            "calibration":{k:calibration(rows) for k,rows in by_model.items()},
            "interpretation":"Negative Brier difference is better than baseline, but limited sample is not evidence of robust predictive accuracy."}

def main():
    if not core.TOKEN:
        raise SystemExit("Configure FOOTBALL_DATA_TOKEN in GitHub Actions secrets")
    result={"created_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"leagues":{},
            "note":"Research-only model diagnostics; no betting, odds, or return estimates."}
    for code,name in LEAGUES.items():
        try:
            history,_=core.normalized(download(code))
            report=compare(history)
            result["leagues"][code]={"name":name,"historical_matches":len(history),**report}
        except urllib.error.HTTPError as e:
            result["leagues"][code]={"name":name,"status":"unavailable","http_status":e.code}
        except (TimeoutError,OSError,ValueError,TypeError,KeyError,ZeroDivisionError) as e:
            result["leagues"][code]={"name":name,"status":"error","error_type":type(e).__name__}
    (ROOT/"validation_report.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# BetTobbe AI — jämförelse och validering","",
           "Tre modeller utvärderas på samma matcher, med enbart tidigare resultat som träningsdata.","",
           "| Liga | Testmatcher | Baslinje Brier | BetRossi Brier | BetMilad Brier |","|---|---:|---:|---:|---:|"]
    for code,record in result["leagues"].items():
        if record["status"]=="ok":
            v=record["models"]
            lines.append(f"| {record['name']} | {record['tested']} | {v['LeagueBaseline']['brier']} | {v['BetRossi']['brier']} | {v['BetMilad']['brier']} |")
        else:
            lines.append(f"| {record['name']} | Saknas ({record['status']}) | – | – | – |")
    lines+=["","Lägre Brier och log loss är bättre. Testmängderna är små och sannolikheter är inte säkerheter.",
             "Detaljerad kalibrering, log loss och träffsäkerhet finns i validation_report.json."]
    (ROOT/"validation_report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print({k:{"status":v["status"],"tested":v.get("tested",0)} for k,v in result["leagues"].items()})

if __name__=="__main__":
    main()
