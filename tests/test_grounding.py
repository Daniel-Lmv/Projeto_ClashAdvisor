import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from clashadvisor.grounding import candidates, parse_selection, render_plan, safe_fallback
from clashadvisor.graph import guard, after_guard, repair_plan, grade, after_grade, classify, answer

PROFILE = {'nome':'Teste','tag':'#P0Y8Q2','centro_vila':12,
           'herois':[{'nome':'Barbarian King','nivel':4},{'nome':'Battle Machine','nivel':3}],
           'tropas':[{'nome':'Super Archer','nivel':1}]}

class GroundingTests(unittest.TestCase):
    def test_no_building_levels(self):
        output = safe_fallback(PROFILE)
        self.assertIn('Barbarian King (nível 4)', output)
        self.assertNotIn('Laboratório de Supertropas', output)
        self.assertNotIn('Laboratório de Heróis', output)
        self.assertNotIn('Battle Machine', output)
    def test_reject_unknown_id(self):
        self.assertIsNone(parse_selection('{"prioridades":["laboratorio_nivel_3"]}', {'herois'}))
    def test_reject_free_text(self):
        self.assertIsNone(parse_selection('{"prioridades":["herois"],"explicacao":"laboratorio nivel 3"}', {'herois'}))
    def test_valid_ids(self):
        self.assertEqual(parse_selection('{"prioridades":["herois","infra"]}', {'herois','infra'}), ['herois','infra'])
    def test_retry_then_fallback(self):
        s = {'rota':'perfil_planejamento','perfil_dados':PROFILE,'selecao_planejamento':'texto inventado'}
        first = guard(s)
        self.assertTrue(first['falha_fundamentacao'])
        self.assertEqual(after_guard({**s,**first}), 'corrigir')
        with patch('clashadvisor.graph.model', return_value=type('M', (), {'ainvoke':AsyncMock(return_value='invalido')})()):
            second = asyncio.run(repair_plan({**s,**first}))
        result = guard({**s,**second})
        self.assertFalse(result['falha_fundamentacao'])
        self.assertIn('Dados que faltam', result['resposta'])
    def test_rag_grade_preserves_planning_route(self):
        s = {'rota': 'perfil_planejamento', 'pergunta': 'Quais melhorias devo priorizar?',
             'tentativas': 2, 'documentos': [{'texto': 'Priorizar heróis', 'fonte': 'docs/teste.md'}]}
        with patch('clashadvisor.graph.model', return_value=type('M', (), {'ainvoke':AsyncMock(return_value='SIM')})()):
            result = asyncio.run(grade(s))
        self.assertNotIn('rota', result)
        self.assertEqual(after_grade({**s, **result}), 'responder')
        self.assertEqual(({**s, **result})['rota'], 'perfil_planejamento')

    def test_internet_query_routes_community(self):
        question = 'Pesquise na internet informações recentes sobre estratégias de ataque para Centro de Vila 12 no Clash of Clans. Apresente as fontes consultadas.'
        self.assertEqual(classify({'pergunta': question})['rota'], 'comunidade')

    def test_community_error_is_not_replaced_by_rag(self):
        state = {'rota': 'comunidade', 'pergunta': 'Pesquise na internet',
                 'erro': 'MCP comunitário indisponível: conexão falhou',
                 'documentos': [{'texto': 'Texto antigo', 'fonte': 'docs/antigo.md'}]}
        result = asyncio.run(answer(state))
        self.assertIn('indisponível', result['resposta'])
        self.assertEqual(result['fontes'], [])

    def test_valid_selection_deterministic(self):
        s={'rota':'perfil_planejamento','perfil_dados':PROFILE,'selecao_planejamento':'{"prioridades":["infra"]}'}
        self.assertIn('Conferir a infraestrutura',guard(s)['resposta'])

if __name__ == '__main__': unittest.main()
