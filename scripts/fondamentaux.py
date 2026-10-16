"""Données fondamentales Yahoo (annuelles + estimations) pour le calcul de la note Higgons.
Usage : python3 fondamentaux.py sortie.json id1 id2 ...   (ids de cours.TICKERS)"""
import json, sys, time
from datetime import datetime, timezone
import cours

TYPES = ["annualDilutedEPS", "annualBasicEPS", "annualNetIncomeCommonStockholders", "annualStockholdersEquity",
         "annualNetDebt", "annualTotalDebt", "annualCashCashEquivalentsAndShortTermInvestments",
         "annualOrdinarySharesNumber", "annualTotalRevenue"]

def get(url):
    cours._init_session()
    if cours.CRUMB:
        url += ("&" if "?" in url else "?") + f"crumb={cours.CRUMB}"
    r = cours.SESSION.get(url, timeout=25)
    r.raise_for_status()
    return r.json()

def serie(sym):
    p1 = int(datetime(2019, 1, 1, tzinfo=timezone.utc).timestamp()); p2 = int(time.time())
    j = get(f"https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/{sym}?type={','.join(TYPES)}&period1={p1}&period2={p2}")
    out = {}
    for res in j["timeseries"]["result"]:
        t = res["meta"]["type"][0]
        out[t] = {v["asOfDate"][:4]: v["reportedValue"]["raw"] for v in res.get(t, []) or [] if v}
    return out

def resume(sym):
    m = "earningsTrend,financialData,defaultKeyStatistics,summaryDetail,price"
    j = get(f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{sym}?modules={m}")["quoteSummary"]["result"][0]
    raw = lambda d, k: (d.get(k) or {}).get("raw") if isinstance(d.get(k), dict) else d.get(k)
    tr = {t["period"]: raw(t.get("earningsEstimate", {}), "avg") for t in j.get("earningsTrend", {}).get("trend", [])}
    fd, ks, sd, pr = j.get("financialData", {}), j.get("defaultKeyStatistics", {}), j.get("summaryDetail", {}), j.get("price", {})
    return {"bpaEst": tr, "roe": raw(fd, "returnOnEquity"), "detteTotale": raw(fd, "totalDebt"), "tresorerie": raw(fd, "totalCash"),
            "perCourant": raw(sd, "trailingPE"), "perPrevu": raw(sd, "forwardPE"), "dividende": raw(sd, "dividendRate"),
            "rendement": raw(sd, "dividendYield"), "bpaCourant": raw(ks, "trailingEps"), "bpaPrevu": raw(ks, "forwardEps"),
            "devise": pr.get("currency"), "devisePublication": fd.get("financialCurrency"), "cours": raw(pr, "regularMarketPrice"),
            "cible": raw(fd, "targetMeanPrice"), "cibleMed": raw(fd, "targetMedianPrice"), "nbAnalystes": raw(fd, "numberOfAnalystOpinions")}

def main(out, ids):
    res, err = {}, {}
    for i in ids:
        t = cours.TICKERS[i][0] if i in cours.TICKERS else (i if "." in i else i + ".PA")
        try:
            res[i] = {"ticker": t, "annuel": serie(t), **resume(t)}
        except Exception as e:  # noqa: BLE001
            err[i] = f"{t}: {e}"
        time.sleep(0.5)
    json.dump({"genere": datetime.now(timezone.utc).isoformat(timespec="minutes"), "valeurs": res, "erreurs": err},
              open(out, "w"), indent=1, ensure_ascii=False)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
