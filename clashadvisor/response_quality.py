"""Verificações determinísticas para erros observados na avaliação.

São guardrails conservadores de domínio, não um verificador universal de fatos.
"""
import re
import unicodedata


def fold(text: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', text.casefold()) if not unicodedata.combining(c))


# Não são edifícios melhoráveis do Clash of Clans; Salão dos Heróis é distinto.
_FAKE_BUILDING = re.compile(r'\blaboratorio\s+(?:de|das?|dos?)\s+(?:supertropas|super\s+tropas|herois)\b')
_DEFENSIVE_LAYOUTS = re.compile(
    r'\b(?:base\s+(?:de\s+(?:guerra|farm|trofeus)|anti\s*(?:3|tres)\s*estrelas|hibrida)|'
    r'layouts?\s+defensiv[oa]s?|layouts?\s+de\s+base)\b'
)
_ATTACK_INTENT = re.compile(r'\b(?:ataque|atacar|ofensiv[ao]|exercito|composic(?:ao|oes)|attack|army|armies)\b')


def unsupported_building(text: str) -> bool:
    return bool(_FAKE_BUILDING.search(fold(text)))


def unsafe_rag_claim(response: str, documents: list[dict], has_profile: bool = False) -> bool:
    """Detecta algumas afirmações de perfil e edifícios que não têm fonte.

    Não usa a pergunta do usuário como comprovação de níveis.
    """
    if unsupported_building(response):
        return True
    if has_profile:
        return False
    evidence = fold(' '.join(str(d.get('texto', '')) for d in documents))
    text = fold(response)
    # Níveis individuais de heróis da conta exigem confirmação da API/documentos.
    names = r'(?:rei barbaro|barbarian king|rainha arqueira|archer queen|grande guardiao|grand warden|minion prince|principe servo)'
    for match in re.finditer(rf'\b{names}\b[^\n.]{{0,65}}?\bnivel\s*(\d+)\b', text):
        if match.group(0) not in evidence:
            return True
    # Dados do exercício de construtores não são evidências para uma consulta RAG geral.
    if re.search(r'\b(?:6\s*,\s*4\s*e\s*2\s*horas|2\s+construtores|6\s+horas)\b', text):
        if not re.search(r'\b(?:6\s*,\s*4\s*e\s*2\s*horas|2\s+construtores|6\s+horas)\b', evidence):
            return True
    return False


def off_topic_attack_answer(response: str, question: str) -> bool:
    """Rejeita listas de layouts de defesa usadas como estratégias de ataque."""
    q = fold(question)
    if not _ATTACK_INTENT.search(q):
        return False
    body = fold(response)
    defensive = list(_DEFENSIVE_LAYOUTS.finditer(body))
    if len(defensive) >= 2:
        return True
    # Um ataque pode mencionar uma base de guerra como *alvo*; o erro é
    # listar tipos de base como se fossem composições de ataque.
    return bool(re.search(
        r'(?m)^\s*(?:\d+[.)]\s*|[-*]\s*|#{1,5}\s*)?\*{0,2}'
        r'(?:base\s+(?:de\s+(?:guerra|farm|trofeus)|anti\s*(?:3|tres)\s*estrelas|hibrida)|'
        r'layouts?\s+defensiv[oa]s?|layouts?\s+de\s+base)\*{0,2}\s*[:;,]',
        body,
    ))


def safe_invalid_building() -> str:
    return (
        'Não posso recomendar essa melhoria: **"Laboratório de Supertropas" não é uma '
        'construção melhorável comprovada do jogo** (o mesmo vale para "Laboratório de Heróis"). '
        'O nível declarado numa pergunta não é uma evidência do estado da vila. '
        'Para planejar melhorias, consulte os níveis reais do **Laboratório**, do **Salão dos Heróis** '
        'e dos edifícios no jogo; a API de perfil não informa todos esses dados.'
    )


def safe_rag_fallback(documents: list[dict], question: str = '') -> str:
    refs = ', '.join(sorted({str(d.get('fonte')) for d in documents if d.get('fonte')}))
    suffix = f' Documentos recuperados: {refs}.' if refs else ''
    general = ('Não consegui validar todas as afirmações da resposta gerada; por isso não vou '
               'atribuir níveis, tempos ou edifícios não comprovados à sua vila.')
    if re.search(r'\b(?:cv\s*12|th\s*12|centro\s+de\s+vila\s*12)\b', fold(question)):
        general += (' Como orientação geral para CV12, confira os heróis, o laboratório, '
                    'os acampamentos e o castelo do clã no jogo; depois escolha tropas e '
                    'magias para um exército principal. Sem níveis reais desses edifícios, '
                    'a prioridade é condicional.')
    return general + suffix


def safe_attack_fallback() -> str:
    return (
        'A busca encontrou referências sobre CV12, mas os trechos disponíveis não permitiram '
        'confirmar uma composição e uma sequência de **ataque** confiáveis. '
        'Não vou apresentar layouts de defesa como estratégias ofensivas. '
        'Consulte as fontes abaixo para verificar os ataques descritos.'
    )
