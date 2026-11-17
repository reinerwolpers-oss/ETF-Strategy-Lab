ETF STRATEGY LAB 3.0
====================

Live-App:
https://reinerwolpers-oss.github.io/ETF-Strategy-Lab/

AUSSTATTUNG
- Acht ETF-Strategien: Welt, Tech-Offensive, Momentum, Trendfolge,
  Core-Satellite, Halbleiter-Offensive, Momentum-Faktor, dynamische Rotation.
- Automatische Strategiewahl: 60 Monate historisches Training, danach
  separater 36-Monats-Test der zuvor ausgewählten Strategie.
- Auswahlscore: annualisierte Trainingsrendite minus 0,25 x Betrag
  des maximalen Drawdowns. Der Testzeitraum beeinflusst diese Wahl nicht.
- Dies ist ein einmaliger Holdout-Test, KEIN rollierendes Walk-Forward-System.
- Keine Brokeranbindung, keine automatischen Kauf- oder Verkaufsorders.

KURSDATEN
Die Datei data/etf-prices.json wird über GitHub Actions werktags nach
23:15 UTC bei erfolgreicher Verfügbarkeit aktualisiert. Die Datensätze
umfassen abgeschlossene Monate und stammen aus dem inoffiziellen
Yahoo-Finance-Chart-Endpunkt. Ein Fehler lässt die vorhandenen Daten intakt.

Zuordnung: WORLD=VT, TECH=QQQ, BONDS=BND, SEMI=SMH, FACTOR=MTUM.
Historische USD-adjusted-close-Preise werden mit dem jeweiligen Monatsstand
von EURUSD=X (USD pro EUR) in EUR umgerechnet.
FX und ETF können unterschiedliche Schlusszeiten haben. ETF-interne
Kosten können bereits in Adjusted-Close-Daten enthalten sein.

EINRICHTUNG
1. GitHub Actions: ETF-Kursdaten aktualisieren ausführen oder auf
   den automatischen Zeitplan warten.
2. Auf GitHub Pages veröffentlichen: Settings > Pages >
   Deploy from a branch > main > /(root) > Save.
3. Die veröffentlichte Seite öffnen und bei Datensatz 'Online' prüfen,
   ob 'Echte Kurse geladen' und Version 3 angezeigt werden.
4. Falls die Datenquelle nicht antwortet, zeigt die App DEMO an.
   DEMO-Zahlen sind künstlich und keine historischen Gewinne.
5. Klick 'Kursdaten aktualisieren' lädt lediglich die von GitHub Pages
   veröffentlichte JSON-Datei neu, startet keinen GitHub-Actions-Job.

HINWEISE
Die historischen Zahlen sind keine Renditeprognose, insbesondere keine
Garantie für 20 % pro Jahr. US-gelistete ETFs dienen als Preis-Proxys,
nicht als konkrete Kaufempfehlungen für Anleger in Deutschland.
Steuern, Transaktionsgebühren, Spreads, Wechselkosten und tatsächliche
Order-Ausführung werden nicht vollständig abgebildet.
Die Simulation trifft keine Handelsentscheidungen im echten Depot.
