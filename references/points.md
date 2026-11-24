# Les 12 points, où les chercher, quand ils changent de statut

| Clé | Ce qu'on cherche | Pièce habituelle | Ce qui change le statut |
|---|---|---|---|
| date_limite | Date et heure limites de remise des offres | RC | `ok` si trouvée. Elle date les actions de `a_faire`. |
| visite | Visite de site : obligatoire (avec attestation ?), facultative, absente | RC | `eliminatoire` si obligatoire avec attestation, ou si un rejet est annoncé. |
| criteres | Critères de jugement et leur pondération | RC | `ok`. Le `pourquoi` d'un autre point peut citer le poids du critère qu'il touche (délai, prix). |
| penalites_retard | Montant par jour de retard, plafond éventuel | CCAP | `risque` au-delà de 1/1000 par jour ou sans plafond. Simple renvoi au CCAG : `a_verifier` ou `ok`. |
| retenue_garantie | Taux, possibilité de la remplacer par une garantie | CCAP | `a_verifier` au-delà de 5 %. |
| avance | Taux de l'avance, conditions (garantie à première demande ?) | CCAP ou AE | `ok`. Une garantie exigée va dans `a_faire`. |
| revision_prix | Prix fermes, actualisables ou révisables ; index (BT01…) | CCAP | `risque` si les prix sont fermes et non révisables sur plus de 3 mois. « Fermes et actualisables » reste ferme pendant les travaux (l'actualisation ne joue qu'au démarrage) : même règle. |
| variantes | Autorisées, interdites, limitées à un périmètre | RC | `ok`. |
| delai_execution | Durée des travaux, période de préparation incluse ou non | AE ou CCAP | `a_verifier` si deux pièces se contredisent. |
| sous_traitance | Conditions de déclaration, paiement direct, limites | CCAP | `ok`, ou `risque` si une limite chiffrée gêne une offre qui sous-traite. |
| assurances | Responsabilité civile, décennale, montants exigés | CCAP ou RC | `ok`, ou `risque` si un montant minimum est exigé. La comparaison avec la police de l'entreprise va dans `que_faire`. |
| pieces_candidature | Formulaires et attestations exigés (DC1, DC2, Kbis…) | RC | `eliminatoire` si « à peine d'irrecevabilité » ou si un rejet est annoncé. Une durée de validité (Kbis de moins de 3 mois) va dans `a_faire`. |

## `a_verifier` : seulement deux cas

Une contradiction entre deux pièces, ou un renvoi sans chiffre (« conformément au CCAG »). Jamais pour ce que seule l'entreprise sait (sa police d'assurance, son planning, son carnet de commandes) : le statut se décide sur le dossier, et la vérification interne va dans `que_faire`. Un « à vérifier » posé par prudence noie la vraie alerte.
