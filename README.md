# vigie-cours

Relevé automatique de cours de bourse (API Yahoo Finance, différé d'environ 15 min), publié dans `donnees/cours.json` sur la branche `cours`.

- Robot : [`scripts/cours.py`](scripts/cours.py), lancé toutes les 10 minutes en semaine par [`.github/workflows/cours.yml`](.github/workflows/cours.yml).
- Lecture : https://raw.githubusercontent.com/rulio12-xxx/vigie-cours/cours/donnees/cours.json

Format : `{releve, lignes: {<id>: {cours, date, heure, variation, veille, ticker, ageMin, avantOuverture}}, erreurs}`. `avantOuverture` = la place n'a pas encore ouvert aujourd'hui (le cours est alors la dernière clôture). Les valeurs en devise (`CONVERTIR`) sont converties en euros ; `coursDevise` et `taux` gardent l'original. Pour suivre une nouvelle valeur, ajouter son ticker Yahoo dans `TICKERS`.

## Relevés par créneau (anti-cache)

L'outil de lecture web des tâches planifiées garde chaque adresse en cache très longtemps : relire `cours.json` renvoie un vieux relevé. Chaque passage du robot écrit donc aussi un relevé à **adresse unique par créneau de tâche** : `donnees/releves/AAAA-MM-JJ-HHMM.txt` (branche `cours`), HHMM = 0925, 1305 ou 1950 (prochaine tâche à venir). Les tâches trouvent l'adresse via des index fixes : [`index/racine.md`](index/racine.md) → `index/AAAA-MM.md` → relevé du créneau. Les index ne changent jamais (2026-10 à 2028-12) ; prolonger avant 2029 en ajoutant de nouveaux mois **dans un nouveau fichier racine**.
