import os
from urllib.parse import quote
import requests
from .domain import sanitize_tag


class SupercellError(RuntimeError):
    pass


def get_player(tag: str) -> dict:
    valid = sanitize_tag(tag)
    token = os.getenv('COC_API_TOKEN', '').strip()
    if not token:
        raise SupercellError('COC_API_TOKEN não configurado no .env do servidor.')
    try:
        response = requests.get(
            f'https://api.clashofclans.com/v1/players/{quote(valid, safe="")}',
            headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json'},
            timeout=15,
        )
    except requests.RequestException as exc:
        raise SupercellError(f'Falha de rede ao consultar Supercell: {exc}') from exc
    if response.status_code != 200:
        messages = {401: 'token inválido', 403: 'acesso negado; confira IP autorizado e permissões', 404: 'jogador não encontrado', 429: 'limite de requisições'}
        raise SupercellError(f'API Supercell HTTP {response.status_code}: {messages.get(response.status_code, "erro na consulta")}')
    data = response.json()
    return {
        'tag': data.get('tag'), 'nome': data.get('name'),
        'centro_vila': data.get('townHallLevel'), 'trofeus': data.get('trophies'),
        'herois': [{'nome': h.get('name'), 'nivel': h.get('level')} for h in data.get('heroes', [])],
        'tropas': [{'nome': t.get('name'), 'nivel': t.get('level')} for t in data.get('troops', [])],
        'magias': [{'nome': s.get('name'), 'nivel': s.get('level')} for s in data.get('spells', [])],
        'observacao': 'A API não expõe todas as construções, recursos armazenados ou melhorias em andamento.',
    }
