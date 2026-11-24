# lecture-dce

**Un skill Claude qui lit un dossier de consultation (DCE) de marché public de travaux et relève les 12 points qu'un chargé d'études ne doit pas rater**, avec la source de chacun. Il signale ce qui est éliminatoire ou risqué, et ne remplit jamais un trou par une valeur « habituelle ».

> *A Claude skill that reads a French public works tender file (DCE) and extracts the 12 points a bid engineer must not miss, each with its source. Evaluated against a plain prompt on 5 test files. Written in French.*

Le dépôt contient le skill **et son banc d'évaluation** : on ne diffuse pas un skill dont on n'a pas mesuré la qualité.

---

## Résultats (20/11/2026, Claude Sonnet, 5 dossiers fictifs)

| | Consigne simple (v0.1) | Skill (v0.2) |
|---|---|---|
| Score global | 95 % | **100 %** |
| Statuts faux | 9 | **0** |
| Valeurs inventées (sur 10 points absents des dossiers) | 0 | **0** |
| Coût moyen par dossier | | 0,17 $ |
| Durée moyenne par dossier | | 15 s |

Les deux versions trouvent les chiffres. La différence est dans le jugement : la consigne simple classe trop souvent « à vérifier » par prudence, et la vraie alerte se perd. Le skill définit chaque statut, et l'erreur tombe à zéro.

⚠️ **Limites** : cinq dossiers écrits par moi, c'est un banc d'essai, pas une preuve. Un pilote se juge sur 20 dossiers réels. Un seul modèle testé.

---

## Lancer l'évaluation

**Prérequis** : Python 3.10 ou plus (bibliothèque standard seulement), et la CLI [Claude Code](https://docs.claude.com/en/docs/claude-code) installée et connectée (`claude --version` doit répondre).

```bash
# 1. (Re)générer les 5 dossiers de test et leurs réponses attendues
python evals/creer_cas.py

# 2. Évaluer la version actuelle du skill, résultats dans evals/resultats-essai.json
python evals/evaluer.py essai

# 3. Même chose avec un autre modèle
python evals/evaluer.py essai opus

# 4. Rejouer la consigne simple, pour comparer
python evals/evaluer.py v0.1
```

Le premier argument est une **étiquette** : `v0.1` lance la consigne simple, toute autre étiquette lance le skill (`SKILL.md` + `references/points.md`). Les résultats sont écrits dans `evals/resultats-<étiquette>.json`.

⚠️ `python evals/evaluer.py v0.2` **remplace** les résultats publiés ci-dessus. Pour un essai, utiliser une autre étiquette.

Le script affiche une ligne par dossier, puis le score :

```
cas-01 36/36 inventions: 0 15s
...
SCORE essai 100.0 % · inventions 0
```

---

## Comment c'est noté

- **12 points par dossier, 3 points chacun** : la valeur juste (les mots attendus sont présents), le statut juste, la source citée. Soit 36 points par dossier.
- **Une invention** (une valeur donnée là où le dossier ne dit rien) **est comptée à part.** En marché public, c'est l'erreur la plus grave.
- **Normalisation avant comparaison** : forme Unicode (NFKC), espaces insécables, majuscules. Sinon on compte des fautes qui n'en sont pas.
- **Pas de LLM juge** : les réponses sont factuelles (une date, un taux, un article). Une comparaison exacte est reproductible et ne coûte rien.
- **La grille se trompe aussi** : au premier passage, le skill perdait deux points qui étaient deux erreurs de la grille. Elles sont corrigées et tracées dans le [CHANGELOG](CHANGELOG.md).

---

## Structure

```
lecture-dce/
  SKILL.md                consignes, déclencheur, contre-déclencheurs
  references/points.md    les 12 points et où les chercher
  evals/
    creer_cas.py          dossiers de test + réponses attendues
    evaluer.py            exécute, note, trace coût et durée
    resultats-v0.1.json   consigne simple
    resultats-v0.2.json   skill
  CHANGELOG.md            chaque version et son score
```

La description du skill dit **quand l'utiliser et quand ne pas l'utiliser** (lecture d'un CCTP pour l'exécution, chiffrage, mémoire technique). C'est ce qui évite qu'il entre en collision avec un autre skill.

---

## Licence

MIT. Les dossiers de consultation sont fictifs.

Mehdi Mezouar · [Arkodis](https://arkodis.fr)
