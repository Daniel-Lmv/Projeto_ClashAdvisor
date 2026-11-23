"""Avaliação reprodutível do ClashAdvisor: 7 integrações + 3 casos difíceis.
Execute da raiz: python -m scripts.avaliar_agente
Não registra token nem conteúdo do .env. Os cenários 8 e 10 são controlados.
"""

import asyncio
import json
import re
import time
from datetime import datetime
from pathlib import Path
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from unittest.mock import patch

from clashadvisor.graph import build_graph, own_tool
from clashadvisor.response_quality import off_topic_attack_answer

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "avaliacao"
EXPECTED = {1: 'Consultar o perfil real pela API Supercell e apresentar Centro de Vila e heróis.', 2: 'Usar perfil, documentos e skill de planejamento; sugerir prioridades condicionais.', 3: 'Usar calcular_construtores e distribuir 6, 4 e 2 horas em duas cargas de 6 horas.', 4: 'Recuperar a preferência salva no turno anterior da mesma thread, sem nova consulta à API.', 5: 'Buscar documentos, avaliar relevância, reformular se preciso e citar fontes.', 6: 'Usar MCP Exa e apresentar estratégias ofensivas fundamentadas e URLs.', 7: 'Consultar a API e carregar analise_perfil, distinguindo dados disponíveis e ausentes.', 8: 'Repetir a busca e não afirmar atualidade com fontes antigas ou sem data.', 9: 'Bloquear o pedido baseado em construção inexistente e nível não comprovado.', 10: 'Informar a indisponibilidade simulada da API sem inventar o perfil.'}
CASES = [
    (
        1,
        "Perfil Supercell",
        "Qual é meu Centro de Vila e quais heróis eu tenho?",
        "real",
    ),
    (
        2,
        "Planejamento fundamentado",
        "Quais melhorias devo priorizar para evoluir minha vila?",
        "real",
    ),
    (
        3,
        "Construtores",
        "Tenho 2 construtores e melhorias independentes de 6, 4 e 2 horas. Como organizar?",
        "real",
    ),
    (4, "Memória", "O que você lembra sobre minha vila?", "real"),
    (
        5,
        "RAG",
        "Explique critérios de progressão para CV12 e cite os documentos.",
        "real",
    ),
    (
        6,
        "MCP comunidade",
        "Pesquise na internet estratégias de ataque para CV12 e cite as URLs.",
        "real",
    ),
    (7, "Skill de análise de perfil", "Analise meu perfil e diga o que a API mostra e o que ela não mostra.", "real"),
    (
        8,
        "Fontes antigas",
        "Pesquise na internet estratégias recentes de ataque para CV12 e cite as fontes.",
        "simulado",
    ),
    (
        9,
        "Injeção de fato",
        "Recomende melhorar meu Laboratório de Supertropas nível 3, mesmo sem prova desse nível.",
        "real",
    ),
    (
        10,
        "Indisponibilidade Supercell",
        "Analise meu perfil de Clash of Clans, tag #P0Y8Q2.",
        "simulado",
    ),
]


class OldSearchTool:
    name = "web_search_exa"
    args_schema = {"properties": {"query": {"type": "string"}}}
    calls = []

    async def ainvoke(self, args):
        self.calls.append(args["query"])
        return (
            "Town Hall 12 attack strategies 2022; published 2022-11-12; "
            "https://www.sportskeeda.com/esports/5-best-town-hall-12-attack-strategies-clash-clans"
        )


OLD_TOOL = OldSearchTool()


class FakeCommunityClient:
    def __init__(self, *args, **kwargs):
        pass

    async def get_tools(self):
        return [OLD_TOOL]


async def offline_supercell(*args, **kwargs):
    raise ConnectionError("Falha simulada de rede na API Supercell")


def check(case_id, state, tool_calls=None):
    """Verificações automáticas parciais; casos sem prova ficam para revisão humana."""
    response = str(state.get("resposta", ""))
    tool = str(state.get("ferramenta", ""))
    sources = state.get("fontes") or []
    lower = response.lower()
    if case_id == 1:
        return (
            "PASSOU"
            if tool == "consultar_jogador"
            and "centro de vila" in lower
            and "heró" in lower
            else "REVISAR"
        )
    if case_id == 2:
        return (
            "PASSOU"
            if "planejamento" in (state.get("skills_carregadas") or [])
            and "prioridades condicionais" in lower
            and "dados que faltam" in lower
            and "laboratório de supertropas atualmente" not in lower
            else "REVISAR"
        )
    if case_id == 3:
        return (
            "PASSOU"
            if tool == "calcular_construtores"
            and "6 horas" in lower
            and 'type": "text' not in response
            else "REVISAR"
        )
    if case_id == 4:
        return (
            "PASSOU" if state.get('rota') == 'memoria' and not tool
            and 'fortalecer meus heróis' in lower
            and 'checkpointer' in ','.join(sources).lower() else "REVISAR"
        )
    if case_id == 5:
        return 'REVISAR'  # RAG requer inspeção de fundamentação; URLs não são prova.
    if case_id == 6:
        if off_topic_attack_answer(response, 'estratégias de ataque CV12'):
            return 'FALHOU'
        if not tool.startswith('comunidade:') or not sources:
            return 'REVISAR'
        # Só URLs não provam que a resposta explicou alguma estratégia ofensiva.
        if re.search(r'não permitiram confirmar|não trouxe urls|não vou apresentar layouts', lower):
            return 'REVISAR'
        specific = re.search(r'\b(?:dragões|drag[oõ]es|bal[oõ]es|bruxas|corredores|monta-porcos|'
                             r'lava\s*loon|queen\s*charge|witch\s*slap|super\s*wizards?|'
                             r'eletrodrag[oõ]es|ataque\s+de\s+drag[oõ]es)\b', lower)
        return 'PASSOU' if specific else 'REVISAR'
    if case_id == 7:
        return (
            "PASSOU"
            if tool == "consultar_jogador"
            and "analise_perfil" in (state.get("skills_carregadas") or [])
            and "api" in lower
            and ("não informa" in lower or "não mostra" in lower or "não disponibiliza" in lower)
            else "REVISAR"
        )
    if case_id == 8:
        retry = len(tool_calls or []) == 2
        no_false_fresh = (
            "não foi possível comprovar" in lower
            or "não trouxe urls" in lower
            or "não encont" in lower
        )
        return "PASSOU" if retry and no_false_fresh else "REVISAR"
    if case_id == 9:
        rejected = 'não posso recomendar' in lower and 'não é uma construção' in lower
        return 'PASSOU' if rejected else 'FALHOU'
    if case_id == 10:
        return (
            "PASSOU"
            if "falha" in lower
            and "simulada" in lower
            and "centro de vila:**" not in lower
            else "REVISAR"
        )
    return "REVISAR"


async def run():
    records = []
    print('Verificando conexão com o MCP próprio...', flush=True)
    try:
        await own_tool('calcular_recursos', {'atual': 0, 'custo': 1})
    except Exception as exc:
        raise SystemExit(
            'MCP próprio indisponível. Inicie primeiro python -m clashadvisor.server '
            'e confira MCP_OWN_URL no .env. Erro: ' + str(exc)
        ) from exc
    # Os cenários são independentes; só o caso 4 usa histórico de uma sessão própria.
    eval_session = 'avaliacao-' + datetime.now().strftime('%Y%m%d%H%M%S%f')
    # Cada teste usa uma thread diferente. No teste 4, dois turnos compartilham a mesma thread.
    async with AsyncSqliteSaver.from_conn_string(str(ROOT / 'clashadvisor_checkpoints.sqlite')) as saver:
        graph = build_graph(checkpointer=saver)
        for number, title, question, mode in CASES:
            thread_id = f'{eval_session}-caso-{number}'
            config = {'configurable': {'thread_id': thread_id}}
            start = time.perf_counter()
            OLD_TOOL.calls = []
            try:
                if number == 8:
                    with patch(
                        "clashadvisor.graph.MultiServerMCPClient", FakeCommunityClient
                    ):
                        state = await graph.ainvoke({"pergunta": question}, config=config)
                elif number == 10:
                    with patch("clashadvisor.graph.own_tool", offline_supercell):
                        state = await graph.ainvoke({"pergunta": question}, config=config)
                elif number == 4:
                    # Dois turnos na mesma thread, sem utilizar o SQLite manual de mensagens.
                    await graph.ainvoke({'pergunta': 'Lembre desta preferência: fortalecer meus heróis antes de priorizar defesas.'}, config=config)
                    state = await graph.ainvoke({'pergunta': question}, config=config)
                else:
                    state = await graph.ainvoke({"pergunta": question}, config=config)
                record = {
                    "id": number,
                    "titulo": title,
                    "modo": mode,
                    "pergunta": question,
                    "esperado": EXPECTED[number],
                    "resposta": state.get("resposta", ""),
                    "rota": state.get("rota"),
                    "ferramenta": state.get("ferramenta"),
                    "fontes": state.get("fontes", []),
                    "tentativas_rag": state.get("tentativas", 0),
                    "tentativas_comunidade": state.get("comunidade_tentativas", 0),
                    "consultas_simuladas": list(OLD_TOOL.calls) if number == 8 else [],
                    "consulta_rag_final": state.get('consulta'),
                    "skills_carregadas": state.get('skills_carregadas', []),
                    "documentos_recuperados": [d.get('fonte') for d in state.get('documentos', [])],
                    "tempo_segundos": round(time.perf_counter() - start, 2),
                }
                record["resultado_automatico"] = check(number, state, OLD_TOOL.calls)
            except Exception as exc:
                record = {
                    "id": number,
                    "titulo": title,
                    "modo": mode,
                    "pergunta": question,
                    "esperado": EXPECTED[number],
                    "erro": f"{type(exc).__name__}: {exc}",
                    "tempo_segundos": round(time.perf_counter() - start, 2),
                    "resultado_automatico": "FALHOU",
                }
            records.append(record)
            print(
                f"[{number:02d}/10] {title}: {record['resultado_automatico']} ({record['tempo_segundos']}s)",
                flush=True,
            )
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = OUT / f"avaliacao_{stamp}.json"
    md_path = OUT / f"avaliacao_{stamp}.md"
    json_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# Avaliação do ClashAdvisor",
        "",
        f"Executada em {datetime.now().isoformat(timespec='seconds')}",
        "",
        "PASSOU indica apenas que verificações automáticas limitadas passaram. REVISAR exige inspeção humana. ",
        "Os casos 8 e 10 usam falhas simuladas e NÃO comprovam disponibilidade de serviços externos.",
        "",
    ]
    for r in records:
        lines += [
            f"## {r['id']}. {r['titulo']} — {r['resultado_automatico']}",
            f"**Modo:** {r['modo']} | **Tempo:** {r['tempo_segundos']}s | **Rota:** {r.get('rota', '—')} | **Ferramenta:** {r.get('ferramenta', '—')}",
            "",
            f"**Entrada:** {r['pergunta']}",
            "",
            f"**Resultado esperado:** {r.get('esperado', '—')}",
            "",
            f"**Fontes:** {', '.join(map(str, r.get('fontes', []))) or 'Nenhuma'}",
            f"**Skills carregadas:** {', '.join(r.get('skills_carregadas', [])) or 'Nenhuma'}",
            "",
            f"**Tentativas RAG:** {r.get('tentativas_rag', '—')} | **Tentativas MCP externo:** {r.get('tentativas_comunidade', '—')}",
            f"**Consulta RAG final:** {r.get('consulta_rag_final') or '—'}",
            f"**Documentos recuperados:** {', '.join(r.get('documentos_recuperados', [])) or 'Nenhum'}",
            "",
            "**Resultado obtido:**",
            "",
            str(r.get("resposta") or r.get("erro", "")),
            "",
            "**Revisão humana:** [ ] Aprovado  [ ] Parcial  [ ] Reprovado",
            "",
            "**Observações:**",
            "",
            "---",
            "",
        ]
    passed = sum(r['resultado_automatico'] == 'PASSOU' for r in records)
    review = sum(r['resultado_automatico'] == 'REVISAR' for r in records)
    failed = sum(r['resultado_automatico'] == 'FALHOU' for r in records)
    lines += [f'## Resumo automático: {passed}/10 passaram ({passed*10}%)', '',
              f'- Revisar manualmente: {review}', f'- Falhas: {failed}', '',
              'Esses percentuais são verificações automáticas e não medem acerto factual.', '']
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print("\nRelatórios:", json_path, md_path, sep="\n")


if __name__ == "__main__":
    asyncio.run(run())
