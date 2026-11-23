"""Busca lexical local para o RAG, com normalização e diversidade de documentos."""
import re
import unicodedata
from .config import ROOT

STOP = {'sobre', 'para', 'como', 'quais', 'qual', 'quero', 'minha', 'meu', 'uma', 'com', 'que', 'dos', 'das', 'por', 'tem', 'sao', 'cite', 'documentos', 'explique', 'criterios', 'de', 'na', 'no'}


def terms(text: str) -> set[str]:
    normalized = ''.join(c for c in unicodedata.normalize('NFKD', text.casefold()) if not unicodedata.combining(c))
    return {w for w in re.findall(r'[\w]{3,}', normalized) if w not in STOP}


def expanded_terms(query: str) -> set[str]:
    words = terms(query)
    if words & {'progressao', 'evolucao', 'planejamento', 'priorizar', 'prioridade'}:
        words |= {'planejamento', 'evolucao', 'prioridade', 'herois', 'melhorias'}
    if words & {'cv12', 'th12'} or {'centro', 'vila', '12'} <= words:
        words |= {'cv12', 'vila', 'planejamento'}
    return words


def retrieve(query: str, limit: int = 3) -> list[dict]:
    words = expanded_terms(query)
    scored = []
    for path in sorted((ROOT / 'docs').glob('*.md')):
        content = path.read_text(encoding='utf-8')
        chunks = [x.strip() for x in content.split('\n\n') if x.strip()]
        title = terms(chunks[0]) if chunks else set()
        for chunk in chunks:
            overlap = len(words & terms(chunk))
            if overlap:
                # Seções de documentação são mais úteis que listas de links isoladas.
                title_bonus = min(2, len(words & title))
                index_penalty = 2 if path.stem == 'fontes' else 0
                link_penalty = min(2, chunk.count('http'))
                short_penalty = 3 if len(chunk) < 90 else 0
                content_bonus = 1 if (words & {'planejamento', 'evolucao', 'prioridade'} and
                                      ('prioridade' in terms(chunk) or 'verificar' in terms(chunk))) else 0
                scored.append({'fonte': str(path.relative_to(ROOT)), 'texto': chunk,
                               'score': overlap + title_bonus + content_bonus - index_penalty - link_penalty - short_penalty})
    # Uma passagem por fonte evita que 3 trechos do índice de fontes
    # expulsem o documento substantivo sobre CV12.
    selected, seen = [], set()
    for item in sorted(scored, key=lambda x: (-x['score'], x['fonte'])):
        if item['fonte'] in seen:
            continue
        selected.append(item)
        seen.add(item['fonte'])
        if len(selected) >= limit:
            break
    return selected
