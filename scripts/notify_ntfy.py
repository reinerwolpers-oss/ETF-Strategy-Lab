#!/usr/bin/env python3
"""Optional error-only ntfy alert. Requires private GitHub Actions secrets."""
import os
import re
import urllib.parse
import urllib.request

topic=os.environ.get("NTFY_TOPIC","").strip()
server=os.environ.get("NTFY_SERVER","https://ntfy.sh").strip().rstrip("/")
if topic:
    if not re.fullmatch(r"[A-Za-z0-9_-]{3,100}",topic):
        raise SystemExit("Invalid ntfy topic; alert skipped.")
    uri=urllib.parse.urlsplit(server)
    if uri.scheme!="https" or not uri.hostname or uri.username or uri.password or uri.query or uri.fragment:
        raise SystemExit("ntfy server must be an HTTPS origin")
    endpoint=server+"/"+topic
    message="ETF Saison Paper Bot 4.4: GitHub Actions meldet einen Fehler. Bitte Workflow und Datenstatus pruefen. Keine echten Orders."
    req=urllib.request.Request(endpoint,data=message.encode("utf-8"),method="POST",
        headers={"Title":"ETF Paper Bot Fehler","Priority":"high","Tags":"warning"})
    with urllib.request.urlopen(req,timeout=15) as response:
        print("Optional ntfy alert accepted:",response.status)
else:
    print("ntfy secrets not configured, no alert attempted")
