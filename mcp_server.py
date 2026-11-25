# Serveur MCP du skill lecture-dce : les dossiers de test, le contrôle du format et la notation du banc, en 4 outils.
# Lancement : python mcp_server.py  (transport stdio ; .mcp.json l'enregistre pour Claude Code dans ce dossier).
#             python mcp_server.py --http [port]  (streamable HTTP sur 127.0.0.1, port 8791 par défaut, adresse /mcp :
#             le transport d'un agent distant comme Copilot Studio. Sans authentification : à ne jamais exposer tel quel.)
# Aucun appel au modèle : tout est déterministe et gratuit. Prérequis : pip install mcp
import json, pathlib, re, sys

ICI = pathlib.Path(__file__).parent
sys.path.insert(0, str(ICI))
import app  # noqa: E402  (importer app ne démarre pas le serveur HTTP)
from app import ev  # noqa: E402  (evals/evaluer.py, déjà importé par app)

try:
    from mcp.server.mcpserver import MCPServer as Serveur  # mcp 2.x
except ImportError:
    from mcp.server.fastmcp import FastMCP as Serveur  # mcp 1.x

mcp = Serveur("lecture-dce")


def lire_json(texte):
    """Le JSON d'une réponse du skill, seul ou au milieu d'un texte (même extraction que evaluer.appeler)."""
    m = re.search(r"\{.*\}", texte or "", re.S)
    if not m:
        return None, "Aucun objet JSON trouvé dans la réponse."
    try:
        rep = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        return None, f"JSON illisible : {e.msg}, ligne {e.lineno}."
    return (rep, None) if isinstance(rep, dict) else (None, "La réponse doit être un objet JSON.")


@mcp.tool()
def lister_dossiers() -> list[dict]:
    """Liste les 5 dossiers de consultation (DCE) de test : id et titre."""
    return [{"id": c["id"], "titre": c["titre"]} for c in app.cas_disponibles()]


@mcp.tool()
def lire_dossier(cas: str) -> str:
    """Renvoie le texte d'un dossier de test (cas-01 à cas-05)."""
    if not re.fullmatch(r"cas-\d\d", cas or "") or not (app.EV / cas / "dce.md").is_file():
        raise ValueError(f"Dossier inconnu : {cas!r}. Utiliser lister_dossiers.")
    return (app.EV / cas / "dce.md").read_text(encoding="utf-8")


@mcp.tool()
def verifier_reponse(reponse_json: str, texte_dossier: str) -> dict:
    """Contrôle le format d'une réponse du skill : 12 clés, statuts connus, une source par valeur trouvée,
    et les explications des risques (pourquoi, que faire, question, chiffres absents du dossier)."""
    rep, erreur = lire_json(reponse_json)
    if erreur:
        return {"ok": False, "erreur": erreur}
    return {**app.controler(rep), "explications": ev.controler_explications(rep, texte_dossier)}


@mcp.tool()
def noter_reponse(cas: str, reponse_json: str) -> dict:
    """Note une réponse sur un dossier de test, comme le banc : points sur 36, inventions, statuts faux, détail par clé."""
    lire_dossier(cas)  # même contrôle du nom de dossier
    rep, erreur = lire_json(reponse_json)
    if erreur:
        return {"erreur": erreur}
    return app.noter(rep, cas)


if __name__ == "__main__":
    if "--http" in sys.argv:
        i = sys.argv.index("--http")
        port = int(sys.argv[i + 1]) if len(sys.argv) > i + 1 else 8791
        mcp.run("streamable-http", host="127.0.0.1", port=port)  # jamais 0.0.0.0 : aucune authentification ici
    else:
        mcp.run("stdio")
