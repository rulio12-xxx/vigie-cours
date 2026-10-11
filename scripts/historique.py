"""Plus bas / plus haut de clôture sur 8 et 12 mois pour chaque ligne suivie (Yahoo, données journalières)."""
import json, sys, time
from datetime import datetime, timezone, timedelta
import cours  # réutilise TICKERS, CONVERTIR et la session Yahoo

def chart(ticker):
    cours._init_session()
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1y&interval=1d"
    if cours.CRUMB:
        url += f"&crumb={cours.CRUMB}"
    r = cours.SESSION.get(url, timeout=20)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    ts, cl = res["timestamp"], res["indicators"]["quote"][0]["close"]
    return res["meta"].get("currency"), [(datetime.fromtimestamp(t, timezone.utc).date(), c) for t, c in zip(ts, cl) if c is not None]

def serie_eur(i, tick):
    dev, s = chart(tick)
    if i in cours.CONVERTIR:
        _, fx = chart(cours.CONVERTIR[i][1])
        fxd = dict(fx)
        s = [(d, c / fxd[d]) for d, c in s if d in fxd]
    return dev, s

def extremes(s, jours):
    lim = datetime.now(timezone.utc).date() - timedelta(days=jours)
    w = [(d, c) for d, c in s if d >= lim]
    lo, hi = min(w, key=lambda x: x[1]), max(w, key=lambda x: x[1])
    return {"min": round(lo[1], 4), "minDate": lo[0].isoformat(), "max": round(hi[1], 4), "maxDate": hi[0].isoformat()}

def main(out):
    res, err = {}, {}
    for i, ticks in cours.TICKERS.items():
        for t in ticks:
            try:
                dev, s = serie_eur(i, t)
                if i == "amundi-gold" and dev != "EUR":
                    raise RuntimeError(f"devise {dev}")
                res[i] = {"ticker": t, "devise": dev, "dernier": round(s[-1][1], 4), "dernierDate": s[-1][0].isoformat(),
                          "m8": extremes(s, 243), "m12": extremes(s, 365)}
                break
            except Exception as e:  # noqa: BLE001
                err[i] = f"{t}: {e}"
            time.sleep(0.5)
        if i in res:
            err.pop(i, None)
    json.dump({"genere": datetime.now(timezone.utc).isoformat(timespec="minutes"), "lignes": res, "erreurs": err},
              open(out, "w"), indent=1, ensure_ascii=False)

if __name__ == "__main__":
    main(sys.argv[1])
