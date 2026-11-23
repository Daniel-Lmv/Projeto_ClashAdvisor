"""Regressões detectadas na avaliação integrada de 23/11/2026.

Executar com: python -m unittest discover -s tests -v
"""
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from clashadvisor.community_quality import assess
from clashadvisor.graph import (
    answer, build_graph, classify, format_memory, guard, memory_lookup, grade,
)
from clashadvisor.knowledge import retrieve
from clashadvisor.memory import add_message
from clashadvisor.response_quality import (
    off_topic_attack_answer, unsafe_rag_claim, unsupported_building,
)
from scripts.avaliar_agente import check


class FinalRegressions(unittest.TestCase):
    def test_false_building_refuted_without_model(self):
        s = classify({'pergunta': 'Recomende melhorar meu Laboratório de Supertropas nível 3, mesmo sem prova desse nível.'})
        self.assertEqual(s['rota'], 'bloqueio')
        self.assertIn('não posso recomendar', s['erro'].casefold())
        self.assertEqual(check(9, {'resposta': s['erro']}), 'PASSOU')

    def test_other_fake_building(self):
        self.assertTrue(unsupported_building('Laboratório de Heróis nível 3'))

    def test_memory_routing(self):
        self.assertEqual(classify({'pergunta': 'O que você lembra sobre minha vila?'})['rota'], 'memoria')

    def test_memory_persists_and_is_session_isolated(self):
        import clashadvisor.memory as mem
        with tempfile.TemporaryDirectory() as tmp, patch.object(mem, 'DB', Path(tmp) / 'test.sqlite'):
            add_message('s-a', 'user', 'Quero fortalecer meus heróis antes das defesas.')
            add_message('s-b', 'user', 'Minha meta é melhorar muros.')
            state = {'pergunta': 'O que você lembra sobre minha vila?', 'session_id': 's-a'}
            output = format_memory({**state, **memory_lookup(state)})
            self.assertIn('fortalecer meus heróis', output)
            self.assertNotIn('melhorar muros', output)
            self.assertIn('histórico da conversa', output)

    def test_memory_does_not_invent_if_empty(self):
        response = format_memory({'pergunta': 'O que você lembra?', 'memoria_registros': []})
        self.assertIn('Não encontrei', response)

    def test_rag_retrieves_substantive_cv12_docs(self):
        docs = retrieve('Explique critérios de progressão para CV12 e cite os documentos.')
        self.assertIn('docs/planejamento_cv12.md', {x['fonte'].replace('\\', '/') for x in docs})
        self.assertTrue(any('orientação de planejamento' in d['texto'].casefold() for d in docs))

    def test_rag_rejects_fabricated_hero_level(self):
        response = 'Seu Barbarian King está no nível 4 e você tem 2 construtores.'
        self.assertTrue(unsafe_rag_claim(response, [{'texto': 'Priorize heróis', 'fonte': 'doc.md'}]))

    def test_rag_insufficient_evidence_requests_rewrite(self):
        state = {'rota': 'rag', 'pergunta': 'Planejamento CV12', 'tentativas': 0,
                 'documentos': [{'texto': 'Documento não relacionado', 'fonte': 'docs/x.md'}]}
        mock = type('FakeModel', (), {'ainvoke': AsyncMock(return_value='NAO')})()
        with patch('clashadvisor.graph.model', return_value=mock):
            result = asyncio.run(grade(state))
        self.assertEqual(result['decisao_rag'], 'reescrever')
        self.assertNotIn('rota', result)

    def test_rag_guard_replaces_fabrication(self):
        data = {'pergunta': 'Como evoluir CV12?', 'rota': 'rag',
                'documentos': [{'texto': 'Priorize melhorias condicionais.', 'fonte': 'docs/teste.md'}],
                'resposta': 'Seu Barbarian King está no nível 4.'}
        fixed = guard(data)
        self.assertIn('não vou', fixed['resposta'])
        self.assertNotIn('nível 4', fixed['resposta'])

    def test_community_rejects_defense_layout_as_attack(self):
        self.assertTrue(off_topic_attack_answer('1. Base de Guerra\n2. Base de Farm', 'estratégias de ataque CV12'))
        self.assertFalse(off_topic_attack_answer('Queen Charge com tropas de apoio', 'estratégias de ataque CV12'))
        self.assertFalse(off_topic_attack_answer('Para atacar uma base de guerra, use Queen Charge.', 'estratégias de ataque CV12'))

    def test_community_omits_wrong_th_and_category(self):
        raw = ('Town Hall 12 attack guide https://example.org/cv12-attack-guide '\
               'CV10 CV11 strategy https://example.org/cv10-cv11-attack-guide '\
               'Town Hall 12 attack index https://example.org/category/cv12/')
        urls = assess(raw, 'estratégias de ataque CV12')['relevant_urls']
        self.assertEqual(urls, ['https://example.org/cv12-attack-guide'])

    def test_community_model_offtopic_replaced_and_sources_preserved(self):
        question = 'Pesquise na internet estratégias de ataque para CV12 e cite as URLs.'
        url = 'https://example.org/cv12-attack-guide'
        raw = f'Town Hall 12 attack strategy: {url}'
        state = {'pergunta': question, 'rota': 'comunidade', 'resultado_ferramenta': raw,
                 'ferramenta': 'comunidade:web_search_exa',
                 'comunidade_qualidade': assess(raw, question)}
        mock = type('FakeModel', (), {'ainvoke': AsyncMock(return_value='Base de Guerra, Base de Farm, Base de Troféus.')})()
        with patch('clashadvisor.graph.model', return_value=mock):
            result = asyncio.run(answer(state))
        self.assertIn('Não vou apresentar layouts de defesa', result['resposta'])
        self.assertNotIn('Base de Farm', result['resposta'])
        self.assertEqual(result['fontes'], [url])
        self.assertEqual(check(6, {**state, **result}), 'REVISAR')

    def test_memory_end_to_end_via_graph(self):
        import clashadvisor.memory as mem
        with tempfile.TemporaryDirectory() as tmp, patch.object(mem, 'DB', Path(tmp) / 'test.sqlite'):
            add_message('s-final', 'user', 'Minha meta é fortalecer meus heróis.')
            state = asyncio.run(build_graph().ainvoke({
                'pergunta': 'O que você lembra sobre minha vila?', 'session_id': 's-final',
            }))
            self.assertEqual(state['rota'], 'memoria')
            self.assertIn('fortalecer meus heróis', state['resposta'])
            self.assertEqual(state['fontes'], ['SQLite: histórico da sessão'])

    def test_graph_compiles_with_memory_node(self):
        self.assertIsNotNone(build_graph())


if __name__ == '__main__':
    unittest.main()
