"""Validação conservadora de evidências da busca MCP comunitária.

Não confunde 'uma URL encontrada' com 'fonte recente e relevante'.
"""
import re
from datetime import date
from urllib.parse import urlsplit

URL_RE = re.compile(r'https?://[^\s<>"\'`]+', re.I)
TH12_RE = re.compile(r'\b(?:th\s*[- ]?12|town\s*hall\s*12|centro\s*de\s*vila\s*12|cv\s*12)\b', re.I)
ATTACK_RE = re.compile(r'attack|strategy|strategies|ataque|estrat[eé]gia|army|armies|ex[eé]rcito|composition|composi[cç][aã]o', re.I)


def extract_urls(raw: str) -> list[str]:
    found = []
    for match in URL_RE.finditer(raw):
        url = match.group(0).rstrip('.,;:!?)\\]}')
        parsed = urlsplit(url)
        if parsed.netloc and url not in found:
            found.append(url)
    return found


def assess(raw: str, question: str, today: date | None = None) -> dict:
    """Heurística: não garante a relevância da página, apenas a evidência no retorno."""
    today = today or date.today()
    urls = extract_urls(raw)
    want_recent = bool(re.search(r'recent|atualizad|202[4-9]|latest|current|novidad', question, re.I))
    target_th12 = bool(TH12_RE.search(question))
    target_attack = bool(ATTACK_RE.search(question))
    relevant = []
    fresh = []
    stale = []
    unknown_date = []
    for url in urls:
        path = urlsplit(url).path.casefold()
        # Índices de categoria e guias de outras faixas não respondem ao pedido CV12.
        if target_attack and re.search(r'/category/|/tag/|/page/\d+/?$', path):
            continue
        if target_th12 and re.search(r'(?:th|cv)\s*[-_]?\s*(?:10|11|13|14|15|16)\b', path) and not re.search(r'(?:th|cv)\s*[-_]?\s*12\b', path):
            continue
        pos = raw.find(url)
        # Nearby text from search result, not arbitrary unrelated text elsewhere.
        context = raw[max(0, pos - 240):min(len(raw), pos + len(url) + 350)]
        match_th12 = not target_th12 or bool(TH12_RE.search(context + ' ' + url))
        match_attack = not target_attack or bool(ATTACK_RE.search(context + ' ' + url))
        if not (match_th12 and match_attack):
            continue
        relevant.append(url)
        years = [int(y) for y in re.findall(r'\b20(?:1\d|2\d|3\d)\b', context)]
        if not years:
            unknown_date.append(url)
        elif max(years) >= today.year - 1:
            fresh.append(url)
        else:
            stale.append(url)
    # For freshness, absence of a date is unknown, never automatically current.
    enough = bool(fresh) if want_recent else bool(relevant)
    return {'urls': urls, 'relevant_urls': relevant, 'fresh_urls': fresh,
            'stale_urls': stale, 'unknown_date_urls': unknown_date,
            'needs_retry': not enough, 'recent_requested': want_recent}


def retry_query(question: str, year: int | None = None) -> str:
    year = year or date.today().year
    if TH12_RE.search(question):
        return f'Clash of Clans Town Hall 12 TH12 attack strategies army compositions {year} guide'
    return f'{question.strip()} {year} official updated guide'
