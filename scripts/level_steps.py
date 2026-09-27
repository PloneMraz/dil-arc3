"""When a run's levels came, and how many actions each took — read from its store.

    $PY scripts/level_steps.py STORE_DIR [STORE_DIR ...]

Reads the region's reports kept in the store (`[data]`): each report says the
act just taken (its context) and the levels gained. An action is any act but
RESET, which is counted apart.
"""
import json, sqlite3, sys
from pathlib import Path

for store in sys.argv[1:]:
    db = sqlite3.connect(str(Path(store) / "store" / "memory" / "data.sqlite"))
    reports = []
    for k, v in db.execute("select k, v from data"):
        o = json.loads(v)
        p = o.get("payload")
        if k.startswith("signal-") and isinstance(p, dict) and isinstance(p.get("status"), dict) and "affords" in p:
            reports.append((int(k.split("-")[1]), p))
    reports.sort()
    actions = resets = since = 0
    levels = []
    for cycle, p in reports:
        if str(p.get("context", "")).endswith(":0"):
            resets += 1
        else:
            actions += 1
            since += 1
        if (p["status"].get("levelsDelta") or 0) > 0:
            levels.append((cycle, since))
            since = 0
    print(f"{Path(store).name}: {actions} actions, {resets} resets; levels at (cycle, actions since the last): {levels}")
