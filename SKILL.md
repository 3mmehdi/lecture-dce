---
name: lecture-dce
description: Relève les 12 points à vérifier dans un dossier de consultation des entreprises (DCE) d'un marché public de travaux (règlement de consultation, CCAP, acte d'engagement), avec la source de chaque point. À utiliser quand un chargé d'études demande « analyse ce DCE », « qu'est-ce qu'il faut retenir de cet appel d'offres », « relève les clauses à risque du CCAP ». Ne pas utiliser pour lire un CCTP à des fins d'exécution de chantier, pour chiffrer une offre, ni pour rédiger un mémoire technique.
version: 0.2.0
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

Ajoute une clé `alertes` : une liste de phrases courtes, une par point à risque, éliminatoire ou contradictoire.

## Règles

1. **Recopie les chiffres à l'identique** : dates, heures, pourcentages, montants, fractions (1/1000, 1/3000). Ne convertis rien.
2. **Cite la source de chaque valeur** : la pièce (RC, CCAP, AE) et le numéro d'article tel qu'il apparaît.
3. **N'invente rien.** Si un point n'est pas dans le dossier, `valeur` = "non trouvé", `source` = "", `statut` = `non_trouve`. Ne complète jamais avec une valeur « habituelle » des marchés publics.
4. **Contradiction entre deux pièces** : statut `a_verifier`, les deux valeurs et les deux sources dans `valeur` et `source`, et une alerte. Ne choisis pas à la place du chargé d'études.
5. Statuts :
   - `eliminatoire` : une condition dont l'oubli fait rejeter l'offre (visite obligatoire avec attestation, pièce exigée à peine d'irrecevabilité).
   - `risque` : une clause qui coûte cher si elle joue (pénalités sans plafond ou supérieures à 1/1000 par jour, révision des prix exclue sur un marché de plus de 3 mois, assurance au-delà du standard).
   - `ok` : le reste quand c'est trouvé.

Détail des 12 points et où les chercher : [references/points.md](references/points.md).
