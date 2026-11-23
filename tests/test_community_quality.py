import unittest
from datetime import date
from clashadvisor.community_quality import assess, extract_urls, retry_query

TODAY = date(2026, 11, 23)
Q = 'Pesquise na internet estratégias recentes de ataque para Centro de Vila 12'

class CommunityQualityTests(unittest.TestCase):
    def test_url_extraction(self):
        self.assertEqual(extract_urls('Link https://example.org/th12).'), ['https://example.org/th12'])
    def test_old_result_requires_retry(self):
        raw = '5 best Town Hall 12 attack strategies published 2022 https://example.org/th12-attack'
        result = assess(raw, Q, TODAY)
        self.assertTrue(result['needs_retry'])
        self.assertEqual(len(result['stale_urls']), 1)
    def test_current_result_passes(self):
        raw = '2026 Town Hall 12 attack strategies https://example.org/th12-attack-2026'
        result = assess(raw, Q, TODAY)
        self.assertFalse(result['needs_retry'])
        self.assertEqual(len(result['fresh_urls']), 1)
    def test_undated_not_fresh(self):
        raw = 'Town Hall 12 attack strategies https://example.org/th12-attack'
        result = assess(raw, Q, TODAY)
        self.assertTrue(result['needs_retry'])
        self.assertEqual(len(result['unknown_date_urls']), 1)
    def test_unrelated_result_rejected(self):
        raw = 'Town Hall 16 base design https://example.org/th16-base'
        self.assertEqual(assess(raw, Q, TODAY)['relevant_urls'], [])
    def test_retry_query(self):
        self.assertIn('2026', retry_query(Q, 2026))
        self.assertIn('Town Hall 12', retry_query(Q, 2026))

if __name__ == '__main__': unittest.main()
