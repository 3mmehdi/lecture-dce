# Interface locale du skill lecture-dce : lire un dossier et voir d'où vient chaque valeur, puis rejouer le banc d'évaluation.
# Lancement : python app.py  puis  http://127.0.0.1:8790
# Bibliothèque standard seulement. Les appels au modèle et la notation sont ceux de evals/evaluer.py, sans copie.
import json, mimetypes, pathlib, re, subprocess, sys, tempfile, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ICI = pathlib.Path(__file__).parent
EV = ICI / "evals"
sys.path.insert(0, str(EV))
import evaluer as ev  # noqa: E402  (SKILL, NAIF, CLES, appeler, noter)

HOTE, PORT = "127.0.0.1", 8790
VERSION_SKILL = "v0.3"  # la version rejouée et comparée à la consigne simple
DISCUSSIONS = EV / "discussions"  # conversations Claude Code enregistrées, pour le mode Rejouer
QUESTION = "Analyse ce DCE : qu'est-ce que je dois retenir avant de répondre ?"
# Avec le serveur MCP : Claude lit le dossier par l'outil, puis se contrôle et se note avant de rendre sa réponse
QUESTION_MCP = ("Analyse le DCE {cas} : récupère son texte avec l'outil lire_dossier. Avant de me rendre ta réponse, "
                "contrôle-la avec verifier_reponse puis note-la avec noter_reponse, corrige si besoin, et rends le JSON final.")
OUTILS_MCP = ["mcp__lecture-dce__" + n for n in ("lister_dossiers", "lire_dossier", "verifier_reponse", "noter_reponse")]
STATUTS = {"ok", "risque", "eliminatoire", "a_verifier", "non_trouve"}
NOMS = {"date_limite": "Date limite", "visite": "Visite de site", "criteres": "Critères", "penalites_retard": "Pénalités de retard",
        "retenue_garantie": "Retenue de garantie", "avance": "Avance", "revision_prix": "Révision des prix", "variantes": "Variantes",
        "delai_execution": "Délai d'exécution", "sous_traitance": "Sous-traitance", "assurances": "Assurances",
        "pieces_candidature": "Pièces de candidature"}

# ---------------------------------------------------------------- dossiers
def abreviation(titre):
    """« ## Règlement de la consultation (RC) » -> RC ; « ## Acte d'engagement » -> AE."""
    m = re.search(r"\(([A-Z]{2,5})\)", titre)
    if m: return m.group(1)
    t = titre.strip().lower()
    if t.startswith("acte d"): return "AE"
    if t.startswith("règlement") or t.startswith("reglement"): return "RC"
    if "clauses administratives" in t: return "CCAP"
    return titre.strip().split()[0].upper() if titre.strip() else ""

def decouper(texte):
    """Le dossier en lignes repérées : pièce, numéro d'article, texte."""
    lignes, piece, titre = [], "", ""
    for i, brut in enumerate(texte.splitlines()):
        l = brut.rstrip()
        if l.startswith("# "): titre = l[2:].strip(); lignes.append({"id": i, "type": "titre", "texte": titre}); continue
        if l.startswith("## "): piece = abreviation(l[3:]); lignes.append({"id": i, "type": "piece", "texte": l[3:].strip(), "piece": piece}); continue
        if not l.strip(): continue
        m = re.match(r"\s*Art\.?\s*([0-9]+(?:\.[0-9]+)*)", l, re.I)
        lignes.append({"id": i, "type": "article" if m else "texte", "texte": l.strip(), "piece": piece, "art": m.group(1) if m else ""})
    return {"titre": titre, "lignes": lignes}

def lignes_source(source, dossier):
    """« CCAP art. 2.2 / AE art. 3 » -> les id des lignes citées. Une source introuvable ne renvoie rien, sans deviner."""
    ids = []
    for part in re.split(r"[/;,]| et ", source or ""):
        m = re.search(r"([A-Za-z]{2,5})\s*,?\s*art(?:icle)?\.?\s*([0-9]+(?:\.[0-9]+)*)", part, re.I)
        if not m: continue
        piece, art = m.group(1).upper(), m.group(2)
        ids += [l["id"] for l in dossier["lignes"] if l.get("art") == art and l.get("piece", "").upper() == piece]
    return ids

def cas_disponibles():
    out = []
    for d in sorted(p for p in EV.iterdir() if p.is_dir() and p.name.startswith("cas-")):
        texte = (d / "dce.md").read_text(encoding="utf-8")
        out.append({"id": d.name, "titre": decouper(texte)["titre"], "texte": texte})
    return out

def regles():
    """references/points.md -> {clé: {piece, regle}} : la règle de statut que le skill applique, montrée à côté du point."""
    out = {}
    for l in (ICI / "references" / "points.md").read_text(encoding="utf-8").splitlines():
        c = [x.strip() for x in l.strip().strip("|").split("|")]
        if len(c) == 4 and c[0] in ev.CLES: out[c[0]] = {"piece": c[2], "regle": c[3].replace("`", "")}
    return out

REGLES = regles()

def attendu(cas): return json.loads((EV / cas / "attendu.json").read_text(encoding="utf-8"))

def resultats(version):
    p = EV / f"resultats-{version}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

# ---------------------------------------------------------------- contrôle et notation
def controler(rep):
    """Ce que l'on vérifie avant de montrer la réponse : les 12 clés, des statuts connus, une source quand une valeur est donnée."""
    manquantes = [k for k in ev.CLES if k not in rep]
    statuts_inconnus = [k for k in ev.CLES if k in rep and (rep[k] or {}).get("statut") not in STATUTS]
    sans_source = [k for k in ev.CLES if k in rep and (rep[k] or {}).get("statut") not in ("non_trouve", None) and not (rep[k] or {}).get("source")]
    return {"manquantes": manquantes, "statuts_inconnus": statuts_inconnus, "sans_source": sans_source,
            "ok": not (manquantes or statuts_inconnus)}

def statuts_faux(rep, att):
    return [{"cle": k, "nom": NOMS[k], "rendu": (rep.get(k) or {}).get("statut", ""), "attendu": att[k]["statuts"]}
            for k in ev.CLES if (rep.get(k) or {}).get("statut") not in att[k]["statuts"]]

def noter(rep, cas):
    att = attendu(cas)
    pts, inv, det = ev.noter(rep, att)
    return {"points": pts, "sur": 36, "inventions": inv, "detail": det, "statuts_faux": statuts_faux(rep, att)}

def points_affiches(rep, dossier, absents=()):
    out = []
    for k in ev.CLES:
        r = rep.get(k) or {}
        out.append({"cle": k, "nom": NOMS[k], "valeur": r.get("valeur", ""), "source": r.get("source", ""), "statut": r.get("statut", ""),
                    "lignes": lignes_source(r.get("source", ""), dossier),
                    "pourquoi": r.get("pourquoi", ""), "que_faire": r.get("que_faire", ""), "question": r.get("question", ""),
                    "a_relire": sorted({a["chiffre"] for a in absents if a["cle"] == k}),
                    "regle": REGLES.get(k, {}).get("regle", ""), "piece_habituelle": REGLES.get(k, {}).get("piece", "")})
    return out

def a_faire_affiche(rep, dossier):
    return [{"quand": (t or {}).get("quand", ""), "quoi": (t or {}).get("quoi", ""), "source": (t or {}).get("source", ""),
             "lignes": lignes_source((t or {}).get("source", ""), dossier)} for t in (rep.get("a_faire") or []) if isinstance(t, dict)]

# ---------------------------------------------------------------- déroulés (flux d'étapes)
def derouler_lecture(texte, cas, mode, modele="sonnet"):
    """Génère les étapes d'une lecture. mode = direct (appel réel) ou rejouer (réponse déjà mesurée, instantané)."""
    dossier = decouper(texte)
    yield {"etape": "dossier", "dossier": dossier}
    yield {"etape": "consigne", "taille": len(ev.SKILL) + len(texte), "detail": "SKILL.md + references/points.md + le dossier"}
    if mode == "rejouer":
        r = resultats(VERSION_SKILL)
        if not cas or not r or cas not in r["cas"]:
            yield {"etape": "erreur", "message": "Le mode Rejouer ne couvre que les 5 dossiers de test. Passe en direct pour un dossier collé."}
            return
        c = r["cas"][cas]
        yield {"etape": "appel", "statut": "rejoue", "modele": r.get("modele", "sonnet")}
        rep, duree, cout = c["reponse"], c["duree_s"], c["cout_usd"]
    else:
        yield {"etape": "appel", "statut": "en_cours", "modele": modele}
        try:
            rep, duree, cout = ev.appeler(ev.SKILL, texte, modele)
        except Exception as e:  # CLI absente, délai dépassé, JSON illisible : on le dit, on n'invente pas de réponse
            yield {"etape": "erreur", "message": f"L'appel au modèle a échoué : {type(e).__name__}. Vérifie que « claude --version » répond, ou passe en mode Rejouer."}
            return
    yield {"etape": "reponse", "duree_s": round(duree, 1), "cout_usd": cout, "brut": rep}
    yield from apres_reponse(rep, texte, dossier, cas)
    yield {"etape": "fin"}

def apres_reponse(rep, texte, dossier, cas):
    """Les mêmes contrôles et la même notation, que la réponse vienne du banc ou d'une conversation Claude Code."""
    expl = ev.controler_explications(rep, texte)
    yield {"etape": "controle", **controler(rep), "explications": expl}
    yield {"etape": "points", "points": points_affiches(rep, dossier, expl["chiffres_absents"]), "alertes": rep.get("alertes", []),
           "a_faire": a_faire_affiche(rep, dossier)}
    if cas:
        yield {"etape": "notation", **noter(rep, cas)}

# ---------------------------------------------------------------- conversation Claude Code (le skill installé, déclenché par sa description)
MAISON = str(pathlib.Path.home())

def anonyme(s):
    return str(s).replace(MAISON, "~").replace(MAISON.replace("\\", "/"), "~")

def retour_mcp(texte):
    """Le retour de verifier_reponse ou de noter_reponse, résumé ; None pour tout autre retour d'outil."""
    try:
        d = json.loads(texte)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(d, dict): return None
    if "points" in d and "sur" in d:
        return {"etape": "mcp_note", "points": d["points"], "sur": d["sur"], "inventions": d.get("inventions", 0),
                "statuts_faux": len(d.get("statuts_faux") or [])}
    if "manquantes" in d and "ok" in d:
        x = d.get("explications") or {}
        return {"etape": "mcp_controle", "ok": d["ok"], "manquantes": len(d["manquantes"]),
                "expliques": (x.get("a_expliquer", 0) - len(x.get("manquantes") or [])), "a_expliquer": x.get("a_expliquer", 0),
                "absents": sorted({a.get("chiffre", "") for a in x.get("chiffres_absents") or [] if isinstance(a, dict)})}
    return None

def traduire(e, vus):
    """Un événement stream-json de « claude -p » -> zéro ou plusieurs étapes lisibles. On ne garde que ce qui explique le déroulé."""
    t = e.get("type")
    if t == "system" and e.get("subtype") == "init":
        skills = e.get("skills") or []
        yield {"etape": "session", "modele": e.get("model", ""), "skills": len(skills), "present": "lecture-dce" in skills}
    elif t == "assistant":
        for c in e.get("message", {}).get("content", []):
            k = c.get("type")
            if k == "thinking" and "reflechit" not in vus:
                vus.add("reflechit"); yield {"etape": "reflechit"}
            elif k == "tool_use":
                vus.discard("reflechit")
                entree = c.get("input") or {}
                if c.get("name", "").startswith("mcp__"):
                    detail = ", ".join(f"{k}={v}" if len(str(v)) < 40 else f"{k}=<{len(str(v)):,} caractères>".replace(",", " ")
                                       for k, v in entree.items())
                else:
                    detail = entree.get("skill") or entree.get("query") or anonyme(entree.get("file_path") or json.dumps(entree, ensure_ascii=False))
                yield {"etape": "outil", "nom": c.get("name", ""), "detail": detail}
            elif k == "text" and c.get("text", "").strip():
                vus.discard("reflechit"); yield {"etape": "texte", "texte": c["text"]}
    elif t == "user":
        for c in e.get("message", {}).get("content", []):
            if not isinstance(c, dict): continue
            if c.get("type") == "text" and c.get("text", "").startswith("Base directory for this skill"):
                yield {"etape": "charge", "quoi": "SKILL.md", "caracteres": len(c["text"]), "debut": anonyme(c["text"][:600])}
            elif c.get("type") == "tool_result":
                contenu = c.get("content")
                texte = contenu if isinstance(contenu, str) else "".join(x.get("text", "") for x in contenu or [] if isinstance(x, dict))
                retour = retour_mcp(texte)
                if retour: yield retour
                elif len(texte) > 40: yield {"etape": "lu", "caracteres": len(texte)}
    elif t == "result":
        yield {"etape": "resultat", "duree_s": round((e.get("duration_ms") or 0) / 1000, 1), "cout_usd": e.get("total_cost_usd", 0),
               "tours": e.get("num_turns", 0), "erreur": bool(e.get("is_error"))}

def derouler_discussion(texte, question, cas, mode, modele="sonnet", avec_mcp=False):
    dossier = decouper(texte)
    yield {"etape": "dossier", "dossier": dossier}
    if avec_mcp:
        if not cas:
            yield {"etape": "erreur", "message": "Avec le serveur MCP, choisis un dossier de test : la notation a besoin de sa réponse attendue."}
            return
        question = QUESTION_MCP.format(cas=cas)
    yield {"etape": "demande", "question": question, "lignes": len(texte.splitlines()), "mcp": avec_mcp}
    etapes = []
    nom = f"{cas}-mcp.json" if avec_mcp else f"{cas}.json"
    if mode == "rejouer":
        f = DISCUSSIONS / nom
        if not cas or not f.exists():
            yield {"etape": "erreur", "message": "Aucune conversation enregistrée pour ce dossier. Passe en direct : chaque conversation en direct sur un dossier de test est enregistrée."}
            return
        for x in json.loads(f.read_text(encoding="utf-8")):
            time.sleep(0.5 if x["etape"] in ("outil", "charge", "lu", "texte", "mcp_controle", "mcp_note") else 0.15)  # assez pour suivre à l'œil
            etapes.append(x); yield {**x, "rejoue": True}
    else:
        vus = set()
        with tempfile.TemporaryDirectory() as vide:  # dossier vide : aucune consigne de projet ne s'ajoute au skill
            cmd = ["claude", "-p", "--model", modele, "--output-format", "stream-json", "--verbose"]
            if avec_mcp:  # le serveur du dépôt, et lui seul ; pas de shell ni d'écriture de fichiers
                conf = pathlib.Path(vide) / "mcp.json"
                conf.write_text(json.dumps({"mcpServers": {"lecture-dce": {"command": sys.executable, "args": [str(ICI / "mcp_server.py")]}}}), encoding="utf-8")
                # --tools fixe la liste des outils intégrés : --disallowedTools a laissé passer une tentative d'écriture le 26/11
                cmd += ["--mcp-config", str(conf), "--strict-mcp-config", "--tools", "Skill,Read,ToolSearch",
                        "--allowedTools", " ".join(["Skill", "Read"] + OUTILS_MCP)]
            else:
                cmd += ["--allowedTools", "Skill Read"]
            try:
                proc = subprocess.Popen(cmd, cwd=vide, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
            except OSError as e:
                yield {"etape": "erreur", "message": f"Claude Code introuvable ({type(e).__name__}). Vérifie que « claude --version » répond."}; return
            proc.stdin.write(question if avec_mcp else f"{question}\n\n{texte}"); proc.stdin.close()
            for ligne in proc.stdout:
                try: e = json.loads(ligne)
                except json.JSONDecodeError: continue
                for x in traduire(e, vus):
                    etapes.append(x); yield x
            proc.wait(timeout=60)
        if cas and any(x["etape"] == "resultat" and not x["erreur"] for x in etapes):
            DISCUSSIONS.mkdir(exist_ok=True)
            (DISCUSSIONS / nom).write_text(json.dumps(etapes, ensure_ascii=False, indent=1), encoding="utf-8")
    final = next((x["texte"] for x in reversed(etapes) if x["etape"] == "texte"), "")
    m = re.search(r"\{.*\}", final, re.S)
    try:
        rep = json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        rep = None
    if rep is None:
        yield {"etape": "erreur", "message": "La réponse ne contient pas d'objet JSON lisible : elle reste affichée telle quelle, sans fiche."}
        return
    yield from apres_reponse(rep, texte, dossier, cas)
    yield {"etape": "fin"}

def derouler_banc(version, mode, modele="sonnet"):
    consigne = ev.NAIF if version == "v0.1" else ev.SKILL
    saved = resultats(version)
    total = inv_tot = 0
    cas_l = cas_disponibles()
    yield {"etape": "debut", "version": version, "n": len(cas_l)}
    for c in cas_l:
        if mode == "rejouer":
            if not saved or c["id"] not in saved["cas"]:
                yield {"etape": "erreur", "message": f"Aucun résultat enregistré pour {version}."}; return
            s = saved["cas"][c["id"]]; rep, duree, cout = s["reponse"], s["duree_s"], s["cout_usd"]
            time.sleep(0.25)  # assez pour suivre à l'œil, sans faire croire à un vrai appel
        else:
            yield {"etape": "cas_debut", "cas": c["id"]}
            try:
                rep, duree, cout = ev.appeler(consigne, c["texte"], modele)
            except Exception as e:
                yield {"etape": "erreur", "message": f"{c['id']} : l'appel au modèle a échoué ({type(e).__name__})."}; return
        n = noter(rep, c["id"])
        total += n["points"]; inv_tot += n["inventions"]
        yield {"etape": "cas", "cas": c["id"], "titre": c["titre"], "duree_s": round(duree, 1), "cout_usd": cout, **n}
    yield {"etape": "fin", "score": round(100 * total / (36 * len(cas_l)), 1), "inventions": inv_tot}

# ---------------------------------------------------------------- serveur
class Gestion(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def _flux(self, gen):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8"); self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        try:
            for ev_ in gen:
                self.wfile.write(f"data: {json.dumps(ev_, ensure_ascii=False)}\n\n".encode("utf-8")); self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _fichier(self, chemin):
        base = (ICI / "ui").resolve() if not chemin.startswith("fonts/") else ICI.resolve()
        cible = (base / chemin).resolve()
        if base not in cible.parents and cible != base or not cible.is_file():
            self.send_error(404); return
        b = cible.read_bytes()
        self.send_response(200); self.send_header("Content-Type", mimetypes.guess_type(cible.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/": return self._fichier("index.html")
        if p == "/api/cas": return self._json(cas_disponibles())
        if p == "/api/comparaison":
            out = {}
            for v in ("v0.1", VERSION_SKILL):
                r = resultats(v)
                if not r: continue
                lignes = []
                for cas, c in r["cas"].items():
                    n = noter(c["reponse"], cas)
                    lignes.append({"cas": cas, "duree_s": c["duree_s"], "cout_usd": c["cout_usd"], **n})
                tot = sum(l["points"] for l in lignes)
                out["v0.1" if v == "v0.1" else "skill"] = {"version": v, "modele": r.get("modele"), "score": round(100 * tot / (36 * len(lignes)), 1),
                          "inventions": sum(l["inventions"] for l in lignes),
                          "statuts_faux": sum(len(l["statuts_faux"]) for l in lignes), "cas": lignes}
            return self._json(out)
        if p.startswith("/fonts/"): return self._fichier(p[1:])
        return self._fichier(p.lstrip("/"))

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            d = json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            return self._json({"message": "Requête illisible."}, 400)
        mode = "rejouer" if d.get("mode") == "rejouer" else "direct"
        if self.path == "/api/lire":
            texte = (d.get("texte") or "").strip()
            if not texte: return self._json({"message": "Le dossier est vide. Choisis un dossier ou colle son texte."}, 400)
            return self._flux(derouler_lecture(texte, d.get("cas"), mode, d.get("modele") or "sonnet"))
        if self.path == "/api/discussion":
            texte = (d.get("texte") or "").strip()
            if not texte: return self._json({"message": "Le dossier est vide. Choisis un dossier ou colle son texte."}, 400)
            question = (d.get("question") or "").strip() or QUESTION
            return self._flux(derouler_discussion(texte, question, d.get("cas"), mode, d.get("modele") or "sonnet", bool(d.get("mcp"))))
        if self.path == "/api/banc":
            v = "v0.1" if d.get("version") == "v0.1" else VERSION_SKILL
            return self._flux(derouler_banc(v, mode, d.get("modele") or "sonnet"))
        self.send_error(404)

class Serveur(ThreadingHTTPServer):
    # Sous Windows, SO_REUSEADDR laisse un deuxième serveur s'ouvrir sur le même port : l'ancien continuerait de répondre
    allow_reuse_address = sys.platform != "win32"

if __name__ == "__main__":
    try:
        srv = Serveur((HOTE, PORT), Gestion)
    except OSError:
        sys.exit(f"Le port {PORT} est déjà pris : une interface tourne sans doute déjà. Ferme l'autre terminal, ou ouvre http://{HOTE}:{PORT}")
    print(f"lecture-dce : http://{HOTE}:{PORT}  (Ctrl+C pour arrêter)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
