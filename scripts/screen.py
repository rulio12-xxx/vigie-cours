"""Filtre ponctuel : grandes valeurs françaises en baisse depuis un an (clôtures Yahoo sur 1 an)."""
import json, sys, time
from datetime import datetime, timezone
import cours
from historique import chart

LISTE = "AC AI AIR MT.AS CS BNP EN CAP CA ACA BN DSY EDEN ENGI EL ERF RMS KER OR LR MC ML ORA RI PUB RNO SAF SGO SAN SU GLE STLAP STMPA TEP HO TTE URW VIE DG BVI SW FR AKE ALO BOL COFA DIM ELIS ERA FGR GTT IPN RXL SOI SPIE TFI UBI VK RCO AF ADP WLN SOP ATE BIM NK AMUN TE VIV DEC RF LI COV GET NEX FDJ RUI AYV MF ENX VIRP OVH CARM SK".split()

def main(out):
    res, err = {}, {}
    for t in LISTE:
        y = t if "." in t else t + ".PA"
        try:
            dev, s = chart(y)
            c = [x[1] for x in s]
            hi, lo, last, first = max(c), min(c), c[-1], c[0]
            dhi = max(s, key=lambda x: x[1])[0].isoformat(); dlo = min(s, key=lambda x: x[1])[0].isoformat()
            res[t] = {"dernier": round(last, 2), "date": s[-1][0].isoformat(), "plusHaut": round(hi, 2), "dateHaut": dhi,
                      "plusBas": round(lo, 2), "dateBas": dlo, "depuisHaut": round(last / hi - 1, 4),
                      "surBas": round(last / lo - 1, 4), "sur1an": round(last / first - 1, 4), "devise": dev}
        except Exception as e:  # noqa: BLE001
            err[t] = str(e)
        time.sleep(0.4)
    json.dump({"genere": datetime.now(timezone.utc).isoformat(timespec="minutes"), "valeurs": res, "erreurs": err},
              open(out, "w"), indent=1)

if __name__ == "__main__":
    main(sys.argv[1])
