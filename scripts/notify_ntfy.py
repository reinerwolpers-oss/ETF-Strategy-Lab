#!/usr/bin/env python3
"""Optional error-only ntfy alert. Requires private GitHub Actions secrets."""
import os
import re
import urllib.parse
import urllib.request

topic=os.environ.get("NTFY_TOPIC","").strip()
if not topic and os.environ.get("NTFY_REQUIRE_TOPIC")=="1":
    raise SystemExit("ETF_NTFY_TOPIC missing; no test message sent.")
server=os.environ.get("NTFY_SERVER","https://ntfy.sh").strip().rstrip("/")
if topic:
    if not re.fullmatch(r"[A-Za-z0-9_-]{3,100}",topic):
        raise SystemExit("Invalid ntfy topic; alert skipped.")
    uri=urllib.parse.urlsplit(server)
    if uri.scheme!="https" or not uri.hostname or uri.username or uri.password or uri.query or uri.fragment:
        raise SystemExit("ntfy server must be an HTTPS origin")
    endpoint=server+"/"+topic
    is_test=os.environ.get("NTFY_TEST_MODE")=="1"
    message=("ETF Saison-Bot: Testnachricht aus GitHub Actions erfolgreich gesendet. Kein Fehler, keine Order." if is_test else
             "ETF Saison Paper Bot 4.4: GitHub Actions meldet einen Fehler. Bitte Workflow und Datenstatus pruefen. Keine echten Orders.")
    req=urllib.request.Request(endpoint,data=message.encode("utf-8"),method="POST",
        headers={"Title":"ETF Paper Bot Test" if is_test else "ETF Paper Bot Fehler",
                 "Priority":"default" if is_test else "high",
                 "Tags":"white_check_mark" if is_test else "warning"})
    with urllib.request.urlopen(req,timeout=15) as response:
        print("Optional ntfy alert accepted:",response.status)
else:
    print("ntfy secrets not configured, no alert attempted")
