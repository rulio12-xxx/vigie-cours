# vigie-cours

Relevé automatique de cours de bourse (API Yahoo Finance, différé d'environ 15 min), publié dans `donnees/cours.json` sur la branche `cours`.

- Robot : [`scripts/cours.py`](scripts/cours.py), lancé toutes les 10 minutes en semaine par [`.github/workflows/cours.yml`](.github/workflows/cours.yml).
- Lecture : https://raw.githubusercontent.com/rulio12-xxx/vigie-cours/cours/donnees/cours.json

Format : `{releve, lignes: {<id>: {cours, date, heure, variation, veille, ticker, ageMin, avantOuverture}}, erreurs}`. `avantOuverture` = la place n'a pas encore ouvert aujourd'hui (le cours est alors la dernière clôture). Les valeurs en devise (`CONVERTIR`) sont converties en euros ; `coursDevise` et `taux` gardent l'original. Pour suivre une nouvelle valeur, ajouter son ticker Yahoo dans `TICKERS`.
