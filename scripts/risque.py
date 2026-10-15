"""Indicateurs de marché pour la note « risque de krach » (S&P 500 vs moyenne 200 jours, VIX, courbe US 10 ans − 3 mois)."""
import json, sys
from datetime import datetime, timezone
import cours

def serie(t, rng="1y"):
    cours._init_session()
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?range={rng}&interval=1d" + (f"&crumb={cours.CRUMB}" if cours.CRUMB else "")
    r = cours.SESSION.get(url, timeout=25); r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    pts = [(datetime.fromtimestamp(a, timezone.utc).date().isoformat(), c) for a, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"]) if c is not None]
    return pts

def main(out):
    o, err = {}, {}
    try:
        s = serie("^GSPC"); c = [x[1] for x in s]
        ma = sum(c[-200:]) / min(200, len(c))
        o["sp500"] = {"dernier": round(c[-1], 2), "date": s[-1][0], "mm200": round(ma, 2), "ecartMM200": round(c[-1] / ma - 1, 4),
                      "plusHaut52s": round(max(c), 2), "depuisPlusHaut": round(c[-1] / max(c) - 1, 4)}
    except Exception as e: err["sp500"] = str(e)  # noqa: BLE001
    for k, t in (("vix", "^VIX"), ("taux10ans", "^TNX"), ("taux3mois", "^IRX")):
        try:
            s = serie(t, "1mo"); o[k] = {"dernier": round(s[-1][1], 3), "date": s[-1][0]}
        except Exception as e: err[k] = str(e)  # noqa: BLE001
    if "taux10ans" in o and "taux3mois" in o:
        o["courbe10a3m"] = round(o["taux10ans"]["dernier"] - o["taux3mois"]["dernier"], 3)
    json.dump({"genere": datetime.now(timezone.utc).isoformat(timespec="minutes"), "indicateurs": o, "erreurs": err}, open(out, "w"), indent=1)

if __name__ == "__main__":
    main(sys.argv[1])
