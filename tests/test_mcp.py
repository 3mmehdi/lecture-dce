# Tests du serveur MCP : les outils appelés directement, puis un échange réel en stdio avec le client du SDK.
# Lancement : python -m unittest discover -s tests  (ignorés si le paquet mcp n'est pas installé)
import asyncio, json, pathlib, sys, unittest

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
try:
    import mcp_server as s
except ImportError:
    s = None

OUTILS = {"lister_dossiers", "lire_dossier", "verifier_reponse", "noter_reponse"}


def reponse_v03(cas):
    return json.loads((RACINE / "evals" / "resultats-v0.3.json").read_text(encoding="utf-8"))["cas"][cas]["reponse"]


class Outils(unittest.TestCase):
    def setUp(self):
        if s is None: self.skipTest("paquet mcp absent (pip install mcp)")

    def test_notation_identique_au_banc(self):
        n = s.noter_reponse("cas-03", json.dumps(reponse_v03("cas-03"), ensure_ascii=False))
        self.assertEqual((n["points"], n["inventions"], n["statuts_faux"]), (36, 0, []))

    def test_cle_manquante_signalee(self):
        rep = reponse_v03("cas-03"); del rep["avance"]
        v = s.verifier_reponse("Voici la fiche : " + json.dumps(rep), s.lire_dossier("cas-03"))
        self.assertFalse(v["ok"]); self.assertEqual(v["manquantes"], ["avance"])

    def test_json_illisible(self):
        self.assertIn("erreur", s.verifier_reponse("{pas du json}", ""))

    def test_pas_de_sortie_du_dossier(self):
        for cas in ("../app.py", "cas-99", "cas-03/../../app.py"):
            with self.assertRaises(ValueError): s.lire_dossier(cas)


class Stdio(unittest.TestCase):
    def setUp(self):
        if s is None: self.skipTest("paquet mcp absent (pip install mcp)")

    def test_echange_reel(self):
        from mcp import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client

        async def echange():
            params = StdioServerParameters(command=sys.executable, args=[str(RACINE / "mcp_server.py")])
            async with stdio_client(params) as (lecture, ecriture):
                async with ClientSession(lecture, ecriture) as session:
                    await session.initialize()
                    noms = {t.name for t in (await session.list_tools()).tools}
                    res = await session.call_tool("lister_dossiers", {})
                    return noms, res

        noms, res = asyncio.run(asyncio.wait_for(echange(), 60))
        self.assertEqual(noms, OUTILS)
        self.assertFalse(getattr(res, "is_error", None) or getattr(res, "isError", False))  # is_error en 2.x, isError en 1.x
        texte = " ".join(getattr(c, "text", "") for c in res.content)
        self.assertIn("cas-01", texte); self.assertIn("cas-05", texte)


if __name__ == "__main__":
    unittest.main()
