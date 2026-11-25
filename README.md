# lecture-dce

**Un skill Claude qui lit un dossier de consultation (DCE) de marché public de travaux et relève les 12 points qu'un chargé d'études ne doit pas rater**, avec la source de chacun. Il signale ce qui est éliminatoire ou risqué, explique pourquoi et ce qu'il faut faire, et ne remplit jamais un trou par une valeur « habituelle ».

> *A Claude skill that reads a French public works tender file (DCE) and extracts the 12 points a bid engineer must not miss, each with its source. Evaluated against a plain prompt on 5 test files. Written in French.*

Le dépôt contient le skill **et son banc d'évaluation** : on ne diffuse pas un skill dont on n'a pas mesuré la qualité.

---

## Résultats (Claude Sonnet, 5 dossiers fictifs)

| | Consigne simple (v0.1) | Skill (v0.2, 20/11) | Skill (v0.3, 24/11) |
|---|---|---|---|
| Score global | 95 % | **100 %** | **100 %** |
| Statuts faux | 9 | **0** | **0** |
| Valeurs inventées (sur 10 points absents des dossiers) | 0 | **0** | **0** |
| Risques expliqués (pourquoi + que faire) | | | **12 sur 12** |
| Coût moyen par dossier | | 0,17 $ | 0,17 $ |
| Durée moyenne par dossier | | 15 s | 30 s |

Les deux versions trouvent les chiffres. La différence est dans le jugement : la consigne simple classe trop souvent « à vérifier » par prudence, et la vraie alerte se perd. Le skill définit chaque statut, et l'erreur tombe à zéro.

La v0.3 ajoute, pour chaque point à risque, éliminatoire ou à vérifier : **pourquoi** (la règle déclenchée et le coût, calculé avec les seuls chiffres du dossier), **que faire** (avec la date du dossier), et **la question à poser à l'acheteur** quand elle peut lever le doute. Plus une liste d'actions datées avant la remise. Le score sur 36 ne change pas : les explications sont contrôlées à part (présentes ? chiffres retrouvés dans le dossier ?).

⚠️ **Limites** : cinq dossiers écrits par moi, c'est un banc d'essai, pas une preuve. Un pilote se juge sur 20 dossiers réels. Un seul modèle testé.

---

## Voir le skill travailler, dans le navigateur

```bash
python app.py
```

Puis ouvrir http://127.0.0.1:8790. Rien à installer : bibliothèque standard seulement, et le serveur n'écoute que sur le poste.

- **Lire un dossier** : choisir un des 5 dossiers (ou coller le texte d'un autre), lancer la lecture. La lecture passe par Claude Code, comme pour un chargé d'études : une question et le dossier, et Claude choisit le skill seul. Les 12 points s'affichent avec leur statut, les alertes et les actions datées avant la remise. Un clic sur un point allume, dans le dossier, l'article qu'il cite : on voit d'où vient chaque valeur. Le clic montre aussi la règle de `references/points.md` qui a fixé le statut ; sur un risque, il ouvre en plus le pourquoi, l'action à mener et la question à copier pour l'acheteur. En bas, les étapes (skill choisi, tours de Claude Code, réponse, contrôle du format, notation) avec leur durée et leur coût, la réponse brute, et un lien vers le déroulé de la conversation.
- **Dans Claude Code** : le déroulé de la conversation, qu'elle soit lancée ici ou depuis *Lire un dossier* (c'est la même : une lecture remplit les deux onglets). L'interface envoie seulement une question (« Analyse ce DCE… ») et le dossier à `claude -p`, sans consigne. Le fil montre Claude qui choisit le skill d'après sa description, charge `SKILL.md`, lit `references/points.md` à la demande, puis répond. À côté : les étapes, et l'écart avec le banc, qui injecte la consigne en un seul tour (tours, durée, coût). Un bouton ouvre la même réponse dans la vue *Lire un dossier*, avec la même note. Il faut d'abord installer le skill (voir plus bas).
- **Évaluer le skill** : la consigne simple et le skill côte à côte, dossier par dossier, et la liste des statuts que le skill corrige. Chaque version peut être relancée.
- **En direct ou Rejouer** : *En direct* appelle vraiment Claude (de 20 à 50 s par dossier). *Rejouer* réaffiche les réponses mesurées, sans appel : les conversations enregistrées dans `evals/discussions/`, une par dossier de test (36/36 et 0 invention sur les cinq).

L'interface réutilise les fonctions de `evals/evaluer.py` : le score affiché est exactement celui du banc. Tests : `python -m unittest discover -s tests`.

## Installer le skill dans Claude Code

```bash
mkdir -p ~/.claude/skills/lecture-dce/references
cp SKILL.md ~/.claude/skills/lecture-dce/
cp references/points.md ~/.claude/skills/lecture-dce/references/
```

Puis, dans une nouvelle session Claude Code, coller un DCE et demander « analyse ce DCE » : le skill se déclenche seul. Testé sur du texte ; pas encore mesuré sur un DCE en PDF.

## Le serveur MCP

`mcp_server.py` expose le banc d'évaluation à un agent, en 4 outils :

- `lister_dossiers` : les 5 dossiers de test, id et titre.
- `lire_dossier` : le texte d'un dossier (`cas-01` à `cas-05`, rien d'autre).
- `verifier_reponse` : le format d'une réponse du skill (12 clés, statuts connus, une source par valeur) et ses explications (pourquoi, que faire, question, chiffres absents du dossier).
- `noter_reponse` : la note sur 36, les inventions et les statuts faux, exactement comme le banc.

```bash
pip install mcp
python mcp_server.py
```

Le serveur parle en stdio. `.mcp.json` l'enregistre pour Claude Code dans ce dossier : au premier lancement de `claude`, il demande d'approuver le serveur. Aucun appel au modèle : tout est déterministe et gratuit.

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

⚠️ `python evals/evaluer.py v0.2` ou `v0.3` **remplace** les résultats publiés ci-dessus. Pour un essai, utiliser une autre étiquette.

Le script affiche une ligne par dossier, puis le score :

```
cas-01 36/36 inventions: 0 27s explications: 2/2
...
SCORE essai 100.0 % · inventions 0
```

---

## D'où viennent les seuils

Les règles de statut de `references/points.md` reprennent le droit des marchés publics de travaux, en plus prudent :

- pénalités de retard : le CCAG-Travaux 2021 prévoit par défaut 1/3000 du montant par jour, plafonné à 10 % (art. 19.2). Le skill classe en `risque` au-delà de 1/1000 par jour (trois fois le défaut) ou sans plafond ;
- retenue de garantie : le Code de la commande publique la plafonne à 5 % (R2191-33). Au-delà, le skill met `a_verifier` ;
- prix fermes : une clause de révision est obligatoire au-delà de 3 mois quand les matériaux suivent les cours mondiaux (R2112-14). Le skill classe en `risque` des prix fermes non révisables sur plus de 3 mois.

Le skill ne consulte aucun texte de loi : il applique ces seuils au seul dossier, et cite la pièce et l'article du dossier. Ce sont des choix de démonstration, à recaler avec les chargés d'études et le service juridique d'une entreprise avant tout usage réel.

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
  references/points.md    les 12 points, où les chercher, et les seuils qui fixent le statut
  evals/
    creer_cas.py          dossiers de test + réponses attendues
    evaluer.py            exécute, note, trace coût et durée
    resultats-v0.1.json   consigne simple
    resultats-v0.2.json   skill, sans explications
    resultats-v0.3.json   skill, avec explications (rejoué par l'interface)
    discussions/          conversations Claude Code enregistrées (rejouées par l'interface)
  app.py, ui/             l'interface locale (http://127.0.0.1:8790)
  mcp_server.py           le serveur MCP (4 outils, sans appel au modèle)
  .mcp.json               l'enregistre pour Claude Code dans ce dossier
  tests/                  tests de l'interface
    test_mcp.py           tests du serveur MCP, dont un échange réel en stdio
  CHANGELOG.md            chaque version et son score
```

La description du skill dit **quand l'utiliser et quand ne pas l'utiliser** (lecture d'un CCTP pour l'exécution, chiffrage, mémoire technique). C'est ce qui évite qu'il entre en collision avec un autre skill.

---

## Licence

MIT. Les dossiers de consultation sont fictifs.

Mehdi Mezouar · [Arkodis](https://arkodis.fr)
