# Journal des versions

Chaque version est évaluée sur les mêmes 5 dossiers, avec le même modèle (Claude Sonnet).

## Interface locale, 24/11/2026

- `python app.py` : lire un dossier en voyant d'où vient chaque valeur, et relancer le banc dans le navigateur. Modes *En direct* et *Rejouer*. 12 tests.
- Contrôle à nouveau le 24/11 en direct : 100 % sur les 5 dossiers, 0 invention.

## 0.2.0, 20/11/2026 : le skill

- Définition écrite de chaque statut (`eliminatoire`, `risque`, `ok`, `a_verifier`, `non_trouve`).
- Règle sur les contradictions entre pièces : les deux valeurs, les deux sources, une alerte, aucun arbitrage.
- Les 12 points et la pièce où les chercher, dans `references/points.md`.
- Contre-déclencheurs dans la description : ni lecture de CCTP pour l'exécution, ni chiffrage, ni mémoire technique.
- **Score : 100 %, 0 statut faux, 0 invention.** 0,17 $ et 15 s par dossier en moyenne.

## Grille corrigée, 20/11/2026

Premier passage de la 0.2.0 : 98,9 %. Les deux points perdus ont été relus un par un : c'étaient deux erreurs de la grille, pas du skill.
- Une valeur « non obligatoire » refusée faute du mot exact attendu.
- Un risque que la grille avait noté « sûr ».

Après correction : 0.2.0 à 100 %, 0.1.0 à 95 % (93,9 % avant correction).

## 0.1.0, 20/11/2026 : la consigne simple

- Une phrase et la liste des 12 clés, sans définition des statuts. Sert de point de comparaison.
- **Score : 95 %, 9 statuts faux, 0 invention.** Erreur dominante : « à vérifier » par prudence, qui noie la vraie alerte.
