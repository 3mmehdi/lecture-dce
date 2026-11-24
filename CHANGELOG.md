# Journal des versions

Chaque version est évaluée sur les mêmes 5 dossiers, avec le même modèle (Claude Sonnet).

## Interface, 25/11/2026 : le skill dans Claude Code

- Nouvel onglet *Dans Claude Code* : le skill installé est appelé par `claude -p` avec une simple question, sans consigne. Le fil montre le choix du skill, le chargement de `SKILL.md`, la lecture de `references/points.md`, puis la réponse, contrôlée et notée comme au banc.
- Mesuré : cas-02 en 28 s, cas-03 en 36 s ; 0,21 à 0,23 $ (contre 0,19 $ en consigne injectée sur cas-03), 4 tours, 36/36 et 0 invention sur les deux. Le skill n'a pas changé.
- Les conversations sont enregistrées déjà traduites (aucun chemin ni configuration du poste) dans `evals/discussions/`, pour le mode Rejouer.

## 0.3.0, 24/11/2026 : expliquer chaque risque

- Chaque point `risque`, `eliminatoire` ou `a_verifier` porte `pourquoi` (règle déclenchée, coût calculé avec les seuls chiffres du dossier), `que_faire` (avec la date du dossier) et, quand elle peut lever le doute, `question` (prête à envoyer à l'acheteur, articles cités).
- Nouvelle liste `a_faire` : les actions datées avant la remise. Les `alertes` sont triées : éliminatoire, contradiction, risque.
- `references/points.md` dit, point par point, ce qui change le statut. `a_verifier` est réservé aux contradictions et aux renvois sans chiffre.
- Le banc contrôle les explications hors score : présentes sur chaque risque, question présente sur chaque point à vérifier, chiffres absents du dossier listés pour relecture.
- Premier passage : 98,9 %. Deux statuts glissaient vers « à vérifier » parce que la police d'assurance de l'entreprise n'est pas dans le dossier, et que « fermes et actualisables » semblait ambigu. Deux règles ajoutées à `points.md` : le statut se décide sur le dossier, la vérification interne va dans `que_faire` ; des prix fermes et actualisables restent fermes pendant les travaux.
- **Score : 100 %, 0 statut faux, 0 invention, 12 risques expliqués sur 12.** 0,17 $ et 30 s par dossier en moyenne : les explications doublent la durée, pas le coût.

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
