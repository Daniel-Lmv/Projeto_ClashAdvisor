"""Catálogo enxuto e leitura sob demanda de habilidades do domínio."""
from .config import ROOT

SKILL_DESCRIPTIONS = {
    'analise_perfil': 'Interpretar o perfil oficial, separar dados confirmados de dados ausentes e propor verificações.',
    'planejamento': 'Organizar prioridades de evolução, validar limitações e ordenar ações de melhoria.'
}


def skill_catalog() -> str:
    """O catálogo mostra apenas nome e finalidade; não carrega a habilidade inteira."""
    return '\n'.join(f'- {name}: {description}' for name, description in SKILL_DESCRIPTIONS.items())


def load_skill(name: str) -> str:
    if name not in SKILL_DESCRIPTIONS:
        raise ValueError('Skill desconhecida')
    return (ROOT / 'skills' / name / 'SKILL.md').read_text(encoding='utf-8')
