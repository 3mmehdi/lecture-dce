# Tests du serveur MCP : les outils appelés directement, puis un échange réel en stdio avec le client du SDK.
# Lancement : python -m unittest discover -s tests  (ignorés si le paquet mcp n'est pas installé)
import asyncio, json, logging, pathlib, sys, unittest
for _n in ("httpx", "httpx2"): logging.getLogger(_n).setLevel(logging.WARNING)  # le client HTTP du SDK journalise chaque requête

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


class Http(unittest.TestCase):
    """Le même serveur en streamable HTTP, le transport d'un agent distant : un échange réel sur 127.0.0.1."""
    def setUp(self):
        if s is None: self.skipTest("paquet mcp absent (pip install mcp)")

    def test_echange_reel_http(self):
        import socket, subprocess, time
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client
        with socket.socket() as so:
            so.bind(("127.0.0.1", 0)); port = so.getsockname()[1]
        proc = subprocess.Popen([sys.executable, str(RACINE / "mcp_server.py"), "--http", str(port)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(100):  # attendre que le port réponde (10 s au plus)
                try:
                    socket.create_connection(("127.0.0.1", port), 0.2).close(); break
                except OSError:
                    time.sleep(0.1)

            async def echange():
                async with streamable_http_client(f"http://127.0.0.1:{port}/mcp") as flux:
                    async with ClientSession(flux[0], flux[1]) as session:
                        await session.initialize()
                        noms = {t.name for t in (await session.list_tools()).tools}
                        res = await session.call_tool("noter_reponse", {"cas": "cas-03", "reponse_json": json.dumps(reponse_v03("cas-03"))})
                        return noms, " ".join(getattr(c, "text", "") for c in res.content)

            noms, texte = asyncio.run(asyncio.wait_for(echange(), 60))
            self.assertEqual(noms, OUTILS)
            self.assertIn('"points": 36', texte)
        finally:
            proc.terminate(); proc.wait(10)


if __name__ == "__main__":
    unittest.main()
