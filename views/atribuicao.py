import pandas as pd
import streamlit as st

import config
from components.cards import card
from components.header import secao_titulo
from components.print_button import area_com_print
from components.tabela_atribuicao import tabela_quadro, tabela_resumo_dias
from services.atribuicao import (
    ATIVIDADES_POR_HC, REGRAS, calcular_quadro, carregar_atividades, fora_do_quadro,
    hoje_local, recursos_sem_cadastro, rotulo_dia,
)


def _dd_mm(dia) -> str:
    return dia.strftime("%d/%m")


def _leg(titulo: str, data: str, hora: str) -> dict:
    """Legenda do "Copiar imagem". Aqui a data é a do(s) dia(s) planejado(s) — a aba não usa o
    filtro de Data do topo e olha só para o futuro, então não há "FECHAMENTO"."""
    return {
        "legenda_template": "{titulo} | {data} {hora}",
        "legenda_vars": {"titulo": titulo, "data": data, "hora_auto": hora},
    }


def render(df, indicadores):
    secao_titulo(
        "Atribuição",
        f"HC necessário para atender a demanda de hoje e dos próximos 2 dias "
        f"(1 técnico = {ATIVIDADES_POR_HC:g} atividades/dia)",
    )

    ativ = carregar_atividades()
    if ativ.empty:
        st.warning(
            "Ainda não há dados de Atribuição no banco. Rode o `atribuição.py` (baixa os arquivos do OFSC) "
            "e depois o `upload_atribuicao.py`."
        )
        return

    hoje = hoje_local()
    dias = sorted(d for d in ativ["dia"].unique() if d >= hoje)[:3]
    if not dias:
        st.warning(
            f"Os dados de Atribuição estão desatualizados (último dia carregado: "
            f"{max(ativ['dia']).strftime('%d/%m/%Y')}). Rode o `atribuição.py` e o `upload_atribuicao.py` de novo."
        )
        return

    ativ = ativ[ativ["dia"].isin(dias)]
    gerado = str(ativ["gerado_em"].max()) if "gerado_em" in ativ.columns else ""
    hora = gerado[-5:] if len(gerado) >= 5 else ""
    periodo = f"{_dd_mm(dias[0])} a {dias[-1].strftime('%d/%m/%Y')}" if len(dias) > 1 else dias[0].strftime("%d/%m/%Y")

    estado = st.radio("Estado", list(REGRAS), horizontal=True, key="atribuicao_estado")
    regra = REGRAS[estado]
    st.caption(
        f"Base gerada em {gerado or '—'} · Demanda = atividades de {', '.join(sorted(regra['contar_demanda']))} "
        f"por bucket · HC = técnicos TLP distintos com atividade no dia · HC NEC = demanda ÷ {ATIVIDADES_POR_HC:g} "
        f"(arredondado pra cima) · GAP = HC NEC − HC (positivo = faltam técnicos; negativo = sobra) · "
        f"ATRIB. = atividades por técnico. Nos dias futuros o HC ainda é baixo porque os técnicos "
        f"não foram todos alocados."
    )

    quadros = [(f"{rotulo_dia(d)} · {_dd_mm(d)}", calcular_quadro(ativ[ativ["dia"] == d], estado)) for d in dias]

    # --------------------------------------------------------------
    # Resumo: HC necessário por dia (cards) + por cluster (tabela)
    # --------------------------------------------------------------
    with area_com_print(
        f"atribuicao_resumo_{estado}", nome_arquivo=f"atribuicao_resumo_{estado}",
        **_leg(f"ATRIBUIÇÃO {estado} - HC NECESSÁRIO {rotulo_dia(dias[0])} A {rotulo_dia(dias[-1])}", periodo, hora),
    ):
        colunas = st.columns(len(quadros))
        for col, (rotulo, q) in zip(colunas, quadros):
            total = q.iloc[-1]
            gap = int(total["GAP"])
            with col:
                card(
                    f"HC necessário · {rotulo}", int(total["HC_NEC"]),
                    color=config.TLP_RED if gap > 0 else "#15803D",
                    subtitle=f"{int(total['TOTAL'])} atividades · HC atual {int(total['HC'])} · GAP {gap:+d}",
                    icon="🧑\u200d💼",
                )
        st.markdown("<br>", unsafe_allow_html=True)
        tabela_resumo_dias(quadros)

    # --------------------------------------------------------------
    # Detalhe por dia: bucket × horário
    # --------------------------------------------------------------
    secao_titulo("Detalhe por bucket", "Atividades por horário, HC atual, GAP e HC necessário")
    abas = st.tabs([rotulo for rotulo, _ in quadros])
    for aba, d, (rotulo, q) in zip(abas, dias, quadros):
        with aba:
            with area_com_print(
                f"atribuicao_quadro_{estado}_{d.isoformat()}", nome_arquivo=f"atribuicao_{estado}_{d.isoformat()}",
                **_leg(f"ATRIBUIÇÃO {rotulo_dia(d)} - {estado}", d.strftime("%d/%m/%Y"), hora),
            ):
                tabela_quadro(q)

    # --------------------------------------------------------------
    # Conferência: o que a conta deixa de fora (a planilha também deixava, em silêncio)
    # --------------------------------------------------------------
    with st.expander("Conferência dos dados (o que não entrou na conta)"):
        sem = recursos_sem_cadastro(ativ)
        if sem.empty:
            st.success("Todos os técnicos estão na tabela de Recursos.")
        else:
            st.warning(
                f"{len(sem)} técnico(s) sem cadastro em Recursos — as atividades deles NÃO entram na demanda. "
                "Inclua no `data/Mapeamento_Atribuicao.xlsx` (aba Recursos) e rode o upload de novo."
            )
            st.dataframe(sem.rename(columns={"recurso": "Recurso", "estado": "Estado", "atividades": "Atividades"}),
                         hide_index=True, use_container_width=True)

        for d in dias:
            fora = fora_do_quadro(ativ[ativ["dia"] == d], estado)
            if fora.empty:
                continue
            st.markdown(
                f"**{rotulo_dia(d)} · {_dd_mm(d)}** — {int(fora['atividades'].sum())} atividades que contam na demanda de "
                f"{estado}, mas caem num bucket que não aparece no quadro (cidade sem bucket cadastrado, ou bucket de outra regional):"
            )
            st.dataframe(fora.rename(columns={"bucket": "Bucket", "cidade": "Cidade", "atividades": "Atividades"}),
                         hide_index=True, use_container_width=True)
