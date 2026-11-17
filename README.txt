ETF Strategy Lab 2.0
====================
AUTOMATISCHE ECHTE ETF-KURSE ÜBER GITHUB PAGES

Die App lädt eine automatisch erzeugte Datei data/etf-prices.json. Ein GitHub-
Actions-Workflow holt die Daten werktags um 23:15 UTC. Der Kurslieferant ist
Yahoo Finance (inoffizieller Endpunkt; kann temporär ausfallen oder sperren).
Der Workflow übernimmt nur vollständige, geprüfte historische Daten. Bei
Fehlern bleibt die vorhandene Kursdatei unangetastet.

EINRICHTUNG (einmalig)
1. ZIP entpacken. Den INHALT des Ordners ETF_Strategy_Lab in ein GitHub-Repo
   hochladen, inklusive des versteckten Ordners .github/workflows.
2. GitHub Repo -> Settings -> Actions -> General -> Workflow permissions:
   'Read and write permissions' erlauben, falls nötig.
3. Unter Actions den Workflow 'ETF-Kursdaten aktualisieren' auswählen und
   'Run workflow' ausführen. Der Lauf muss erfolgreich (grün) sein. Prüfen,
   ob data/etf-prices.json danach vorhanden ist.
4. Repo -> Settings -> Pages -> Deploy from a branch -> main / (root).
5. Die veröffentlichte GitHub-Pages-URL öffnen. Die App lädt die JSON-Datei
   selbst; Klick auf 'Kursdaten aktualisieren' lädt die veröffentlichte Datei
   erneut (es startet KEIN sofortiger neuer Server-Download).

LOKAL
- index.html lässt sich weiterhin per Doppelklick im Browser öffnen.
- Im file:// Modus werden Demodaten verwendet; für automatische Kursdateien
  braucht die App Hosting über HTTP(S), z.B. GitHub Pages.
- CSV-Import funktioniert unabhängig von GitHub.

DATEN UND GRENZEN
- WORLD = VT (Vanguard Total World Stock ETF)
- TECH = QQQ (Invesco QQQ Trust, NASDAQ-100, nicht reiner Technologie-ETF)
- BONDS = BND (Vanguard Total Bond Market ETF)
- Alle drei sind US-gelistete Fonds, US-Dollar-denominiert, als Index-Proxys.
  Die App empfiehlt nicht deren direkten Kauf in Deutschland.
- Es werden bereinigte Monats-Schlusskurse (adjusted close) aus abgeschlossenen
  Monaten verwendet, soweit der Datenanbieter sie liefert.
- Renditen sind USD-Renditen, nicht EUR-Renditen. In Euro ausgewiesene
  Sparplan-Vermögenswerte sind daher nur hypothetische Recheneinheiten,
  KEINE belastbaren EUR-Prognosen. Wechselkurse werden nicht gerechnet.
- Keine Steuern, Transaktionsgebühren oder Brokeranbindung. Eingestellte
  jährliche Zusatzkosten werden zusätzlich abgezogen.
- Backtests garantieren keine künftigen Gewinne, insbesondere nicht 20% p.a.
- Wenn automatische Kursdaten fehlen, fällt die App sichtbar auf Demo-Daten
  zurück. Sie gibt diese nie als echte Kurse aus.
