# Évalue une version du skill lecture-dce sur tous les cas : python evaluer.py v0.1|v0.2 [modele]
# Chaque champ rapporte 3 points : valeur juste (mots attendus présents), statut juste, source citée.
# Un mot attendu peut avoir des variantes séparées par « | ».
# Une invention (valeur donnée là où le dossier ne dit rien) est comptée à part.
# Depuis la v0.3, les explications sont contrôlées à part, hors score : pourquoi et que_faire présents sur chaque point
# risque, éliminatoire ou à vérifier, question présente sur chaque point à vérifier, et chiffres absents du dossier listés.
import json, pathlib, re, subprocess, sys, time, tempfile, unicodedata
ICI = pathlib.Path(__file__).parent
SKILL = (ICI.parent / "SKILL.md").read_text(encoding="utf-8") + "\n\n" + (ICI.parent / "references" / "points.md").read_text(encoding="utf-8")
CLES = ["date_limite", "visite", "criteres", "penalites_retard", "retenue_garantie", "avance", "revision_prix",
        "variantes", "delai_execution", "sous_traitance", "assurances", "pieces_candidature"]

NAIF = ("Lis ce dossier de consultation et donne les points importants en JSON, avec ces 12 clés : " + ", ".join(CLES) +
        ". Chaque clé vaut un objet {valeur, source, statut}, statut parmi ok, risque, eliminatoire, a_verifier, non_trouve.")

def norm(s):
    s = unicodedata.normalize("NFKC", str(s)).lower().replace(" ", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", s)

def appeler(consigne, dce, modele):
    prompt = f"{consigne}\n\n---\nDOSSIER :\n{dce}\n---\nRéponds uniquement par l'objet JSON."
    with tempfile.TemporaryDirectory() as vide:
        t0 = time.time()
        r = subprocess.run(["claude", "-p", "--model", modele, "--output-format", "json", "--max-turns", "1"],
                           input=prompt, capture_output=True, text=True, encoding="utf-8", cwd=vide, timeout=300)
    meta = json.loads(r.stdout)
    texte = meta.get("result", "")
    m = re.search(r"\{.*\}", texte, re.S)
    return json.loads(m.group(0)), time.time() - t0, meta.get("total_cost_usd", 0)

def noter(rep, att):
    pts, inventions, details = 0, 0, {}
    for k in CLES:
        e, r = att[k], rep.get(k) or {}
        val, st, src = norm(r.get("valeur", "")), r.get("statut", ""), norm(r.get("source", ""))
        if e["statuts"] == ["non_trouve"]:
            ok = st == "non_trouve"
            p = 3 if ok else 0
            if not ok: inventions += 1
        else:
            p = int(all(any(norm(x) in val for x in m.split("|")) for m in e["mots"])) + int(st in e["statuts"]) + int(not e["source"] or norm(e["source"]) in src)
        pts += p; details[k] = p
    return pts, inventions, details

A_EXPLIQUER = {"risque", "eliminatoire", "a_verifier"}

def chiffres(texte):
    return re.findall(r"\d+(?:[ ,./]\d+)*", norm(texte))

def dans(chiffre, texte):
    return re.search(r"(?<![\d/.,])" + re.escape(chiffre) + r"(?![\d/])", texte) is not None

def controler_explications(rep, dce):
    """Hors score. Liste les explications manquantes et les chiffres qu'on ne retrouve pas dans le dossier
    (un calcul en produit : ils sont à relire, pas forcément faux)."""
    dossier = norm(dce)
    manquantes, questions, absents = [], [], []
    for k in CLES:
        r = rep.get(k) or {}
        if r.get("statut") not in A_EXPLIQUER: continue
        if not (r.get("pourquoi") and r.get("que_faire")): manquantes.append(k)
        if r.get("statut") == "a_verifier" and not r.get("question"): questions.append(k)
        for champ in ("pourquoi", "que_faire", "question"):
            absents += [{"cle": k, "champ": champ, "chiffre": c} for c in chiffres(r.get(champ, "")) if not dans(c, dossier)]
    for i, t in enumerate(rep.get("a_faire") or []):
        absents += [{"cle": "a_faire", "champ": str(i), "chiffre": c} for c in chiffres((t or {}).get("quoi", "")) + chiffres((t or {}).get("quand", "")) if not dans(c, dossier)]
    a_expliquer = sum((rep.get(k) or {}).get("statut") in A_EXPLIQUER for k in CLES)
    return {"a_expliquer": a_expliquer, "manquantes": manquantes, "questions_manquantes": questions,
            "chiffres_absents": absents, "a_faire": len(rep.get("a_faire") or [])}

if __name__ == "__main__":
    version = sys.argv[1]; modele = sys.argv[2] if len(sys.argv) > 2 else "sonnet"
    consigne = NAIF if version == "v0.1" else SKILL
    res = {"version": version, "modele": modele, "cas": {}}
    for d in sorted(p for p in ICI.iterdir() if p.is_dir() and p.name.startswith("cas-")):
        rep, duree, cout = appeler(consigne, (d / "dce.md").read_text(encoding="utf-8"),  modele)
        att = json.loads((d / "attendu.json").read_text(encoding="utf-8"))
        pts, inv, det = noter(rep, att)
        expl = controler_explications(rep, (d / "dce.md").read_text(encoding="utf-8"))
        res["cas"][d.name] = {"points": pts, "sur": 36, "inventions": inv, "duree_s": round(duree, 1), "cout_usd": cout, "detail": det,
                              "explications": expl, "reponse": rep}
        print(d.name, f"{pts}/36", "inventions:", inv, f"{duree:.0f}s",
              f"explications: {expl['a_expliquer'] - len(expl['manquantes'])}/{expl['a_expliquer']}", flush=True)
    tot = sum(c["points"] for c in res["cas"].values()); sur = 36 * len(res["cas"])
    res["score"] = round(100 * tot / sur, 1); res["inventions"] = sum(c["inventions"] for c in res["cas"].values())
    res["explications_manquantes"] = sum(len(c["explications"]["manquantes"]) for c in res["cas"].values())
    (ICI / f"resultats-{version}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("SCORE", version, res["score"], "% · inventions", res["inventions"])
