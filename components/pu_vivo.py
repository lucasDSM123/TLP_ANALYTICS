"""
Utilitário compartilhado para o toggle "Ver PU VIVO".

O PU VIVO é a réplica do cálculo de PU usado pelo Backoffice Regional Sul
(site da Vivo), obtida por engenharia reversa da base PRODUCAO_TLP_TRATADA
(coluna 'Peso'). Ver services/indicadores.py -> Indicadores.pu_vivo*() para
a fórmula.

Este módulo só cuida de UI: decidir se o comparativo deve aparecer (toggle
em session_state, ligado no components/filtros.py) e formatar o texto/estilo
da diferença entre o PU do nosso site e o PU Vivo.
"""

import streamlit as st


def pu_vivo_ativo() -> bool:
    """Retorna True quando o usuário marcou 'Ver PU VIVO' na barra de filtros."""
    return bool(st.session_state.get("mostrar_pu_vivo", False))


def texto_comparativo_pu(pu_site: float, pu_vivo_valor: float) -> str:
    """
    Monta o texto 'PU Vivo: X.XX (▲/▼ Y%)' comparando o PU do nosso site
    com o PU Vivo, para usar como subtítulo de card ou célula extra de
    tabela. Retorna string vazia se não houver base para comparar (ambos
    zerados).
    """
    if pu_site == 0 and pu_vivo_valor == 0:
        return ""
    if pu_site == 0:
        seta = ""
    else:
        diff_pct = (pu_vivo_valor - pu_site) / pu_site * 100
        seta = f" ({'▲' if diff_pct >= 0 else '▼'} {abs(diff_pct):.0f}%)"
    return f"PU Vivo: {pu_vivo_valor:.2f}{seta}"


def cor_comparativo_pu(pu_site: float, pu_vivo_valor: float) -> str:
    """Cor do texto comparativo: neutro se praticamente igual, senão sinaliza a diferença."""
    if abs(pu_vivo_valor - pu_site) < 0.02:
        return "#64748B"  # cinza neutro — praticamente igual
    return "#0369A1"  # azul — só informativo, não é bom/ruim (fórmulas diferentes)
