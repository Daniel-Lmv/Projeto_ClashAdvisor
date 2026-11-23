import unittest
from unittest.mock import patch
from clashadvisor.domain import extract_tag, sanitize_tag, calculate_builders
from clashadvisor.knowledge import retrieve
from clashadvisor.skills import load_skill
from clashadvisor.graph import classify, parse_builder_request, build_graph


class TestClashAdvisor(unittest.TestCase):
    def test_tag(self):
        self.assertEqual(extract_tag('analise #P0Y8Q2'), '#P0Y8Q2')
    def test_tag_invalida(self):
        self.assertIsNone(extract_tag('tag #ABC123'))
    def test_sanitize(self):
        with self.assertRaises(ValueError):
            sanitize_tag('#ABC123')
    def test_builders(self):
        self.assertEqual(calculate_builders([6, 4, 2], 2)['tempo_total_horas'], 6)
    def test_builder_invalid(self):
        with self.assertRaises(ValueError):
            calculate_builders([0], 2)
    def test_parse(self):
        self.assertEqual(parse_builder_request('Tenho 2 construtores e melhorias de 6, 4 e 2 horas'), ([6, 4, 2], 2))
    def test_route_profile(self):
        self.assertEqual(classify({'pergunta': 'Analise #P0Y8Q2'})['rota'], 'perfil')
    def test_route_rag(self):
        self.assertEqual(classify({'pergunta': 'Como priorizar a evolução?'})['rota'], 'rag')
    def test_route_community(self):
        self.assertEqual(classify({'pergunta': 'Pesquise na web novidades do jogo'})['rota'], 'comunidade')
    def test_rag(self):
        self.assertTrue(retrieve('planejamento construtores melhorias'))
    def test_skills(self):
        self.assertIn('Planejamento', load_skill('planejamento'))
    def test_graph(self):
        self.assertIsNotNone(build_graph())

if __name__ == '__main__':
    unittest.main()


class TestPerfilAutomatico(unittest.TestCase):
    def test_pergunta_pessoal_usa_tag_configurada(self):
        with patch('clashadvisor.graph.default_tag', return_value='#P0Y8Q2'):
            self.assertEqual(classify({'pergunta': 'Qual é meu Centro de Vila e quais heróis eu tenho?'})['rota'], 'perfil')
            self.assertEqual(classify({'pergunta': 'Quais melhorias devo priorizar para evoluir minha vila?'})['rota'], 'perfil_planejamento')

    def test_pergunta_generica_nao_consulta_perfil(self):
        with patch('clashadvisor.graph.default_tag', return_value='#P0Y8Q2'):
            self.assertEqual(classify({'pergunta': 'Como funciona o Centro de Vila?'})['rota'], 'rag')

    def test_pergunta_pessoal_sem_tag(self):
        with patch('clashadvisor.graph.default_tag', return_value=None):
            self.assertEqual(classify({'pergunta': 'Qual é meu Centro de Vila?'})['rota'], 'bloqueio')

    def test_decodifica_retorno_mcp(self):
        import json
        from clashadvisor.graph import unwrap_mcp
        raw = [{'type': 'text', 'text': json.dumps({'tempo_total_horas': 6, 'cargas_horas': [6, 6]})}]
        self.assertEqual(unwrap_mcp(raw)['tempo_total_horas'], 6)

    def test_consulta_perfil_recebe_tag_padrao(self):
        import asyncio
        from unittest.mock import AsyncMock
        from clashadvisor.graph import profile
        payload = {'tag': '#P0Y8Q2', 'centro_vila': 12, 'herois': []}
        with patch('clashadvisor.graph.default_tag', return_value='#P0Y8Q2'), \
             patch('clashadvisor.graph.own_tool', new_callable=AsyncMock, return_value=payload) as tool:
            result = asyncio.run(profile({'pergunta': 'Quais são meus heróis?'}))
        tool.assert_awaited_once_with('consultar_jogador', {'tag': '#P0Y8Q2'})
        self.assertEqual(result['perfil_dados']['centro_vila'], 12)

    def test_resposta_perfil_deterministica(self):
        import asyncio
        from clashadvisor.graph import answer
        state = {'pergunta': 'Qual é meu CV?', 'rota': 'perfil', 'perfil_dados': {
            'tag': '#P0Y8Q2', 'nome': 'Teste', 'centro_vila': 12,
            'herois': [{'nome': 'Barbarian King', 'nivel': 4}],
        }}
        result = asyncio.run(answer(state))
        self.assertIn('**Centro de Vila:** 12', result['resposta'])
        self.assertIn('nível 4', result['resposta'])
