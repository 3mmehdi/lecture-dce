# Génère les cas de test du skill lecture-dce : un DCE fictif (dce.md) et la réponse attendue (attendu.json).
# attendu : pour chaque clé, les mots qui doivent figurer dans la valeur, les statuts acceptés, et un repère de source.
import json, pathlib
ICI = pathlib.Path(__file__).parent
NT = {"mots": [], "statuts": ["non_trouve"], "source": ""}

def a(mots, statuts, source): return {"mots": mots, "statuts": statuts, "source": source}

CAS = {
"cas-01": ("""# Groupe scolaire Jean-Moulin — Lot 02 Gros œuvre
## Règlement de la consultation (RC)
Art. 3.5 Variantes : les variantes sont autorisées sur le plancher bas uniquement.
Art. 4.3 Visite : la visite du site est obligatoire. L'attestation de visite est jointe à l'offre, faute de quoi l'offre sera déclarée irrégulière.
Art. 5 Pièces de candidature : DC1, DC2, attestation d'assurance décennale en cours de validité.
Art. 6.1 Date limite : les offres sont remises au plus tard le 15/01/2027 à 12h00.
Art. 8 Jugement des offres : prix 50 %, valeur technique 40 %, performance environnementale 10 %.
## Cahier des clauses administratives particulières (CCAP)
Art. 3.2 Sous-traitance : tout sous-traitant est déclaré et agréé avant le début de son intervention ; paiement direct au-delà de 600 euros TTC.
Art. 5.2 Avance : une avance de 10 % est versée, sans constitution de garantie.
Art. 10.4 Prix : les prix sont révisables mensuellement selon l'index BT01.
Art. 11 Retenue de garantie : 5 %, remplaçable par une garantie à première demande.
Art. 12 Assurances : responsabilité civile et décennale, attestations exigées.
Art. 20.1 Pénalités de retard : 1/1000 du montant du marché par jour calendaire de retard, sans plafond.
## Acte d'engagement (AE)
Art. 4 Délai : 18 mois, période de préparation de 2 mois comprise.
""", {
 "date_limite": a(["15/01/2027", "12"], ["ok"], "6.1"),
 "visite": a(["obligatoire"], ["eliminatoire"], "4.3"),
 "criteres": a(["50", "40", "10"], ["ok"], "8"),
 "penalites_retard": a(["1/1000"], ["risque"], "20.1"),
 "retenue_garantie": a(["5"], ["ok"], "11"),
 "avance": a(["10"], ["ok"], "5.2"),
 "revision_prix": a(["BT01"], ["ok"], "10.4"),
 "variantes": a(["plancher"], ["ok"], "3.5"),
 "delai_execution": a(["18"], ["ok"], "4"),
 "sous_traitance": a(["600"], ["ok"], "3.2"),
 "assurances": a(["décennale"], ["ok"], "12"),
 "pieces_candidature": a(["DC1", "DC2"], ["ok", "eliminatoire"], "5"),
}),
"cas-02": ("""# Réhabilitation de 48 logements, résidence Les Tilleuls — Lot 01 Démolition et gros œuvre
## RC
Art. 2 Variantes : aucune variante n'est admise.
Art. 3 Visite : une visite facultative est organisée le 04/02/2027.
Art. 7 Remise des offres : avant le 26/02/2027, 16h00, sur la plateforme de dématérialisation.
Art. 9 Critères : valeur technique 60 %, prix 40 %.
## CCAP
Art. 4 Délai d'exécution : 10 mois à compter de l'ordre de service de démarrage.
Art. 6 Prix : les prix sont fermes et actualisables.
Art. 9 Retenue de garantie : 5 %.
Art. 14 Pénalités : 1/3000 du montant HT du marché par jour de retard, plafonnées à 10 % du montant du marché.
Art. 16 Sous-traitance : conformément au CCAG Travaux.
""", {
 "date_limite": a(["26/02/2027", "16"], ["ok"], "7"),
 "visite": a(["facultative"], ["ok"], "3"),
 "criteres": a(["60", "40"], ["ok"], "9"),
 "penalites_retard": a(["1/3000", "10"], ["ok"], "14"),
 "retenue_garantie": a(["5"], ["ok"], "9"),
 "avance": NT,
 "revision_prix": a(["fermes", "actualisables"], ["ok", "risque"], "6"),
 "variantes": a(["aucune"], ["ok"], "2"),
 "delai_execution": a(["10 mois"], ["ok"], "4"),
 "sous_traitance": a(["CCAG"], ["ok", "a_verifier"], "16"),
 "assurances": NT,
 "pieces_candidature": NT,
}),
"cas-03": ("""# Extension du centre technique municipal — Lot unique
## RC
Art. 1.4 Variantes : interdites.
Art. 2.1 Date et heure limites : 05/03/2027 à 11h30.
Art. 2.3 Visite : sans objet.
Art. 4 Candidature : DC1, DC2, Kbis de moins de 3 mois, à peine d'irrecevabilité.
Art. 5 Critères : prix 60 %, valeur technique 30 %, délai 10 %.
## CCAP
Art. 2.2 Délai global : 12 mois, période de préparation incluse.
Art. 3.1 Prix : les prix sont fermes, non actualisables et non révisables.
Art. 4.2 Avance : 5 %, sous réserve d'une garantie à première demande.
Art. 4.6 Retenue de garantie : 5 %.
Art. 8 Pénalités de retard : 500 euros HT par jour calendaire.
Art. 10 Assurances : décennale de 2 000 000 euros minimum par sinistre.
## Acte d'engagement
Art. 3 Délai : le titulaire s'engage sur un délai de 14 mois.
""", {
 "date_limite": a(["05/03/2027", "11"], ["ok"], "2.1"),
 "visite": a([], ["ok", "non_trouve"], ""),
 "criteres": a(["60", "30", "10"], ["ok"], "5"),
 "penalites_retard": a(["500"], ["ok", "risque"], "8"),
 "retenue_garantie": a(["5"], ["ok"], "4.6"),
 "avance": a(["5", "première demande"], ["ok"], "4.2"),
 "revision_prix": a(["fermes"], ["risque"], "3.1"),
 "variantes": a(["interdit"], ["ok"], "1.4"),
 "delai_execution": a(["12", "14"], ["a_verifier"], "2.2"),
 "sous_traitance": NT,
 "assurances": a(["2 000 000"], ["ok", "risque"], "10"),
 "pieces_candidature": a(["DC1", "Kbis"], ["eliminatoire"], "4"),
}),
"cas-04": ("""# Gymnase intercommunal — Lot 03 Charpente métallique
## RC
Art. 3 Visite : la visite est vivement conseillée mais n'est pas obligatoire.
Art. 4 Variantes : une variante est autorisée sur le traitement anticorrosion.
Art. 6 Les offres doivent parvenir avant le 19/03/2027 à 17h00.
Art. 7 Jugement : prix 45 %, valeur technique 45 %, gestion des déchets 10 %.
## CCAP
Art. 5 Avance : 20 % pour les PME, 5 % dans les autres cas.
Art. 6 Prix révisables, index BT07.
Art. 7 Retenue de garantie : 3 %.
Art. 9 Sous-traitance : la sous-traitance du lot est limitée à 30 % du montant.
Art. 11 Pénalités : 1/1000 du montant par jour, plafonnées à 5 %.
""", {
 "date_limite": a(["19/03/2027", "17"], ["ok"], "6"),
 "visite": a(["pas obligatoire|non obligatoire"], ["ok"], "3"),
 "criteres": a(["45", "10"], ["ok"], "7"),
 "penalites_retard": a(["1/1000", "5"], ["ok", "risque"], "11"),
 "retenue_garantie": a(["3"], ["ok"], "7"),
 "avance": a(["20", "5"], ["ok"], "5"),
 "revision_prix": a(["BT07"], ["ok"], "6"),
 "variantes": a(["anticorrosion"], ["ok"], "4"),
 "delai_execution": NT,
 "sous_traitance": a(["30"], ["ok", "risque"], "9"),
 "assurances": NT,
 "pieces_candidature": NT,
}),
"cas-05": ("""# Crèche de 60 berceaux — Lot 02 Gros œuvre
## RC
Art. 2 Visite obligatoire : une attestation de visite signée par le maître d'ouvrage est remise avec l'offre. Toute offre sans attestation est rejetée.
Art. 5 Remise : 09/04/2027 à 12h00.
Art. 6 Critères : valeur technique 55 %, prix 45 %.
Art. 7 Pièces : DC1, DC2, références de moins de 5 ans, attestation d'assurance.
## CCAP
Art. 3 Délai : 16 mois.
Art. 4 Prix : révisables selon l'index BT01.
Art. 8 Pénalités de retard : application des pénalités du CCAG Travaux.
Art. 9 Retenue de garantie : 5 %.
Art. 12 Assurances : responsabilité civile professionnelle de 5 000 000 euros et décennale.
""", {
 "date_limite": a(["09/04/2027", "12"], ["ok"], "5"),
 "visite": a(["obligatoire"], ["eliminatoire"], "2"),
 "criteres": a(["55", "45"], ["ok"], "6"),
 "penalites_retard": a(["CCAG"], ["ok", "a_verifier", "risque"], "8"),
 "retenue_garantie": a(["5"], ["ok"], "9"),
 "avance": NT,
 "revision_prix": a(["BT01"], ["ok"], "4"),
 "variantes": NT,
 "delai_execution": a(["16"], ["ok"], "3"),
 "sous_traitance": NT,
 "assurances": a(["5 000 000"], ["ok", "risque"], "12"),
 "pieces_candidature": a(["DC1", "DC2"], ["ok", "eliminatoire"], "7"),
}),
}

for nom, (dce, att) in CAS.items():
    d = ICI / nom; d.mkdir(exist_ok=True)
    (d / "dce.md").write_text(dce, encoding="utf-8", newline="\n")
    (d / "attendu.json").write_text(json.dumps(att, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print(len(CAS), "cas écrits")
