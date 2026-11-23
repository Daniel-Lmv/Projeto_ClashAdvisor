"""Normalização conservadora do perfil público; não infere estado da vila."""

HOME_HEROES = {'Barbarian King', 'Archer Queen', 'Grand Warden', 'Royal Champion', 'Minion Prince', 'Dragon Duke'}
BUILDER_HEROES = {'Battle Machine', 'Battle Copter'}
BUILDER_TROOPS = {'Raged Barbarian', 'Sneaky Archer', 'Boxer Giant', 'Beta Minion', 'Bomber', 'Cannon Cart', 'Night Witch', 'Drop Ship', 'Dropship', 'Power P.E.K.K.A', 'Hog Glider', 'Electrofire Wizard'}
SUPER_TROOPS = {'Super Barbarian', 'Super Archer', 'Super Wall Breaker', 'Super Giant', 'Sneaky Goblin', 'Super Miner', 'Rocket Balloon', 'Inferno Dragon', 'Super Valkyrie', 'Super Witch', 'Ice Hound', 'Super Bowler', 'Super Dragon', 'Super Wizard', 'Super Minion', 'Super Hog Rider', 'Super Yeti'}


def normalize_profile(raw: dict) -> dict:
    """Separa categorias sem supor que a lista de unidades seja um inventário de edifícios."""
    def split(items, builder, special=frozenset()):
        groups = {'vila_principal': [], 'base_construtor': [], 'especiais': [], 'nao_classificados': []}
        for item in items or []:
            if not isinstance(item, dict):
                continue
            name = item.get('nome') or ''
            obj = {'nome': name, 'nivel': item.get('nivel')}
            if name in builder:
                groups['base_construtor'].append(obj)
            elif name in special:
                groups['especiais'].append(obj)
            elif name:
                groups['vila_principal'].append(obj)
            else:
                groups['nao_classificados'].append(obj)
        return groups

    heroes = split(raw.get('herois'), BUILDER_HEROES)
    heroes['nao_classificados'].extend(h for h in heroes['vila_principal'] if h['nome'] not in HOME_HEROES)
    heroes['vila_principal'] = [h for h in heroes['vila_principal'] if h['nome'] in HOME_HEROES]
    troops = split(raw.get('tropas'), BUILDER_TROOPS, SUPER_TROOPS)
    return {
        'jogador': {'nome': raw.get('nome'), 'tag': raw.get('tag'), 'centro_vila': raw.get('centro_vila')},
        'herois': heroes,
        'tropas': troops,
        'magias': [x for x in raw.get('magias', []) if isinstance(x, dict)],
        'limitacoes': [
            'API de perfil não fornece níveis de todos os edifícios nem melhorias em andamento.',
            'API de perfil não informa construtores livres nem recursos armazenados.',
            'Não interpretar supertropas como melhorias convencionais do laboratório.',
            'Níveis máximos dependem de atualizações e do nível do Salão dos Heróis.',
        ],
    }


def planning_evidence(normalized: dict, question: str) -> dict:
    """Resumo compacto e seletivo para o LLM; evita despejar dezenas de unidades."""
    q = question.casefold()
    focus_troops = any(word in q for word in ('tropa', 'exército', 'exercito', 'laboratório', 'laboratorio', 'ataque'))
    focus_spells = any(word in q for word in ('magia', 'feitiço', 'feitico'))
    return {
        'jogador': normalized['jogador'],
        'herois_vila_principal': normalized['herois']['vila_principal'],
        'herois_base_construtor': normalized['herois']['base_construtor'],
        'tropas_vila_principal': normalized['tropas']['vila_principal'][:30] if focus_troops else [],
        'magias': normalized['magias'][:20] if focus_spells else [],
        'contagens': {
            'tropas_vila_principal': len(normalized['tropas']['vila_principal']),
            'tropas_base_construtor': len(normalized['tropas']['base_construtor']),
            'supertropas': len(normalized['tropas']['especiais']),
        },
        'limitacoes': normalized['limitacoes'],
    }
