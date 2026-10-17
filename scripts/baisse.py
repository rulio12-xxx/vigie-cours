"""Niveau de baisse (0 à 4) de chaque ligne, critères cumulatifs :
  1 : 3 baisses consécutives sur les 4 derniers relevés de créneau (tâches 9h25 / 13h05 / 19h50)
  2 : + 3 baisses consécutives de clôture journalière (le jour en cours compte avec le dernier cours)
  3 : + au moins 2 semaines en baisse sur les 3 dernières (clôtures hebdomadaires)
  4 : + baisse sur 52 semaines
Usage : python3 baisse.py cours.json dossier_releves cache_quotidien.json sortie.json
Le cache des clôtures journalières est rechargé une fois par jour."""
import json, os, sys, time
from datetime import datetime, timezone, timedelta
import cours

PARIS = cours.PARIS


def serie(ticker):
    j = cours.fetch(ticker, "13mo", "1d")
    r = j["chart"]["result"][0]
    ts, cl = r.get("timestamp") or [], (r["indicators"]["quote"][0].get("close") or [])
    out = {}
    for t, c in zip(ts, cl):
        if c is not None:
            out[datetime.fromtimestamp(t, timezone.utc).astimezone(PARIS).strftime("%Y-%m-%d")] = round(c, 4)
    return out


def charge_cache(path, data, today):
    try:
        c = json.load(open(path))
    except Exception:  # noqa: BLE001
        c = {}
    if c.get("date") == today:
        manque = [k for k in data["lignes"] if k not in c.get("series", {})]
    else:
        c, manque = {"date": today, "series": {}}, list(data["lignes"])
    for k in manque:
        tk = data["lignes"][k]["ticker"]
        try:
            s = serie(tk)
            c["series"][k] = {d: v for d, v in s.items() if d < today}
        except Exception as e:  # noqa: BLE001
            print("série indisponible", k, tk, e)
        time.sleep(0.4)
    json.dump(c, open(path, "w"), separators=(",", ":"))
    return c


def creneaux(dossier, pendant):
    vals = {}
    for nom in sorted(f[:-4] for f in os.listdir(dossier) if f.endswith(".txt")):
        if nom >= pendant:
            continue
        for ligne in open(os.path.join(dossier, nom + ".txt"), encoding="utf-8"):
            p = ligne.strip().split(";")
            if len(p) >= 2 and p[0] not in ("id", "erreur", "fin") and not p[0].startswith("releve"):
                try:
                    vals.setdefault(p[0], []).append((nom, float(p[1])))
                except ValueError:
                    pass
    return vals


def baisses(v):
    return sum(1 for a, b in zip(v, v[1:]) if b < a)


def main(cours_json, dossier, cache, out):
    data = json.load(open(cours_json))
    now = datetime.now(PARIS)
    today = now.strftime("%Y-%m-%d")
    c = charge_cache(cache, data, today)
    sl = creneaux(dossier, cours.creneau(now))
    res = {}
    for k, q in data["lignes"].items():
        actuel = q.get("coursDevise", q["cours"])
        s = c["series"].get(k) or {}
        jours = sorted(s.items())
        if q.get("date") == today:
            jours.append((today, actuel))
        # 1 : créneaux
        cr = [v for _, v in sl.get(k, [])][-4:]
        c1 = len(cr) == 4 and baisses(cr) == 3
        # 2 : jours
        dj = [v for _, v in jours][-4:]
        c2 = len(dj) == 4 and baisses(dj) == 3
        # 3 : semaines (dernière clôture de chaque semaine ISO)
        sem = {}
        for d, v in jours:
            y, w, _ = datetime.strptime(d, "%Y-%m-%d").isocalendar()
            sem[(y, w)] = v
        ws = [sem[x] for x in sorted(sem)][-4:]
        c3 = len(ws) == 4 and baisses(ws) >= 2
        # 4 : 52 semaines
        lim = (now - timedelta(days=364)).strftime("%Y-%m-%d")
        anc = [v for d, v in jours if d <= lim]
        ref = anc[-1] if anc else (jours[0][1] if jours and jours[0][0] <= (now - timedelta(days=350)).strftime("%Y-%m-%d") else None)
        c4 = ref is not None and actuel < ref
        niv = 0
        for ok in (c1, c2, c3, c4):
            if not ok:
                break
            niv += 1
        res[k] = {"niveau": niv, "creneaux": c1, "jours": c2, "semaines": c3, "an": c4,
                  "detail": {"creneaux": cr, "jours": dj, "semaines": ws,
                             "il_y_a_52_sem": ref, "var52": round(actuel / ref - 1, 4) if ref else None}}
    json.dump({"releve": now.strftime("%Y-%m-%d %H:%M"), "fuseau": "Europe/Paris",
               "regles": "Cumulatif. 1 : 3 baisses consécutives sur 3 créneaux de tâche · 2 : + 3 jours de baisse consécutifs · 3 : + au moins 2 semaines de baisse sur les 3 dernières · 4 : + baisse sur 52 semaines",
               "lignes": res}, open(out, "w"), ensure_ascii=False, indent=1, sort_keys=True)
    from collections import Counter
    print("niveaux", dict(Counter(r["niveau"] for r in res.values())))


if __name__ == "__main__":
    main(*sys.argv[1:5])
