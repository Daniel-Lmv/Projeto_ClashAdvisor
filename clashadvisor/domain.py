import re

# Alfabeto de tags do Clash of Clans.
TAG_RE = re.compile(r'(?<!\w)#([0289PYLQGRJCUV]{5,})(?!\w)', re.I)


def extract_tag(text: str) -> str | None:
    match = TAG_RE.search(text)
    return '#' + match.group(1).upper() if match else None


def sanitize_tag(tag: str) -> str:
    found = extract_tag(tag.strip())
    if found is None or found != tag.strip().upper():
        raise ValueError('Tag de jogador inválida. Informe uma tag completa, como #P0Y8Q2.')
    return found


def calculate_builders(durations: list[float], builders: int) -> dict:
    if not isinstance(builders, int) or not 1 <= builders <= 6:
        raise ValueError('Quantidade de construtores deve estar entre 1 e 6.')
    if not durations or len(durations) > 30 or any(not isinstance(v, (int, float)) or not 0 < v <= 100000 for v in durations):
        raise ValueError('Informe de 1 a 30 durações positivas em horas.')
    loads = [0.0] * builders
    for duration in sorted(durations, reverse=True):
        idx = min(range(builders), key=lambda i: loads[i])
        loads[idx] += float(duration)
    return {'cargas_horas': loads, 'tempo_total_horas': max(loads), 'metodo': 'heurística LPT; não garante ótimo global'}
