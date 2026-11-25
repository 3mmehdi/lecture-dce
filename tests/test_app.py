# Tests de l'interface locale : découpage du dossier, liens vers les sources, contrôle, et les routes en mode Rejouer.
# Lancement : python -m unittest discover -s tests
import json, pathlib, sys, threading, unittest, urllib.request
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import app

DOSSIER = """# Extension d'un centre technique
## RC
Art. 2.1 Date limite : 05/03/2027.
## CCAP
Art. 2.2 Délai : 12 mois.
## Acte d'engagement
Art. 3 Délai : 14 mois.
"""

class Regles(unittest.TestCase):
    def test_les_douze_regles_de_statut(self):
        self.assertEqual(set(app.REGLES), set(app.ev.CLES))
        self.assertIn("1/1000", app.REGLES["penalites_retard"]["regle"])
        self.assertEqual(app.REGLES["visite"]["piece"], "RC")

    def test_regle_jointe_a_chaque_point(self):
        points = app.points_affiches({}, app.decouper(DOSSIER))
        self.assertTrue(all(p["regle"] and p["piece_habituelle"] for p in points))

class Decoupage(unittest.TestCase):
    def test_pieces_et_articles(self):
        d = app.decouper(DOSSIER)
        self.assertEqual(d["titre"], "Extension d'un centre technique")
        arts = [(l["piece"], l["art"]) for l in d["lignes"] if l["type"] == "article"]
        self.assertEqual(arts, [("RC", "2.1"), ("CCAP", "2.2"), ("AE", "3")])

    def test_abreviation_entre_parentheses(self):
        self.assertEqual(app.abreviation("Règlement de la consultation (RC)"), "RC")
        self.assertEqual(app.abreviation("Acte d'engagement"), "AE")

class Sources(unittest.TestCase):
    def setUp(self): self.d = app.decouper(DOSSIER)
    def ligne(self, piece, art): return [l["id"] for l in self.d["lignes"] if l.get("piece") == piece and l.get("art") == art][0]

    def test_contradiction_deux_lignes(self):
        self.assertEqual(app.lignes_source("CCAP art. 2.2 / AE art. 3", self.d), [self.ligne("CCAP", "2.2"), self.ligne("AE", "3")])

    def test_meme_numero_autre_piece_pas_confondu(self):
        self.assertEqual(app.lignes_source("RC art. 2.2", self.d), [])

    def test_source_vide(self):
        self.assertEqual(app.lignes_source("", self.d), [])

class Controle(unittest.TestCase):
    def test_cle_manquante_et_statut_inconnu(self):
        rep = {k: {"valeur": "x", "source": "RC art. 1", "statut": "ok"} for k in app.ev.CLES}
        del rep["avance"]; rep["visite"]["statut"] = "peut-être"
        c = app.controler(rep)
        self.assertFalse(c["ok"]); self.assertEqual(c["manquantes"], ["avance"]); self.assertEqual(c["statuts_inconnus"], ["visite"])

    def test_notation_identique_au_banc(self):
        r = app.resultats(app.VERSION_SKILL)
        for cas, c in r["cas"].items():
            self.assertEqual(app.noter(c["reponse"], cas)["points"], app.ev.noter(c["reponse"], app.attendu(cas))[0])

class Explications(unittest.TestCase):
    DCE = "## CCAP\nArt. 8 Pénalités : 500 euros par jour.\n"
    def test_risque_sans_explication_signale(self):
        rep = {k: {"valeur": "x", "source": "CCAP art. 8", "statut": "ok"} for k in app.ev.CLES}
        rep["penalites_retard"]["statut"] = "risque"
        self.assertEqual(app.ev.controler_explications(rep, self.DCE)["manquantes"], ["penalites_retard"])

    def test_contradiction_sans_question_signalee(self):
        rep = {k: {"valeur": "x", "source": "", "statut": "ok"} for k in app.ev.CLES}
        rep["delai_execution"] = {"valeur": "12 / 14", "source": "", "statut": "a_verifier", "pourquoi": "p", "que_faire": "q"}
        self.assertEqual(app.ev.controler_explications(rep, self.DCE)["questions_manquantes"], ["delai_execution"])

    def test_chiffre_absent_du_dossier(self):
        rep = {k: {"valeur": "x", "source": "", "statut": "ok"} for k in app.ev.CLES}
        rep["penalites_retard"] = {"valeur": "500", "source": "", "statut": "risque",
                                   "pourquoi": "500 euros par jour, 30 jours = 15 000 euros", "que_faire": "provisionner"}
        absents = [a["chiffre"] for a in app.ev.controler_explications(rep, self.DCE)["chiffres_absents"]]
        self.assertEqual(absents, ["30", "15 000"])

    def test_v03_tous_les_risques_expliques(self):
        for cas, c in app.resultats("v0.3")["cas"].items():
            self.assertEqual(c["explications"]["manquantes"], [], cas)
            self.assertEqual(c["explications"]["questions_manquantes"], [], cas)

class Discussion(unittest.TestCase):
    def test_traduction_du_flux_claude_code(self):
        vus, sortie = set(), []
        for e in [
            {"type": "system", "subtype": "hook_started"},
            {"type": "system", "subtype": "init", "model": "m", "skills": ["autre", "lecture-dce"]},
            {"type": "assistant", "message": {"content": [{"type": "thinking", "thinking": ""}]}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "lecture-dce"}}]}},
            {"type": "user", "message": {"content": [{"type": "text", "text": "Base directory for this skill: " + app.MAISON + "\\.claude\\skills\\lecture-dce"}]}},
            {"type": "result", "duration_ms": 36376, "total_cost_usd": 0.23, "num_turns": 4, "is_error": False},
        ]:
            sortie += list(app.traduire(e, vus))
        self.assertEqual([x["etape"] for x in sortie], ["session", "reflechit", "outil", "charge", "resultat"])
        self.assertTrue(sortie[0]["present"])
        self.assertNotIn(app.MAISON, sortie[3]["debut"])  # aucun chemin personnel à l'écran

    def test_traduction_des_outils_mcp(self):
        note = json.dumps({"points": 36, "sur": 36, "inventions": 0, "detail": {}, "statuts_faux": []})
        controle = json.dumps({"manquantes": [], "statuts_inconnus": [], "sans_source": [], "ok": True,
                               "explications": {"a_expliquer": 5, "manquantes": [], "chiffres_absents": [{"cle": "penalites_retard", "chiffre": "1/1000"}]}})
        vus, sortie = set(), []
        for e in [
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "mcp__lecture-dce__noter_reponse",
                                                           "input": {"cas": "cas-03", "reponse_json": "x" * 5000}}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "content": [{"type": "text", "text": controle}]}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "content": note}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "content": "# Un dossier, " + "texte " * 20}]}},
        ]:
            sortie += list(app.traduire(e, vus))
        self.assertEqual([x["etape"] for x in sortie], ["outil", "mcp_controle", "mcp_note", "lu"])
        self.assertEqual(sortie[0]["detail"], "cas=cas-03, reponse_json=<5 000 caractères>")  # pas 5 000 caractères à l'écran
        self.assertEqual((sortie[1]["expliques"], sortie[1]["absents"], sortie[2]["points"]), (5, ["1/1000"], 36))

class Routes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = app.Serveur(("127.0.0.1", 0), app.Gestion)
        cls.url = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
    @classmethod
    def tearDownClass(cls): cls.srv.shutdown()

    def post(self, chemin, corps):
        req = urllib.request.Request(self.url + chemin, json.dumps(corps).encode(), {"Content-Type": "application/json"})
        brut = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
        return [json.loads(b[6:]) for b in brut.split("\n\n") if b.startswith("data: ")]

    def test_page_et_cas(self):
        self.assertIn(b"Lecture de DCE", urllib.request.urlopen(self.url + "/").read())
        self.assertEqual(len(json.loads(urllib.request.urlopen(self.url + "/api/cas").read())), 5)

    def test_lecture_rejouee(self):
        texte = (app.EV / "cas-03" / "dce.md").read_text(encoding="utf-8")
        ev = self.post("/api/lire", {"texte": texte, "cas": "cas-03", "mode": "rejouer"})
        etapes = [e["etape"] for e in ev]
        self.assertEqual(etapes, ["dossier", "consigne", "appel", "reponse", "controle", "points", "notation", "fin"])
        points = next(e for e in ev if e["etape"] == "points")["points"]
        delai = next(p for p in points if p["cle"] == "delai_execution")
        self.assertEqual(delai["statut"], "a_verifier"); self.assertEqual(len(delai["lignes"]), 2)
        self.assertTrue(delai["pourquoi"] and delai["que_faire"] and delai["question"])
        a_faire = next(e for e in ev if e["etape"] == "points")["a_faire"]
        self.assertTrue(a_faire and all("quand" in t and "lignes" in t for t in a_faire))

    def test_discussion_rejouee(self):
        if not (app.DISCUSSIONS / "cas-03.json").exists(): self.skipTest("aucune conversation enregistrée")
        texte = (app.EV / "cas-03" / "dce.md").read_text(encoding="utf-8")
        ev = self.post("/api/discussion", {"texte": texte, "cas": "cas-03", "mode": "rejouer"})
        etapes = [e["etape"] for e in ev]
        self.assertEqual(etapes[:2], ["dossier", "demande"])
        self.assertIn("charge", etapes); self.assertEqual(etapes[-1], "fin")
        self.assertEqual(next(e for e in ev if e["etape"] == "notation")["inventions"], 0)

    def test_les_cinq_conversations_rejouees(self):
        # « Lire un dossier » passe par Claude Code : le mode Rejouer doit couvrir les cinq dossiers de test
        for c in sorted(p.name for p in app.EV.iterdir() if p.name.startswith("cas-")):
            with self.subTest(cas=c):
                texte = (app.EV / c / "dce.md").read_text(encoding="utf-8")
                ev = self.post("/api/discussion", {"texte": texte, "cas": c, "mode": "rejouer"})
                self.assertEqual(next(e for e in ev if e["etape"] == "notation")["inventions"], 0)

    def test_mcp_demande_un_dossier_de_test(self):
        ev = self.post("/api/discussion", {"texte": DOSSIER, "mode": "rejouer", "mcp": True})
        self.assertEqual(ev[-1]["etape"], "erreur")

    def test_discussion_mcp_rejouee(self):
        if not (app.DISCUSSIONS / "cas-03-mcp.json").exists(): self.skipTest("aucune conversation MCP enregistrée")
        texte = (app.EV / "cas-03" / "dce.md").read_text(encoding="utf-8")
        ev = self.post("/api/discussion", {"texte": texte, "cas": "cas-03", "mode": "rejouer", "mcp": True})
        etapes = [e["etape"] for e in ev]
        self.assertIn("mcp_note", etapes)
        self.assertTrue(any(e["etape"] == "outil" and e["nom"].endswith("noter_reponse") for e in ev))
        self.assertEqual(next(e for e in ev if e["etape"] == "notation")["inventions"], 0)

    def test_rejouer_dossier_colle_refuse(self):
        ev = self.post("/api/lire", {"texte": DOSSIER, "mode": "rejouer"})
        self.assertEqual(ev[-1]["etape"], "erreur")

    def test_banc_rejoue(self):
        ev = self.post("/api/banc", {"version": "v0.1", "mode": "rejouer"})
        self.assertEqual(ev[-1], {"etape": "fin", "score": 95.0, "inventions": 0})

    def test_deuxieme_serveur_refuse_sous_windows(self):
        if sys.platform != "win32": self.skipTest("Windows seulement")
        with self.assertRaises(OSError):
            app.Serveur(("127.0.0.1", self.srv.server_address[1]), app.Gestion)

    def test_pas_de_sortie_du_dossier(self):
        with self.assertRaises(urllib.error.HTTPError):
            urllib.request.urlopen(self.url + "/../app.py")

if __name__ == "__main__":
    unittest.main()
