#!/usr/bin/env python3
"""Generate a dated, factual BetTobbe match infographic (SVG, no external dependencies).

Never import matches from other days to fill the three slots. All probability
numbers, when available, come from the corresponding GitHub model output.
"""
import datetime as dt
import html
import json
import pathlib
from zoneinfo import ZoneInfo

ROOT=pathlib.Path(__file__).resolve().parent
TZ=ZoneInfo("Europe/Stockholm")
GOLD="#B8903B"
BLACK="#151515"
MUTED="#667085"

def text(x,y,s,size=20,color=BLACK,weight="normal"):
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-weight="{weight}" font-family="Arial,Helvetica,sans-serif">{html.escape(str(s))}</text>'

def render(data, validation=None, today=None):
    local_date=today or dt.datetime.now(TZ).date()
    found=[]
    for code,league in data.get("leagues",{}).items():
        if league.get("status")!="ok":continue
        for fixture in league.get("fixtures",[]):
            try:
                kickoff=dt.datetime.fromisoformat(fixture["kickoff_utc"].replace("Z","+00:00")).astimezone(TZ)
            except (KeyError,ValueError,TypeError):
                continue
            if kickoff.date()==local_date:
                found.append((kickoff,code,league.get("name",code),fixture))
    found.sort(key=lambda t:(t[0],t[1],t[3]["home"]))
    selected=found[:3]
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1580" viewBox="0 0 1080 1580">',
         '<rect width="1080" height="1580" fill="#FFFFFF"/>',
         '<rect x="0" y="0" width="1080" height="16" fill="#B8903B"/>',
         text(62,95,"BETTOBBE AI",53,BLACK,"bold"),
         text(62,146,"DAGENS MATCHANALYS",28,GOLD,"bold"),
         text(62,188,f"{local_date.strftime('%Y-%m-%d')} · svensk tid · verifierat spelschema från API",18,MUTED),
         '<line x1="60" x2="1020" y1="218" y2="218" stroke="#D5D8DC" stroke-width="2"/>']
    for i in range(3):
        top=255+i*385
        svg.extend([f'<rect x="60" y="{top}" width="960" height="345" rx="20" fill="#FAFAFA" stroke="#DBDCE0" stroke-width="2"/>',
                    f'<rect x="60" y="{top}" width="10" height="345" rx="5" fill="{GOLD}"/>'])
        if i>=len(selected):
            svg.append(text(100,top+110,f"MATCH {i+1} — INGEN YTTERLIGARE MATCH",27,BLACK,"bold"))
            svg.append(text(100,top+163,"Färre än tre verifierade matcher i anslutna ligor i dag.",20,MUTED))
            svg.append(text(100,top+220,"Visar inte matcher från andra datum.",19,MUTED))
            continue
        kickoff,code,name,fixture=selected[i]
        svg.append(text(100,top+60,f"{name.upper()} · {kickoff.strftime('%H:%M')}",20,GOLD,"bold"))
        teams=f"{fixture['home']} – {fixture['away']}"
        if len(teams)>52:teams=teams[:49]+"…"
        svg.append(text(100,top+117,teams,29,BLACK,"bold"))
        agent_map={a.get("agent"):a for a in fixture.get("agents",[])}
        p=agent_map.get("BetRossi",{}).get("probabilities")
        if p:
            svg.append(text(100,top+171,f"BetRossi: 1 {100*p['1']:.1f}%  ·  X {100*p['X']:.1f}%  ·  2 {100*p['2']:.1f}%",22,BLACK))
        else:
            svg.append(text(100,top+171,"BetRossi: statistiskt underlag saknas",20,MUTED))
        milad=agent_map.get("BetMilad",{}).get("probabilities")
        if milad:
            svg.append(text(100,top+215,f"BetMilad: 1 {100*milad['1']:.1f}%  ·  X {100*milad['X']:.1f}%  ·  2 {100*milad['2']:.1f}%",20,MUTED))
        else:
            svg.append(text(100,top+215,"BetMilad: kontrollprognos saknas",20,MUTED))
        form=agent_map.get("BetCarrar",{})
        home_form=form.get("home_form",{}).get("sequence","–")
        away_form=form.get("away_form",{}).get("sequence","–")
        svg.append(text(100,top+259,f"Form (5 senaste): {home_form or '–'} / {away_form or '–'}",19,BLACK))
        supervisor=agent_map.get("BetTobbe",{})
        status=supervisor.get("status","INGEN GRANSKNING")
        svg.append(text(100,top+306,"BetTobbe: "+status,18,GOLD,"bold"))
    svg.extend(['<line x1="60" x2="1020" y1="1435" y2="1435" stroke="#D5D8DC" stroke-width="2"/>',
                text(62,1473,"KÄLLA: football-data.org · Separata modeller per liga",18,BLACK,"bold"),
                text(62,1507,"Saknade skador, startelvor, xG och nyheter markeras – inga uppgifter hittas på.",17,MUTED),
                text(62,1540,"Statistiska prognoser är osäkra. Ingen rekommendation om spel.",17,MUTED),
                '</svg>'])
    return "\n".join(svg), {"date":str(local_date),"matches_available":len(found),"displayed":len(selected),
                              "matches":[{"league":code,"home":f["home"],"away":f["away"],"kickoff":t.isoformat()}
                                         for t,code,name,f in selected]}

def main():
    source=ROOT/"multi_league_agents.json"
    if not source.exists():
        raise SystemExit("Missing multi_league_agents.json – run agents first")
    data=json.loads(source.read_text(encoding="utf-8"))
    svg,manifest=render(data)
    (ROOT/"bettobbe_today.svg").write_text(svg,encoding="utf-8")
    (ROOT/"bettobbe_today_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Daily infographic:",manifest["date"],manifest["displayed"],"matches")

if __name__=="__main__":
    main()
