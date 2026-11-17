#!/usr/bin/env python3
"""Safe error-only ntfy sender, with explicit opt-in harmless push test.

Secrets are NEVER printed. Default endpoint is https://ntfy.sh; the optional
legacy ETF_NTFY_SERVER secret is intentionally ignored by GitHub workflows.
"""
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

def main():
    raw=os.environ.get("NTFY_TOPIC","").strip()
    test=os.environ.get("NTFY_TEST_MODE")=="1"
    require=os.environ.get("NTFY_REQUIRE_TOPIC")=="1"
    if not raw:
        if require:
            print("NTFY_DIAG: MISSING_TOPIC - ETF_NTFY_TOPIC is empty or unavailable.")
            return 2
        print("NTFY_DIAG: DISABLED - optional notification not configured.")
        return 0

    # Accept either a bare ntfy.sh topic or a complete standard ntfy.sh topic
    # URL. Do NOT accept a URL that could redirect messages to an unknown host.
    if raw.startswith("https://"):
        url=urllib.parse.urlsplit(raw)
        if (url.scheme!="https" or url.hostname!="ntfy.sh" or url.port not in (None,443)
                or url.username or url.password or url.query or url.fragment):
            print("NTFY_DIAG: BAD_TOPIC_URL - use a bare topic name or https://ntfy.sh/<topic>.")
            return 2
        raw=url.path.lstrip("/")
    elif "://" in raw or "/" in raw:
        print("NTFY_DIAG: BAD_TOPIC_FORMAT - only the topic name belongs in ETF_NTFY_TOPIC.")
        return 2

    if not re.fullmatch(r"[A-Za-z0-9_-]{3,100}",raw):
        print("NTFY_DIAG: BAD_TOPIC_FORMAT - topic must be 3-100 letters, digits, '_' or '-'.")
        return 2

    # Never print topic or complete endpoint in logs.
    endpoint="https://ntfy.sh/"+raw
    message=("ETF Saison-Bot: Testnachricht aus GitHub Actions. Keine Order ausgefuehrt."
             if test else
             "ETF Saison-Bot: GitHub Actions meldet einen technischen Fehler. Bitte Logs pruefen. Keine echten Orders.")
    headers={"Title":"ETF Paper Bot Test" if test else "ETF Paper Bot Fehler",
             "Priority":"default" if test else "high",
             "Tags":"white_check_mark" if test else "warning"}
    request=urllib.request.Request(endpoint,data=message.encode("utf-8"),
                                   method="POST",headers=headers)
    try:
        with urllib.request.urlopen(request,timeout=20) as response:
            print("NTFY_DIAG: ACCEPTED - server HTTP",response.status,
                  "(delivery to phone not independently verified).")
            return 0
    except urllib.error.HTTPError as error:
        print("NTFY_DIAG: HTTP_REJECTED - server status",error.code,
              "; check topic permissions and any required authentication.")
        return 1
    except urllib.error.URLError as error:
        print("NTFY_DIAG: NETWORK_ERROR - could not reach ntfy.sh; cause:",
              type(error.reason).__name__)
        return 1
    except Exception as error:
        print("NTFY_DIAG: SENDING_ERROR -",type(error).__name__)
        return 1

if __name__=="__main__":
    sys.exit(main())
