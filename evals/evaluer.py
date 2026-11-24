# Évalue une version du skill lecture-dce sur tous les cas : python evaluer.py v0.1|v0.2 [modele]
# Chaque champ rapporte 3 points : valeur juste (mots attendus présents), statut juste, source citée.
# Un mot attendu peut avoir des variantes séparées par « | ».
# Une invention (valeur donnée là où le dossier ne dit rien) est comptée à part.
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

if __name__ == "__main__":
    version = sys.argv[1]; modele = sys.argv[2] if len(sys.argv) > 2 else "sonnet"
    consigne = NAIF if version == "v0.1" else SKILL
    res = {"version": version, "modele": modele, "cas": {}}
    for d in sorted(p for p in ICI.iterdir() if p.is_dir() and p.name.startswith("cas-")):
        rep, duree, cout = appeler(consigne, (d / "dce.md").read_text(encoding="utf-8"),  modele)
        att = json.loads((d / "attendu.json").read_text(encoding="utf-8"))
        pts, inv, det = noter(rep, att)
        res["cas"][d.name] = {"points": pts, "sur": 36, "inventions": inv, "duree_s": round(duree, 1), "cout_usd": cout, "detail": det, "reponse": rep}
        print(d.name, f"{pts}/36", "inventions:", inv, f"{duree:.0f}s", flush=True)
    tot = sum(c["points"] for c in res["cas"].values()); sur = 36 * len(res["cas"])
    res["score"] = round(100 * tot / sur, 1); res["inventions"] = sum(c["inventions"] for c in res["cas"].values())
    (ICI / f"resultats-{version}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("SCORE", version, res["score"], "% · inventions", res["inventions"])
