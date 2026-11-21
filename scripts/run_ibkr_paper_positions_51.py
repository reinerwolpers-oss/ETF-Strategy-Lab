#!/usr/bin/env python3
"""Run the existing read-only IBKR paper positions check, keep logs local.

Scheduled via pythonw.exe to avoid console windows and PowerShell execution policy.
"""
import datetime as dt
import pathlib
import subprocess
import sys

ROOT=pathlib.Path.home()/"IBKR-Test"
SCRIPT=ROOT/"ibkr_paper_positions_readonly.py"
LOG=ROOT/"ibkr-paper-positions-51.log"

def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    with LOG.open("a",encoding="utf-8") as log:
        log.write("\n=== "+dt.datetime.now().astimezone().isoformat()+" ===\n")
        log.flush()
        try:
            completed=subprocess.run([sys.executable,str(SCRIPT)],stdout=log,stderr=subprocess.STDOUT,timeout=100,check=False)
            log.write("EXIT_CODE: "+str(completed.returncode)+"\n")
            return completed.returncode
        except Exception as exc:
            log.write("ERROR: "+type(exc).__name__+"\n")
            return 1

if __name__=="__main__":
    raise SystemExit(main())
