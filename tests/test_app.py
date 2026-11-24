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
        r = app.resultats("v0.2")
        for cas, c in r["cas"].items():
            self.assertEqual(app.noter(c["reponse"], cas)["points"], app.ev.noter(c["reponse"], app.attendu(cas))[0])

class Routes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Gestion)
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

    def test_rejouer_dossier_colle_refuse(self):
        ev = self.post("/api/lire", {"texte": DOSSIER, "mode": "rejouer"})
        self.assertEqual(ev[-1]["etape"], "erreur")

    def test_banc_rejoue(self):
        ev = self.post("/api/banc", {"version": "v0.1", "mode": "rejouer"})
        self.assertEqual(ev[-1], {"etape": "fin", "score": 95.0, "inventions": 0})

    def test_pas_de_sortie_du_dossier(self):
        with self.assertRaises(urllib.error.HTTPError):
            urllib.request.urlopen(self.url + "/../app.py")

if __name__ == "__main__":
    unittest.main()
