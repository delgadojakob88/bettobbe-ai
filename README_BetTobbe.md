# BetTobbe AI — gratis prototyp

Pythonbaserad forskningsprototyp för fotbollsprognoser från football-data.org.

## Säker setup från iPhone
1. Gå till **Settings → General → Danger Zone → Change repository visibility** och välj **Private** om projektet är offentligt.
2. Skapa en **ny** API-nyckel på football-data.org (en äldre nyckel delades i chatt).
3. Under **Settings → Secrets and variables → Actions → New repository secret** skapa `FOOTBALL_DATA_TOKEN` och klistra in den nya nyckeln. Lägg **aldrig** nyckeln i en kodfil.
4. Öppna **Actions → BetTobbe – daily football model → Run workflow**.
5. Öppna körningen och ladda ned **BetTobbe-report** under Artifacts; öppna `report.json` på iPhone.

Workflow kör även dagligen ungefär 08:15 vintertid / 09:15 sommartid i Sverige. GitHub kan fördröja schemalagda körningar.

## Vad modellen faktiskt kan
- Hämta färdiga och kommande matcher för Premier League (om tillgängligt på din API-plan).
- Anpassa regulariserade, tidsviktade Poisson-skattningar på historiska resultat.
- Beräkna 1X2 och över/under 2,5 mål och testa ett begränsat walk-forward-urval.
- Skapa `report.json` för granskning.

## Begränsningar
- Ingen betald eller verifierad oddsström, ingen ComeOn-koppling, inga automatiska spel.
- Standardhämtning omfattar begränsad säsongshistorik. Täckning beror på gratisplanen.
- Implementerar **inte** en färdigtränad Dixon–Coles-MLE. Modellen är en enkel Poisson-baslinje, och dess prognoser är inte kalibrerade.
- Inga rekommenderade spel innan odds finns och modellerna validerats.
- Ingen automatisk ChatGPT-bild; daglig rapport i JSON.


## Version 2 — fyra transparenta analysroller

Kör `python agents.py` efter `python bettobbe.py`. Automatiska GitHub Actions-körningen gör båda stegen och kör `python -m unittest -v test_agents` före datahämtningen.

- **BetRossi:** tidsviktad Poissonmodell för 1X2-sannolikheter.
- **BetCarrar:** senaste fem matchernas resultat och tydlig markering av saknade nyheter, skador och laguppställningar.
- **BetMilad:** separat, förenklad kontrollmodell som jämför lagens hemma-/bortamål.
- **BetTobbe:** granskar avvikelser, begränsad historik och saknade källor.

Rapporterna hamnar i GitHub Actions-artifact: `agents_report.md` (läsbar på telefon) och `agents_report.json` (maskinläsbar).

Viktigt: det är **inte** fyra externa autonoma språkmodeller. Ingen verifierad oddsström eller oberoende nyhetsagent finns, och statistiska prognoser utgör inte ett spelråd.


## Modellvalidering och dagens matchbild

Senaste workflow innehåller även:
- `validate_models.py`: Kronologisk jämförelse av BetRossi, BetMilad och en jämnförbar liga-baslinje. Beräknar Brier, log loss, träffsäkerhet och kalibrering på samma testmatcher.
- `validation_report.json` och `validation_report.md`: sparas som GitHub Actions-artifact.
- `render_daily.py`: skapar `bettobbe_today.svg` med vit/svart/guld design. Endast matcher på dagens **svenska kalenderdatum** visas; om färre än tre finns visas tomma platser i stället för matcher från fel datum.
- `bettobbe_today_manifest.json`: granskningsbar lista över valda matcher och datum.

**Så läser du bilden på iPhone:** kör workflow i GitHub Actions, öppna lyckad körning → Artifacts → BetTobbe-report → packa upp och öppna `bettobbe_today.svg` (till exempel i Safari eller Filer). SVG är en skalbar bild.

Begränsningar: GitHub Actions skapar en fil men publicerar inte automatiskt en bild i ChatGPT. Historiken är fortfarande begränsad, och prognoserna är inte validerade som tillförlitliga. Allsvenskan saknas fortfarande i denna anslutning.
