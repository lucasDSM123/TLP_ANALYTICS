import pandas as pd
import streamlit as st

from services import analise_indicador as ai

NENHUM = "Nenhum (ver tudo)"


def seletor_indicador_topo(df: pd.DataFrame, key: str = "indicador_ativo_topo"):
    """
    Barra de indicadores renderizada dentro de cada página que a utiliza
    (hoje: Dashboard e Relatórios). Cada página chama esta função no
    ponto em que quer o seletor, e o recorte resultante afeta apenas o
    conteúdo daquela página — não é mais compartilhado entre abas.

    Ao clicar em um indicador (Caixa Total, Concluído OK, Concluído NOK,
    Iniciada, Cancelada, Suspensa, Bucket, Esteira, HC Ativo, Eficácia,
    PU, Projeção), o conteúdo abaixo dele NA MESMA PÁGINA — cards,
    matrizes, tabelas e gráficos — passa a refletir aquele recorte,
    pois o `df` retornado já vem filtrado (igual ao comportamento de
    filtro cruzado dos cartões clicáveis do Power BI).

    Indicadores do tipo "contagem" (Caixa Total, Concluído OK, Iniciada,
    etc.) filtram as LINHAS da base (ex.: Concluído OK -> Status ==
    "Concluída"). Indicadores do tipo "taxa" (HC Ativo, Eficácia, PU,
    Projeção) não são um recorte de linhas — a base não é filtrada, mas
    o indicador continua "em foco" para a análise detalhada da
    Dashboard (quebra por cluster / ao longo do dia / dia a dia).

    Um botão "Limpar filtro" ao lado reseta a seleção para
    "Nenhum (ver tudo)", removendo o recorte por indicador (os demais
    filtros do topo — Data/Estado/Contratada/Cluster — continuam
    aplicados normalmente).

    Retorna: (df_ativo, chave_ativa, escolha, indicador_e_taxa)
    chave_ativa é None quando nenhum indicador está em foco.
    """
    label_to_key = {v["label"]: k for k, v in ai.INDICADORES.items()}
    labels = [NENHUM] + list(label_to_key.keys())

    col_sel, col_btn = st.columns([6, 1])

    with col_sel:
        escolha = st.segmented_control(
            "Indicador em foco — clique para filtrar os indicadores abaixo",
            options=labels,
            default=NENHUM,
            key=key,
        )

    with col_btn:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("🧹 Limpar filtro", width="stretch", key=f"{key}_limpar"):
            st.session_state.pop(key, None)
            st.rerun()

    if not escolha:
        escolha = NENHUM

    if escolha == NENHUM:
        st.caption("Nenhum indicador em foco — mostrando todos os dados dos filtros acima.")
        return df, None, escolha, False

    chave_ativa = label_to_key[escolha]
    meta_ativa = ai.INDICADORES[chave_ativa]

    if meta_ativa["tipo"] == "contagem":
        df_ativo = df[meta_ativa["filtro"](df)]
        st.caption(
            f"🔎 Filtro ativo: **{escolha}** — "
            f"{len(df_ativo):,} registro(s)".replace(",", ".")
        )
    else:
        df_ativo = df
        st.caption(
            f"📌 Indicador em foco: **{escolha}** "
            "(taxa/média — não filtra linhas; veja o detalhamento abaixo)"
        )

    return df_ativo, chave_ativa, escolha, meta_ativa["tipo"] == "taxa"
