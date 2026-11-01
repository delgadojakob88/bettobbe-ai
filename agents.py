#!/usr/bin/env python3
"""Four transparent specialist agents. No LLMs, odds or invented external news."""
import datetime as dt
import json
import math
import pathlib
from collections import defaultdict

import bettobbe as core

ROOT = pathlib.Path(__file__).resolve().parent

def percent(value):
    return round(100 * value, 1) if value is not None else None

def recent_form(history, team, asof, n=5):
    games = [m for m in history if m[0] < asof and team in (m[1],m[2])][-n:]
    rows = []
    for _, home, away, hg, ag in games:
        gf, ga = (hg,ag) if home == team else (ag,hg)
        rows.append({"goals_for":gf,"goals_against":ga,"result":"V" if gf>ga else "O" if gf==ga else "F"})
    return {
        "played":len(rows),
        "sequence":"".join(r["result"] for r in rows),
        "goals_for":sum(r["goals_for"] for r in rows),
        "goals_against":sum(r["goals_against"] for r in rows),
    }

def betrossi(model, home, away):
    prediction = core.predict(model, home, away) if model else None
    return {
        "agent":"BetRossi",
        "role":"Målmodell och Poisson",
        "status":"OK" if prediction else "OTILLRÄCKLIGA_DATA",
        "probabilities":prediction,
        "method":"Regulariserad tidsviktad Poisson; ingen xG-data i källan",
    }

def betcarrar(history, home, away, asof):
    hf, af = recent_form(history,home,asof), recent_form(history,away,asof)
    return {
        "agent":"BetCarrar",
        "role":"Observerad lagform och datatäckning",
        "status":"OK" if min(hf["played"],af["played"])>=3 else "BEGRÄNSAD_DATA",
        "home_form":hf,"away_form":af,
        "tactics":"EJ_VERIFIERAT",
        "injuries":"EJ_VERIFIERAT",
        "lineups":"EJ_VERIFIERAT",
        "news":"EJ_VERIFIERAT",
        "note":"Källan innehåller matchresultat, inte verifierade nyheter eller taktik.",
    }

def betmilad(history, model, home, away, asof):
    # Deliberately different baseline: recent goals plus league home/away means,
    # no future matches and no claim of independence from the underlying source.
    past = [m for m in history if m[0] < asof]
    home_matches=[m for m in past if m[1]==home][-8:]
    away_matches=[m for m in past if m[2]==away][-8:]
    if not model or len(home_matches)<3 or len(away_matches)<3:
        return {"agent":"BetMilad","role":"Oberoende modellkontroll","status":"OTILLRÄCKLIGA_DATA",
                "probabilities":None,"note":"Kräver minst tre relevanta hemma-/bortamatcher."}
    league_home,league_away,*_=model
    home_goals=sum(m[3] for m in home_matches)
    away_conceded=sum(m[3] for m in away_matches)
    away_goals=sum(m[4] for m in away_matches)
    home_conceded=sum(m[4] for m in home_matches)
    # Shrink to league means and evaluate with independent Poisson parameters.
    lh=(home_goals+away_conceded+8*league_home)/(len(home_matches)+len(away_matches)+8)
    la=(away_goals+home_conceded+8*league_away)/(len(home_matches)+len(away_matches)+8)
    lh=max(.1,min(5.,lh));la=max(.1,min(5.,la))
    ps={"1":0.,"X":0.,"2":0.}
    for i in range(13):
        for j in range(13):
            z=(math.exp(-lh)*lh**i/math.factorial(i))*(math.exp(-la)*la**j/math.factorial(j))
            ps["1" if i>j else "2" if i<j else "X"]+=z
    total=sum(ps.values())
    return {"agent":"BetMilad","role":"Oberoende modellkontroll",
            "status":"OK","probabilities":{k:round(v/total,4) for k,v in ps.items()},
            "method":"Krympande rullande hemmamål/bortamål, separat från huvudmodellens parametrar"}

def bettobbe(rossi, carrar, milad, backtest):
    p1, p2 = rossi["probabilities"], milad["probabilities"]
    issues=[]
    if not p1:issues.append("Huvudmodellen saknar prognos")
    if not p2:issues.append("Kontrollmodellen saknar prognos")
    if carrar["status"]!="OK":issues.append("Otillräcklig formhistorik")
    if backtest.get("matches_tested",0)<100:issues.append("Begränsat backtest: färre än 100 matcher")
    if p1 and p2:
        delta=max(abs(p1[k]-p2[k]) for k in ("1","X","2"))
        if delta>=.12:issues.append("Modellerna skiljer minst 12 procentenheter")
    else:delta=None
    return {
        "agent":"BetTobbe","role":"Kvalitetsgranskning",
        "status":"GRANSKNING_KRÄVS" if issues else "STATISTIK_TILLGÄNGLIG",
        "max_model_difference_percentage_points":percent(delta),
        "warnings":issues,
        "missing_sources":["Verifierade laguppställningar","Skador","Taktiska källor","xG","Verifierade odds"],
        "recommendation":"Endast fotbollsanalys; ingen spelrekommendation",
    }

def create_report():
    if not core.TOKEN:
        raise SystemExit("Configure FOOTBALL_DATA_TOKEN in GitHub Actions secrets.")
    history, fixtures = core.normalized(core.fetch_matches())
    model=core.fit(history,core.TODAY)
    bt=core.backtest(history)
    out=[]
    for kickoff,home,away in fixtures[:15]:
        asof=dt.date.fromisoformat(kickoff[:10])
        a=betrossi(model,home,away)
        b=betcarrar(history,home,away,asof)
        c=betmilad(history,model,home,away,asof)
        d=bettobbe(a,b,c,bt)
        out.append({"kickoff_utc":kickoff,"home":home,"away":away,
                    "agents":[a,b,c,d]})
    report={"generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
            "competition":core.COMPETITION,"historical_matches":len(history),
            "backtest":bt,"fixtures_evaluated":len(out),
            "agents_are":"Fyra deterministiska analysmoduler, inte fyra fristående LLM:er",
            "data_source":"football-data.org",
            "scope":"Fotbollsforskning och modellutvärdering, ingen bettjänst",
            "fixtures":out}
    (ROOT/"agents_report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    (ROOT/"agents_report.md").write_text(format_markdown(report),encoding="utf-8")
    print(f"Agents analysed {len(out)} fixtures, from {len(history)} historical games")
    return report

def format_markdown(report):
    lines=["# BetTobbe AI — fyragentsrapport","",
           f"Genererad (UTC): {report['generated_utc']}",
           f"Liga: {report['competition']} · Historik: {report['historical_matches']} matcher",
           f"Backtest: {report['backtest']['matches_tested']} matcher; Brier {report['backtest']['brier_multiclass']}",
           "",
           "**Agenterna är separata analysmoduler i samma Pythonprogram, inte autonoma språkmodeller.**",
           "Inga verifierade odds, skador, startelvor eller taktiska nyheter finns i datakällan.",""]
    for m in report["fixtures"]:
        lines += [f"## {m['home']} – {m['away']} ({m['kickoff_utc']} UTC)",""]
        for agent in m["agents"]:
            lines.append(f"**{agent['agent']} — {agent['status']}**")
            if agent.get("probabilities"):
                p=agent["probabilities"]
                lines.append(f"  1: {percent(p['1'])}% · X: {percent(p['X'])}% · 2: {percent(p['2'])}%")
            if agent.get("home_form"):
                hf,af=agent["home_form"],agent["away_form"]
                lines.append(f"  Senaste form: hemma {hf['sequence'] or 'saknas'}; borta {af['sequence'] or 'saknas'}")
            if agent.get("warnings"):
                lines.append("  Begränsningar: "+"; ".join(agent["warnings"]))
            lines.append("")
    lines += ["---","Rapporten är statistisk information, inte ett råd om ekonomiska insatser."]
    return "\n".join(lines)+"\n"

if __name__=="__main__":
    create_report()
