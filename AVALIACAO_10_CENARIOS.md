# Dez casos de avaliação

O avaliador está em `scripts/avaliar_agente.py`. O relatório detalhado é gerado em `outputs/avaliacao/` e apresenta **entrada, resultado esperado, resultado obtido e situação** de cada caso.

| Caso | O que está sendo testado | Componente |
|---|---|---|
| 1 | Perfil do jogador | MCP próprio + `analise_perfil` |
| 2 | Prioridades de melhoria | RAG + `planejamento` + MCP próprio |
| 3 | Distribuição de construtores | MCP próprio |
| 4 | Recuperar uma preferência do turno anterior | Memória/checkpointer |
| 5 | Explicar a progressão com documentos | RAG com avaliação e reformulação |
| 6 | Buscar estratégias de ataque | MCP comunitário Exa |
| 7 | Separar dados disponíveis e ausentes da API | Skill `analise_perfil` |
| 8 | Busca recente com fonte antiga (simulação) | MCP Exa + proteção da resposta |
| 9 | Pedir melhoria de construção inexistente | Guardrail de entrada |
| 10 | API indisponível (simulação) | Tratamento de falhas |

**Casos desafiadores:** 8, 9 e 10.