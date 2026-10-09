"""Relève les cours du jour sur l'API Yahoo Finance et écrit donnees/cours.json.

Lancé par .github/workflows/cours.yml (serveurs GitHub, accès internet direct,
sans cache). Chaque cours est horodaté avec l'heure de cotation fournie par Yahoo.
"""
import json, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")

# identifiant de document Vigie -> tickers Yahoo à essayer dans l'ordre
TICKERS = {
    "abionyx": ["ABNX.PA"], "abivax": ["ABVX.PA"], "alten": ["ATE.PA"],
    "aubay": ["AUB.PA"], "biomerieux": ["BIM.PA"], "bnp-paribas": ["BNP.PA"],
    "coface": ["COFA.PA"], "eiffage": ["FGR.PA"], "elis": ["ELIS.PA"],
    "engie": ["ENGI.PA"], "equasens": ["EQS.PA"], "essilorluxottica": ["EL.PA"],
    "fountaine-pajot": ["ALFPC.PA"], "gtt": ["GTT.PA"], "infotel": ["INF.PA"],
    "ipsen": ["IPN.PA"], "maurel-prom": ["MAU.PA"], "nexans": ["NEX.PA"],
    "pernod-ricard": ["RI.PA"], "renault": ["RNO.PA"], "robertet": ["RBT.PA"],
    "safran": ["SAF.PA"], "saint-gobain": ["SGO.PA"], "sanofi": ["SAN.PA"],
    "scor": ["SCR.PA"], "semco": ["ALSEM.PA"], "societe-generale": ["GLE.PA"],
    "stellantis": ["STLAP.PA"], "sword": ["SWP.PA"], "technip-energies": ["TE.PA"],
    "totalenergies": ["TTE.PA"], "trigano": ["TRI.PA"], "umg": ["UMG.AS"],
    "wavestone": ["WAVE.PA"], "stmicroelectronics": ["STMPA.PA"], "opmobility": ["OPM.PA"], "air-liquide": ["AI.PA"],
    # ETF / ETC
    "amundi-cac40": ["CACC.PA"], "amundi-dax": ["DAX.PA"], "amundi-gold": ["GOLD.PA", "GLDA.DE", "GOLD.AS"],
    "amundi-msci-world": ["WLD.PA", "CW8.PA"], "copap": ["COPAP.PA"], "dcam": ["DCAM.PA"],
    "lithium-batteries": ["BATT.PA", "BATT.AS", "BATE.DE"], "mth-oblig-25y": ["MTH.PA"],
    "nucl": ["NUCL.PA", "NUCL.AS", "NUCL.DE"], "paasi": ["PAASI.PA"], "pceu": ["PCEU.PA"],
    "psp5": ["PSP5.PA"], "ptpxh": ["PTPXH.PA"], "pust": ["PUST.PA"],
    "remx": ["REMX.PA", "REMX.AS", "REMX.DE"],
    # actions étrangères (cours converti en euros, voir CONVERTIR)
    "ge-healthcare": ["GEHC"],
    # indices de référence des fonds PEE
    "indice-stoxx600": ["^STOXX"],
}

# lignes cotées en devise : cours converti en euros au taux Yahoo du moment
CONVERTIR = {"ge-healthcare": ("USD", "EURUSD=X")}

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}

# Yahoo refuse (429) les requêtes « nues » venant des serveurs : on imite un
# navigateur (curl_cffi) et on récupère cookie + crumb comme le fait yfinance.
try:
    from curl_cffi import requests as creq
    SESSION = creq.Session(impersonate="chrome")
except ImportError:  # repli sans curl_cffi
    SESSION = None
CRUMB = None


def _init_session():
    global CRUMB
    if SESSION is None or CRUMB is not None:
        return
    try:
        SESSION.get("https://fc.yahoo.com", timeout=20)
    except Exception:  # noqa: BLE001  (fc.yahoo.com répond souvent 404, seul le cookie compte)
        pass
    r = SESSION.get("https://query1.finance.yahoo.com/v1/test/getcrumb", timeout=20)
    CRUMB = r.text.strip() if r.status_code == 200 else ""


def fetch(ticker):
    err = "?"
    for attempt in range(3):
        host = ("query1", "query2", "query1")[attempt]
        url = f"https://{host}.finance.yahoo.com/v8/finance/chart/{ticker}?range=1d&interval=5m"
        try:
            if SESSION is not None:
                _init_session()
                if CRUMB:
                    url += f"&crumb={CRUMB}"
                r = SESSION.get(url, timeout=20)
                if r.status_code == 200:
                    return r.json()
                err = f"HTTP {r.status_code}"
            else:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
                    return json.load(r)
        except Exception as e:  # noqa: BLE001
            err = str(e)
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(err)


def quote(ticker):
    j = fetch(ticker)
    res = (j.get("chart") or {}).get("result") or []
    if not res:
        raise RuntimeError("pas de résultat")
    m = res[0]["meta"]
    prix, t = m.get("regularMarketPrice"), m.get("regularMarketTime")
    if prix is None or t is None:
        raise RuntimeError("pas de cours")
    # dernier point intraday réellement échangé (confirme le prix)
    q = (res[0].get("indicators") or {}).get("quote") or [{}]
    closes = [c for c in (q[0].get("close") or []) if c is not None]
    dt = datetime.fromtimestamp(t, timezone.utc).astimezone(PARIS)
    prev = m.get("chartPreviousClose") or m.get("previousClose")
    reg = ((m.get("currentTradingPeriod") or {}).get("regular") or {})
    avant = bool(reg.get("start") and time.time() < reg["start"]
                 and datetime.fromtimestamp(reg["start"], timezone.utc).astimezone(PARIS).date() == datetime.now(PARIS).date())
    return {
        "avantOuverture": avant,
        "ticker": ticker,
        "cours": round(prix, 4),
        "dernierPoint": round(closes[-1], 4) if closes else None,
        "devise": m.get("currency"),
        "date": dt.strftime("%Y-%m-%d"),
        "heure": dt.strftime("%H:%M"),
        "veille": prev,
        "variation": round((prix / prev - 1) * 100, 2) if prev else None,
        "differeMin": m.get("exchangeDataDelayedBy", 0) // 60 if m.get("exchangeDataDelayedBy") else 0,
        "place": m.get("exchangeName"),
    }


def main(out):
    now = datetime.now(PARIS)
    lignes, erreurs, fx_cache = {}, {}, {}
    for doc_id, cands in TICKERS.items():
        last = None
        for tk in cands:
            try:
                qd = quote(tk)
            except Exception as e:  # noqa: BLE001
                last = f"{tk}: {e}"
                continue
            conv = CONVERTIR.get(doc_id)
            if conv and qd["devise"] == conv[0]:
                fx = fx_cache.get(conv[1])
                if fx is None:
                    fx = fx_cache[conv[1]] = quote(conv[1])["cours"]
                qd["coursDevise"], qd["veilleDevise"], qd["taux"] = qd["cours"], qd["veille"], fx
                qd["cours"] = round(qd["cours"] / fx, 4)
                qd["veille"] = round(qd["veille"] / fx, 4) if qd["veille"] else None
                qd["devise"] = "EUR"
            if qd["devise"] not in ("EUR", None) and not tk.startswith("^"):
                last = f"{tk}: devise {qd['devise']} (cours {qd['cours']} le {qd['date']} {qd['heure']})"
                continue
            q_dt = datetime.strptime(qd["date"] + " " + qd["heure"], "%Y-%m-%d %H:%M").replace(tzinfo=PARIS)
            qd["ageMin"] = int((now - q_dt).total_seconds() // 60)
            lignes[doc_id] = qd
            break
        else:
            erreurs[doc_id] = last
        time.sleep(0.5)
    data = {
        "releve": now.strftime("%Y-%m-%d %H:%M"),
        "fuseau": "Europe/Paris",
        "source": "Yahoo Finance API v8 chart (regularMarketPrice / regularMarketTime)",
        "lignes": lignes,
        "erreurs": erreurs,
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)
    # relevé « créneau » à adresse unique (l'outil de lecture des tâches garde
    # chaque adresse en cache indéfiniment : chaque créneau a donc sa propre URL)
    import os
    nom = creneau(now)
    os.makedirs(os.path.join(os.path.dirname(out) or ".", "releves"), exist_ok=True)
    with open(os.path.join(os.path.dirname(out) or ".", "releves", nom + ".txt"), "w", encoding="utf-8") as f:
        f.write(texte_creneau(data))
    print("créneau", nom)
    print(f"{len(lignes)} cours, {len(erreurs)} erreurs")
    for k, v in erreurs.items():
        print("ERREUR", k, v)


CRENEAUX = ("0925", "1305", "1950")  # heures (Paris) des tâches planifiées


def creneau(now):
    """Nom du prochain créneau de tâche : AAAA-MM-JJ-HHMM."""
    hm = now.strftime("%H%M")
    if now.weekday() < 5:
        for c in CRENEAUX:
            if hm < c:
                return now.strftime("%Y-%m-%d-") + c
    d = now + timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d.strftime("%Y-%m-%d-") + CRENEAUX[0]


def texte_creneau(data):
    lignes = [f"releve={data['releve']} (heure de Paris)",
              "id;cours_eur;date;heure;variation_pct;avantOuverture;cours_devise;taux"]
    for k in sorted(data["lignes"]):
        q = data["lignes"][k]
        lignes.append(";".join(str(x) for x in (
            k, q["cours"], q["date"], q["heure"], q.get("variation"),
            "oui" if q.get("avantOuverture") else "non",
            q.get("coursDevise", ""), q.get("taux", ""))))
    for k, v in sorted(data["erreurs"].items()):
        lignes.append(f"erreur;{k};{v}")
    lignes.append("fin")
    return "\n".join(lignes) + "\n"


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "donnees/cours.json")
