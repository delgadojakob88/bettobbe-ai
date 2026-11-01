#!/usr/bin/env python3
"""BetTobbe Free: football-data.org -> league Poisson forecasts and honest backtesting.
Educational statistical research, not validated gambling advice.
"""
import os, json, math, datetime as dt, urllib.request, pathlib
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent
API = "https://api.football-data.org/v4"
TOKEN = os.getenv("FOOTBALL_DATA_TOKEN", "").strip()
COMPETITION = os.getenv("COMPETITION", "PL")
TODAY = dt.datetime.now(dt.timezone.utc).date()

def fetch_matches():
    req = urllib.request.Request(
        f"{API}/competitions/{COMPETITION}/matches",
        headers={"X-Auth-Token": TOKEN, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=35) as response:
        return json.load(response)["matches"]

def normalized(matches):
    finished, upcoming = [], []
    for m in matches:
        try:
            date = dt.date.fromisoformat(m["utcDate"][:10])
            home, away = m["homeTeam"]["name"], m["awayTeam"]["name"]
            if m["status"] == "FINISHED":
                score = m["score"]["fullTime"]
                if score["home"] is not None and score["away"] is not None:
                    finished.append((date, home, away, int(score["home"]), int(score["away"])))
            elif m["status"] in ("SCHEDULED", "TIMED") and date >= TODAY:
                upcoming.append((m["utcDate"], home, away))
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(finished), sorted(upcoming)

def fit(history, asof, min_matches=35):
    past = [m for m in history if m[0] < asof]
    if len(past) < min_matches:
        return None
    weights = [0.5 ** max(0, (asof - m[0]).days) / 150 for m in past]
    total_w = sum(weights)
    homeavg = sum(m[3] * w for m, w in zip(past, weights)) / total_w
    awayavg = sum(m[4] * w for m, w in zip(past, weights)) / total_w
    teams = {t for m in past for t in m[1:3]}
    attack = {t: 1. for t in teams}
    defense = {t: 1. for t in teams}
    counts = defaultdict(float)
    for (date, h, a, hg, ag), w in zip(past, weights):
        counts[h] += w
        counts[a] += w
    for _ in range(16):
        newa, newd = {}, {}
        for team in teams:
            goals = conced = expected = expected_conceded = 0.
            for (_, h, a, hg, ag), w in zip(past, weights):
                if h == team:
                    goals += w * hg
                    conced += w * ag
                    expected += w * homeavg * defense[a]
                    expected_conceded += w * awayavg * attack[a]
                elif a == team:
                    goals += w * ag
                    conced += w * hg
                    expected += w * awayavg * defense[h]
                    expected_conceded += w * homeavg * attack[h]
            # Shrink teams with few effective observations toward league average.
            newa[team] = max(.4, min(2.5, (goals + 8) / (expected + 8)))
            newd[team] = max(.4, min(2.5, (conced + 8) / (expected_conceded + 8)))
        attack = {t: .5 * attack[t] + .5 * newa[t] for t in teams}
        defense = {t: .5 * defense[t] + .5 * newd[t] for t in teams}
    return homeavg, awayavg, attack, defense, counts

def predict(model, h, a):
    homeavg, awayavg, attack, defense, counts = model
    if h not in attack or a not in attack:
        return None
    lh = max(.1, min(5., homeavg * attack[h] * defense[a]))
    la = max(.1, min(5., awayavg * attack[a] * defense[h]))
    hp = [math.exp(-lh) * lh**i / math.factorial(i) for i in range(11)]
    ap = [math.exp(-la) * la**j / math.factorial(j) for j in range(11)]
    p = {"1":0., "X":0., "2":0., "under_2_5":0., "over_2_5":0.}
    z = 0.
    for i in range(11):
        for j in range(11):
            value = hp[i] * ap[j]
            z += value
            p["1" if i>j else "2" if i<j else "X"] += value
            p["under_2_5" if i+j<3 else "over_2_5"] += value
    return {k: round(v/z, 4) for k,v in p.items()}

def backtest(history):
    # Walk forward: fit only matches strictly BEFORE each test date.
    eval_matches = history[-min(80, len(history)):]
    losses, scored = [], 0
    model_date, model = None, None
    for day, h, a, hg, ag in eval_matches:
        if model_date != day:
            model_date, model = day, fit(history, day)
        if not model:
            continue
        probs = predict(model, h, a)
        if not probs:
            continue
        true = "1" if hg>ag else "2" if hg<ag else "X"
        losses.append(sum((probs[x] - (1 if x == true else 0))**2 for x in ("1","X","2")))
        scored += 1
    return {"matches_tested":scored,
            "brier_multiclass":round(sum(losses)/len(losses),4) if losses else None,
            "note":"Walk-forward, but limited current-season sample. No claims of profitable predictions."}

def main():
    if not TOKEN:
        raise SystemExit("Configure FOOTBALL_DATA_TOKEN in GitHub Actions secrets.")
    matches = fetch_matches()
    history, fixtures = normalized(matches)
    model = fit(history, TODAY)
    forecasts = []
    if model:
        for utc, home, away in fixtures[:15]:
            probs = predict(model, home, away)
            forecasts.append({"kickoff_utc":utc, "home":home, "away":away,
                              "probabilities":probs, "decision":"AVSTÅ – inga verifierade odds"})
    result = {"generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
              "competition":COMPETITION, "historical_matches":len(history),
              "forecast_count":len(forecasts), "backtest":backtest(history),
              "model":"Regularized weighted Poisson baseline (not calibrated Dixon–Coles)",
              "odds_verified":False,
              "recommendation":"INGET SPEL – behöver validerade modeller och tidsstämplade bookmakerodds",
              "forecasts":forecasts}
    (ROOT/"report.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__ == "__main__":
    main()
