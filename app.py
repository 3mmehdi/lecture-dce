# Interface locale du skill lecture-dce : lire un dossier et voir d'où vient chaque valeur, puis rejouer le banc d'évaluation.
# Lancement : python app.py  puis  http://127.0.0.1:8790
# Bibliothèque standard seulement. Les appels au modèle et la notation sont ceux de evals/evaluer.py, sans copie.
import json, mimetypes, pathlib, re, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ICI = pathlib.Path(__file__).parent
EV = ICI / "evals"
sys.path.insert(0, str(EV))
import evaluer as ev  # noqa: E402  (SKILL, NAIF, CLES, appeler, noter)

HOTE, PORT = "127.0.0.1", 8790
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

def points_affiches(rep, dossier):
    return [{"cle": k, "nom": NOMS[k], "valeur": (rep.get(k) or {}).get("valeur", ""), "source": (rep.get(k) or {}).get("source", ""),
             "statut": (rep.get(k) or {}).get("statut", ""), "lignes": lignes_source((rep.get(k) or {}).get("source", ""), dossier)}
            for k in ev.CLES]

# ---------------------------------------------------------------- déroulés (flux d'étapes)
def derouler_lecture(texte, cas, mode, modele="sonnet"):
    """Génère les étapes d'une lecture. mode = direct (appel réel) ou rejouer (réponse déjà mesurée, instantané)."""
    dossier = decouper(texte)
    yield {"etape": "dossier", "dossier": dossier}
    yield {"etape": "consigne", "taille": len(ev.SKILL) + len(texte), "detail": "SKILL.md + references/points.md + le dossier"}
    if mode == "rejouer":
        r = resultats("v0.2")
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
    yield {"etape": "controle", **controler(rep)}
    yield {"etape": "points", "points": points_affiches(rep, dossier), "alertes": rep.get("alertes", [])}
    if cas:
        yield {"etape": "notation", **noter(rep, cas)}
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
            for v in ("v0.1", "v0.2"):
                r = resultats(v)
                if not r: continue
                lignes = []
                for cas, c in r["cas"].items():
                    n = noter(c["reponse"], cas)
                    lignes.append({"cas": cas, "duree_s": c["duree_s"], "cout_usd": c["cout_usd"], **n})
                tot = sum(l["points"] for l in lignes)
                out[v] = {"modele": r.get("modele"), "score": round(100 * tot / (36 * len(lignes)), 1),
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
        if self.path == "/api/banc":
            v = "v0.1" if d.get("version") == "v0.1" else "v0.2"
            return self._flux(derouler_banc(v, mode, d.get("modele") or "sonnet"))
        self.send_error(404)

if __name__ == "__main__":
    srv = ThreadingHTTPServer((HOTE, PORT), Gestion)
    print(f"lecture-dce : http://{HOTE}:{PORT}  (Ctrl+C pour arrêter)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
