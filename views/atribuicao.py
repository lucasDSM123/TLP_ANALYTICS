import pandas as pd
import streamlit as st

import config
from components.cards import card
from components.header import secao_titulo
from components.print_button import area_com_print
from components.tabela_atribuicao import tabela_quadro, tabela_resumo_dias
from services.atribuicao import (
    ATIVIDADES_POR_HC, REGRAS, atividades_da_zeus, calcular_quadro, carregar_atividades,
    carregar_mapeamento, combinar_fontes, fora_do_quadro, hoje_local, perfis_por_tecnico,
    recursos_sem_cadastro, rotulo_dia, tecnicos_sem_perfil,
)


@st.cache_data(show_spinner=False, ttl=300)
def _mapeamento():
    return carregar_mapeamento()


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

    # Hoje vem da base Zeus tratada (a mesma do Dashboard); os dias futuros vêm do OFSC.
    # `df` aqui é a base inteira, sem os filtros do topo.
    hoje = hoje_local()
    ofsc = carregar_atividades()
    zeus_ativ = atividades_da_zeus(df, _mapeamento())
    ativ = combinar_fontes(ofsc, zeus_ativ, perfis_por_tecnico(df), hoje)
    if ativ.empty:
        st.warning(
            "Ainda não há dados de Atribuição no banco. Rode o `atribuição.py` (baixa os arquivos do OFSC) "
            "e depois o `upload_atribuicao.py`."
        )
        return

    dias = sorted(d for d in ativ["dia"].unique() if d >= hoje)[:3]
    if not dias:
        st.warning(
            f"Os dados de Atribuição estão desatualizados (último dia carregado: "
            f"{max(ativ['dia']).strftime('%d/%m/%Y')}). Rode o `atribuição.py` e o `upload_atribuicao.py` de novo."
        )
        return

    ativ = ativ[ativ["dia"].isin(dias)]
    gerado = str(ofsc["gerado_em"].max()) if not ofsc.empty and "gerado_em" in ofsc.columns else ""
    fontes = ativ.groupby("dia")["fonte"].first().to_dict() if "fonte" in ativ.columns else {}
    dias_zeus = [rotulo_dia(d) for d in dias if fontes.get(d) == "Zeus"]
    hora = gerado[-5:] if len(gerado) >= 5 else ""
    periodo = f"{_dd_mm(dias[0])} a {dias[-1].strftime('%d/%m/%Y')}" if len(dias) > 1 else dias[0].strftime("%d/%m/%Y")

    estado = st.radio("Estado", list(REGRAS), horizontal=True, key="atribuicao_estado")
    regra = REGRAS[estado]
    st.caption(
        f"Base OFSC gerada em {gerado or '—'}" + (f" · {', '.join(dias_zeus)} pela base Zeus tratada (igual ao Dashboard)" if dias_zeus else "") + f" · Demanda = atividades de {', '.join(sorted(regra['contar_demanda']))} "
        f"por bucket · HC = HC ATIVO do Dashboard (técnicos TLP com Perfil Técnico: BA = ⌊MSK/2 + BA⌋, TT = ⌈MSK/2 + TT⌉) · HC NEC = demanda ÷ {ATIVIDADES_POR_HC:g} "
        f"(arredondado pra cima) · GAP = HC NEC − HC (positivo = faltam técnicos; negativo = sobra) · "
        f"ATRIB. = atividades por técnico. Nos dias futuros o HC ainda é baixo porque os técnicos "
        f"não foram todos alocados. Atividades canceladas e suspensas são ignoradas. As colunas são a Janela de Serviço da atividade (janela inteira, não só o início; "
        f"janela vazia ou fora do padrão entra em SLA). Nas linhas de bucket aparece só o nº de "
        f"atividades; nos totais, atividades / HC da janela = atividades por técnico e o GAP da janela "
        f"(atividades − HC, com 1 atividade por técnico por janela; positivo = faltam técnicos naquela janela)."
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
    secao_titulo("Detalhe por bucket", "Atividades por janela de serviço, HC atual, GAP e HC necessário")
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

        sem_perfil = tecnicos_sem_perfil(ativ[ativ["estado"] == estado])
        if not sem_perfil.empty:
            st.info(
                f"{len(sem_perfil)} técnico(s) TLP sem Perfil Técnico na base Zeus — o Dashboard não os conta no HC ATIVO, "
                "então a Atribuição também não (inclui recursos de bucket marcados como TLP):"
            )
            st.dataframe(sem_perfil.rename(columns={"recurso": "Recurso", "estado": "Estado", "atividades": "Atividades"}),
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