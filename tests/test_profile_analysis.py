import unittest
from clashadvisor.profile_analysis import normalize_profile, planning_evidence


class TestProfileAnalysis(unittest.TestCase):
    def setUp(self):
        self.data = {
            'nome': 'Teste', 'tag': '#P0Y8Q2', 'centro_vila': 12,
            'herois': [{'nome': 'Barbarian King', 'nivel': 4}, {'nome': 'Battle Machine', 'nivel': 3}],
            'tropas': [{'nome': 'Dragon', 'nivel': 7}, {'nome': 'Raged Barbarian', 'nivel': 6}, {'nome': 'Super Archer', 'nivel': 1}],
            'magias': [{'nome': 'Rage Spell', 'nivel': 4}],
        }

    def test_heroes_separated(self):
        p = normalize_profile(self.data)
        self.assertEqual(p['herois']['vila_principal'][0]['nome'], 'Barbarian King')
        self.assertEqual(p['herois']['base_construtor'][0]['nome'], 'Battle Machine')

    def test_troops_separated(self):
        p = normalize_profile(self.data)
        self.assertEqual(len(p['tropas']['vila_principal']), 1)
        self.assertEqual(len(p['tropas']['base_construtor']), 1)
        self.assertEqual(len(p['tropas']['especiais']), 1)

    def test_compact_evidence(self):
        e = planning_evidence(normalize_profile(self.data), 'Quais melhorias devo priorizar na minha vila?')
        self.assertEqual(e['tropas_vila_principal'], [])
        self.assertEqual(e['magias'], [])
        self.assertEqual(e['jogador']['centro_vila'], 12)

    def test_specific_troops(self):
        e = planning_evidence(normalize_profile(self.data), 'Quais tropas devo melhorar?')
        self.assertEqual(e['tropas_vila_principal'][0]['nome'], 'Dragon')


if __name__ == '__main__':
    unittest.main()
