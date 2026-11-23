"""Planejamento fechado em evidências: LLM seleciona IDs, nunca escreve fatos livres."""
import json
import re

from .profile_analysis import normalize_profile


def candidates(raw: dict) -> list[dict]:
    profile = normalize_profile(raw)
    items = []
    heroes = profile['herois']['vila_principal']
    if heroes:
        names = ', '.join(f"{h['nome']} (nível {h['nivel']})" for h in heroes if isinstance(h.get('nivel'), int))
        if names:
            items.append({'id': 'herois', 'titulo': 'Avaliar a evolução dos heróis da vila principal',
                          'evidencia': f'Heróis informados pela API: {names}.',
                          'acao': 'Priorize os heróis usados no seu exército, após conferir custos e limites atuais no jogo.'})
    items.append({'id': 'infra', 'titulo': 'Conferir a infraestrutura ofensiva',
                  'evidencia': 'A API pública do perfil não informa os níveis do laboratório, acampamentos e castelo do clã.',
                  'acao': 'Verifique esses níveis dentro do jogo antes de decidir qual edifício melhorar.'})
    items.append({'id': 'exercito', 'titulo': 'Definir um exército principal',
                  'evidencia': 'A API lista níveis de unidades, mas não informa quais você usa com maior frequência.',
                  'acao': 'Escolha uma composição de ataque e avalie as tropas e magias dessa composição; não melhore tudo indiscriminadamente.'})
    items.append({'id': 'cv', 'titulo': 'Adiar a decisão de subir o Centro de Vila',
                  'evidencia': f"Centro de Vila informado pela API: {profile['jogador'].get('centro_vila') or 'não informado'}; níveis de edifícios e melhorias em andamento não disponíveis.",
                  'acao': 'Compare seu progresso ofensivo e objetivos antes de decidir avançar o Centro de Vila.'})
    return items


def parse_selection(text: str, allowed: set[str]) -> list[str] | None:
    """Aceita apenas JSON estrito {\"prioridades\": [IDs]}; rejeita conteúdo extra."""
    try:
        obj = json.loads(text.strip())
    except (ValueError, TypeError):
        return None
    if not isinstance(obj, dict) or set(obj) != {'prioridades'}:
        return None
    ids = obj['prioridades']
    if not isinstance(ids, list) or not 1 <= len(ids) <= 3 or any(not isinstance(i, str) or i not in allowed for i in ids):
        return None
    if len(set(ids)) != len(ids):
        return None
    return ids


def render_plan(raw: dict, selected: list[str]) -> str:
    options = {x['id']: x for x in candidates(raw)}
    lines = ['**Prioridades condicionais para sua vila**', '']
    for index, key in enumerate(selected, 1):
        item = options[key]
        lines.extend([f"{index}. **{item['titulo']}**", f"   - Evidência: {item['evidencia']}", f"   - Próxima ação: {item['acao']}"])
    lines.extend(['', '**Dados que faltam:** níveis reais dos edifícios, melhorias em andamento, recursos, construtores disponíveis e seu objetivo de jogo.',
                  '**Limite da análise:** a API de perfil não permite afirmar níveis de edifícios que não foram informados.'])
    return '\n'.join(lines)


def safe_fallback(raw: dict) -> str:
    allowed = {x['id'] for x in candidates(raw)}
    ids = [x for x in ('herois', 'infra', 'exercito') if x in allowed]
    return render_plan(raw, ids)
