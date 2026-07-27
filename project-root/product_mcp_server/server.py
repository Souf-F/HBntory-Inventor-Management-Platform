import os

from mcp_instance import mcp

# Importer les modules tools/* enregistre leurs @mcp.tool() sur l'instance
# partagee definie dans mcp_instance.py. Tant qu'ils sont vides (TODO),
# le serveur demarre sans exposer de tool.
import tools.products  # noqa: F401
import tools.stock  # noqa: F401

if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=int(os.environ.get("MCP_PORT", 8000)),
    )