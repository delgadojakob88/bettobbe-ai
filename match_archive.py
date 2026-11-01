#!/usr/bin/env python3
"""Premier League match history report (no odds or betting recommendations)."""
import collections
import datetime as dt
import json
import pathlib
import bettobbe

ROOT = pathlib.Path(__file__).resolve().parent

def summarize(matches):
    finished, upcoming = bettobbe.normalized(matches)
    table=collections.defaultdict(lambda:{"played":0,"won":0,"drawn":0,"lost":0,"gf":0,"ga":0,"points":0})
    for _,home,away,hg,ag in finished:
        h,a=table[home],table[away]
        h["played"]+=1; a["played"]+=1
        h["gf"]+=hg;h["ga"]+=ag
        a["gf"]+=ag;a["ga"]+=hg
        if hg>ag:
            h["won"]+=1;h["points"]+=3;a["lost"]+=1
        elif hg<ag:
            a["won"]+=1;a["points"]+=3;h["lost"]+=1
        else:
            h["drawn"]+=1;a["drawn"]+=1;h["points"]+=1;a["points"]+=1
    standings=sorted(
        [{"team":name,**stats,"goal_difference":stats["gf"]-stats["ga"]} for name,stats in table.items()],
        key=lambda r:(-r["points"],-r["goal_difference"],-r["gf"],r["team"])
    )
    return {
        "competition":bettobbe.COMPETITION,
        "generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "finished_matches":len(finished),
        "upcoming_matches":len(upcoming),
        "teams_with_results":len(table),
        "total_goals":sum(m[3]+m[4] for m in finished),
        "mean_goals_per_match":round(sum(m[3]+m[4] for m in finished)/len(finished),2) if finished else None,
        "standings_from_loaded_results":standings,
        "recent_results":[{"date":str(date),"home":home,"away":away,"home_goals":hg,"away_goals":ag}
                          for date,home,away,hg,ag in finished[-15:][::-1]],
        "next_fixtures":[{"kickoff_utc":utc,"home":home,"away":away} for utc,home,away in upcoming[:15]],
        "limitations":["Tabellen är beräknad enbart på matcher som API:t returnerade",
                       "Historiska poängavdrag ingår inte", "Inga spelråd eller odds"],
    }

def to_markdown(report):
    lines=["# BetTobbe – matchhistorik","",
           f"Uppdaterad (UTC): {report['generated_utc']}",
           f"Färdigspelade matcher: {report['finished_matches']} · Kommande matcher: {report['upcoming_matches']}",
           f"Snitt mål/match: {report['mean_goals_per_match']}","",
           "## Tabell från tillgängliga matchresultat","",
           "| Lag | M | V | O | F | GM | IM | P |",
           "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for t in report["standings_from_loaded_results"]:
        lines.append(f"| {t['team']} | {t['played']} | {t['won']} | {t['drawn']} | {t['lost']} | {t['gf']} | {t['ga']} | {t['points']} |")
    lines += ["","## Senaste resultat",""]
    for m in report["recent_results"]:
        lines.append(f"- {m['date']}: {m['home']} {m['home_goals']}–{m['away_goals']} {m['away']}")
    lines += ["","## Kommande matcher",""]
    for m in report["next_fixtures"]:
        lines.append(f"- {m['kickoff_utc']} UTC: {m['home']} – {m['away']}")
    lines += ["","**Begränsningar:** " + "; ".join(report["limitations"])]
    return "\n".join(lines)+"\n"

def main():
    if not bettobbe.TOKEN:
        raise SystemExit("FOOTBALL_DATA_TOKEN saknas i GitHub Secrets.")
    report=summarize(bettobbe.fetch_matches())
    (ROOT/"match_archive.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    (ROOT/"match_archive.md").write_text(to_markdown(report),encoding="utf-8")
    print(f"Archive: {report['finished_matches']} results, {report['upcoming_matches']} future fixtures")

if __name__=="__main__":
    main()
