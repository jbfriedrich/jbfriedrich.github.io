import sys, pathlib
html = pathlib.Path("public_signal/index.html").read_text(encoding="utf-8")
fails = []
if 'class="chan chan--posts"' not in html:
    fails.append("signal preset did not render channel rows")
if "Clicks Power Keyboard" not in html:
    fails.append("signal preset lost the notes content")
if 'class="tile ' in html:
    fails.append("signal preset leaked channels markup")
for f in fails: print(f)
print("SIGNAL FAILURES:", len(fails))
sys.exit(1 if fails else 0)
