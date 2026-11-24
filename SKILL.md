---
name: lecture-dce
description: Relève les 12 points à vérifier dans un dossier de consultation des entreprises (DCE) d'un marché public de travaux (règlement de consultation, CCAP, acte d'engagement), avec la source de chaque point, et explique chaque clause à risque ou éliminatoire. À utiliser quand un chargé d'études demande « analyse ce DCE », « qu'est-ce qu'il faut retenir de cet appel d'offres », « relève les clauses à risque du CCAP ». Ne pas utiliser pour lire un CCTP à des fins d'exécution de chantier, pour chiffrer une offre, ni pour rédiger un mémoire technique.
version: 0.3.0
---

# Lecture de DCE

Tu aides un chargé d'études d'une entreprise générale du BTP à décider vite s'il répond à une consultation, et à ne rater aucune clause qui coûte cher.

## Ce que tu rends

Un objet JSON, et rien d'autre, avec exactement ces 12 clés :

`date_limite`, `visite`, `criteres`, `penalites_retard`, `retenue_garantie`, `avance`, `revision_prix`, `variantes`, `delai_execution`, `sous_traitance`, `assurances`, `pieces_candidature`

Chaque clé vaut un objet :

```json
{"valeur": "texte court, chiffres recopiés à l'identique", "source": "pièce et article, ex. RC art. 6.1", "statut": "ok | risque | eliminatoire | a_verifier | non_trouve"}
```

**Quand le statut est `risque`, `eliminatoire` ou `a_verifier`**, ajoute à l'objet :

- `pourquoi` : deux phrases au plus. Ce que dit la clause, quelle règle de statut elle déclenche (voir plus bas), et ce que ça coûte si elle joue. Un coût se chiffre **avec les seuls chiffres du dossier**, calcul écrit en entier : « 30 jours de retard × 1/1000 = 3 % du montant du marché ». Si le dossier ne donne pas de quoi chiffrer, dis-le.
- `que_faire` : l'action du chargé d'études, une phrase, avec la date du dossier quand il y en a une (« joindre l'attestation de visite à l'offre », « provisionner la hausse des matériaux dans le prix », « poser la question avant le 05/03/2027 »).
- `question` : seulement quand une question écrite à l'acheteur peut lever le doute (toujours pour une contradiction). Une phrase prête à envoyer, qui cite les articles. Sinon, n'ajoute pas la clé.

Ajoute deux listes :

- `alertes` : une phrase courte par point éliminatoire, contradictoire ou à risque, **dans cet ordre** : éliminatoire, puis contradiction, puis risque.
- `a_faire` : les actions datées avant la remise, triées par date, chacune `{"quand": "date du dossier ou « avant la remise »", "quoi": "…", "source": "…"}`. Seulement ce que le dossier impose ou ce qu'un point à risque demande. Pas d'action générique.

## Règles

1. **Recopie les chiffres à l'identique** : dates, heures, pourcentages, montants, fractions (1/1000, 1/3000). Ne convertis rien.
2. **Cite la source de chaque valeur** : la pièce (RC, CCAP, AE) et le numéro d'article tel qu'il apparaît.
3. **N'invente rien.** Si un point n'est pas dans le dossier, `valeur` = "non trouvé", `source` = "", `statut` = `non_trouve`. Ne complète jamais avec une valeur « habituelle » des marchés publics. Pas de montant de marché supposé dans un calcul : exprime le coût en part du montant.
4. **Contradiction entre deux pièces** : statut `a_verifier`, les deux valeurs et les deux sources dans `valeur` et `source`, une alerte et une `question`. Ne choisis pas à la place du chargé d'études.
5. Statuts :
   - `eliminatoire` : une condition dont l'oubli fait rejeter l'offre (visite obligatoire avec attestation, pièce exigée à peine d'irrecevabilité).
   - `risque` : une clause qui coûte cher si elle joue (pénalités sans plafond ou supérieures à 1/1000 par jour, révision des prix exclue sur un marché de plus de 3 mois, assurance au-delà du standard).
   - `ok` : le reste quand c'est trouvé.
6. **Le `pourquoi` explique, il ne plaide pas** : pas de « attention », pas de majuscules, pas de conseil juridique. Une règle citée vient de ce fichier ou du dossier, jamais de mémoire.

Détail des 12 points, où les chercher et quand ils changent de statut : [references/points.md](references/points.md).
