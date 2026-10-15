"""Moyennes mensuelles des clôtures (ponctuel) : python3 mensuel.py sortie.json TICKER [MOIS]"""
import json, sys
from datetime import datetime, timezone
import cours
def main(out, ticker, mois=None):
    cours._init_session()
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=12y&interval=1d" + (f"&crumb={cours.CRUMB}" if cours.CRUMB else "")
    r = cours.SESSION.get(url, timeout=30); r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    agg = {}
    for t, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"]):
        if c is None: continue
        d = datetime.fromtimestamp(t, timezone.utc)
        if mois and d.month != int(mois): continue
        k = d.strftime("%Y-%m"); agg.setdefault(k, []).append(c)
    json.dump({"ticker": ticker, "devise": res["meta"].get("currency"), "mois": {k: {"moyenne": round(sum(v)/len(v), 3), "min": round(min(v), 3), "max": round(max(v), 3), "jours": len(v)} for k, v in sorted(agg.items())}}, open(out, "w"), indent=1)
if __name__ == "__main__":
    main(*sys.argv[1:])
