"""
Fixtures compartilhadas para a suite pytest do BluaDiagnostics.

Roda em todo arquivo `tests/test_*.py` automaticamente.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def maria_id() -> str:
    """ID do paciente canônico Maria (briefing Sprint 2)."""
    return "BNF-04821"


@pytest.fixture
def joao_id() -> str:
    """João — diabético tipo 2."""
    return "BNF-09732"


@pytest.fixture
def ana_id() -> str:
    """Ana — gestante 22 semanas."""
    return "BNF-15604"


@pytest.fixture
def paciente_inexistente_id() -> str:
    return "BNF-99999"


@pytest.fixture
def historico_maria_esperado() -> dict:
    """Subset esperado do histórico da Maria (para asserts mais limpos)."""
    return {
        "nome": "Maria",
        "idade": 34,
        "sexo": "F",
        "condicao_principal": "Hipertensão",
        "alergia_principal": "Dipirona",
        "medicacao_principal": "Losartana",
    }
