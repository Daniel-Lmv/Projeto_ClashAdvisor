"""MCP próprio, separado do notebook. Execute: python -m clashadvisor.server"""

from pathlib import Path

from dotenv import load_dotenv
from fastmcp import FastMCP

from .domain import calculate_builders
from .supercell import get_player

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)

mcp = FastMCP("ClashAdvisor - ferramentas próprias")


@mcp.tool()
def consultar_jogador(tag: str) -> dict:
    """Consulta perfil real de Clash of Clans pela tag usando a API oficial da Supercell."""
    return get_player(tag)


@mcp.tool()
def calcular_construtores(duracoes_horas: list[float], construtores: int) -> dict:
    """Distribui melhorias independentes por construtores e estima conclusão em horas."""
    return calculate_builders(duracoes_horas, construtores)


@mcp.tool()
def calcular_recursos(atual: int, custo: int) -> dict:
    """Calcula quantos recursos faltam para uma melhoria."""
    if atual < 0 or custo < 0:
        raise ValueError("Valores devem ser não negativos.")
    return {"atual": atual, "custo": custo, "faltam": max(0, custo - atual)}


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8000)
