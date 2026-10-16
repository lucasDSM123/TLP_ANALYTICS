import streamlit as st

import config
from components.cards import card
from components.charts import opcoes_grafico
from components.header import secao_titulo
from components.print_button import agora_local, area_com_print, legenda_filtros, sanitizar_chave
from components.tabela_backlog_reparo import (
    barra_titulo, grafico_historico, render_tabela_atual, render_tabela_fila_d0, render_tabela_historico,
)
from services.backlog_reparo import (
    carregar_atual, carregar_historico, clusters_permitidos, filtrar_clusters, filtrar_historico,
    historico_segmentado, montar_fila_d0, nome_cluster, ordenar_clusters, separar_atual, total_dos_clusters,
    DIAS_SEMANA, _chave_cluster, encerrados_tt_por_dia, entrante_medio_por_cluster,
    fila_d0_do_dia,
)
from services.loader import carregar_base
import pandas as pd

VERDE = "#15803D"
# A aba é só de reparo GPON da TLP — sem seletor de tecnologia/empreiteira.
TECNOLOGIA = "GPON"
EMPREITEIRA = "TLP"
DICA_BACKFILL = "Para trazer 30 dias de uma vez, rode `python upload_backlog_reparo.py --backfill`."


def _vazio(v) -> bool:
    return v is None or pd.isna(v)


def _int(v) -> str:
    return "–" if _vazio(v) else str(int(v))


def _dec(v, casas=2) -> str:
    return "–" if _vazio(v) else f"{float(v):.{casas}f}".replace(".", ",")


def _acima(v) -> bool:
    return not _vazio(v) and float(v) > config.META_BACKLOG_DIAS


def _fmt_dh(ts) -> str:
    return ts.strftime("%d/%m %H:%M") if hasattr(ts, "strftime") else ""


def _hora_vivo(v) -> str:
    """Normaliza o "H:MM"/"HH:MM" do relógio da Vivo para "HH:MM" ("" se não houver)."""
    if _vazio(v) or not str(v).strip():
        return ""
    h, _, m = str(v).strip().partition(":")
    return f"{int(h):02d}:{m}" if h.isdigit() and m else str(v).strip()


def _avisar_historico_curto(disponiveis: int, pedidos: int) -> None:
    """Quando há menos dias gravados do que a janela escolhida, explica por que nada muda."""
    if disponiveis < pedidos:
        st.caption(f"ℹ️ Só há {disponiveis} dias de histórico gravados — o restante vai sendo acumulado a cada "
                   f"coleta. {DICA_BACKFILL}")


def render(df, indicadores):
    secao_titulo(
        "Backlog Reparo",
        "BDs em aberto e backlog em dias por cluster · fonte: Relatório de BD — Regional Sul (Vivo)",
    )

    df_atual = carregar_atual()
    if df_atual.empty:
        st.warning(
            "Ainda não há dados de Backlog Reparo no Neon. Rode `python criar_tabela_backlog_reparo.py` "
            "e depois `python upload_backlog_reparo.py --backfill` (numa máquina com acesso à rede da Vivo)."
        )
        return

    tec, emp = TECNOLOGIA, EMPREITEIRA
    clusters, total = separar_atual(df_atual, tec, emp)
    if clusters.empty:
        st.info(f"Sem dados de {tec} / {emp} no Neon.")
        return

    # ---------------- segmentações do topo (Estado / Cluster) ----------------
    # `df` já vem filtrado por Data/Estado/Cluster; os clusters que sobraram nele definem o que
    # aparece nas tabelas do relatório da Vivo (que não tem a coluna Estado).
    permitidos = clusters_permitidos(df, st.session_state.get("filtro_sel_estado"),
                                     st.session_state.get("filtro_sel_cluster"))
    clusters = filtrar_clusters(clusters, permitidos)
    if clusters.empty:
        st.info("Nenhum cluster do relatório de Backlog Reparo para as segmentações escolhidas.")
        return
    total = total_dos_clusters(clusters, total, permitidos)

    coletado_em = clusters["coletado_em"].max()
    # Hora em que o relatório da Vivo foi atualizado (o relógio "15:30" do topo da tabela deles).
    # É diferente da hora da nossa coleta: o site pode ter coletado às 16:00 e a Vivo ainda
    # estar com os dados de 15:30.
    hora_vivo = _hora_vivo(clusters["ultimo_bd_encerrado"].iloc[0])
    st.markdown(
        f"<div style='color:{config.TEXT_MUTED}; font-size:13px; margin-bottom:8px;'>"
        f"Última coleta: <b style='color:{config.TEXT};'>{_fmt_dh(coletado_em)}</b>"
        + (f" &nbsp;·&nbsp; Atualizado na Vivo às <b style='color:{config.TEXT};'>{hora_vivo}</b>" if hora_vivo else "")
        + "</div>",
        unsafe_allow_html=True,
    )

    # Os blocos dinâmicos ficam em containers cuja chave muda junto com o conteúdo (filtro/janela):
    # o Streamlit recria o bloco do zero em vez de "remendar" o HTML antigo — evita o erro
    # 'removeChild' do React ao trocar a janela da tabela.
    sufixo = sanitizar_chave(f"{tec}_{emp}")

    # Legenda ao copiar imagem: Estado/Cluster do topo (Cidade/Coordenador ficam ocultos
    # nesta aba) + a hora da última coleta da Vivo, que é a "hora" real dos dados da aba.
    # A "hora" da legenda é a da atualização da Vivo (cai na coleta se a Vivo não informou).
    hora_legenda = hora_vivo or (f"{coletado_em:%H:%M}" if hasattr(coletado_em, "strftime") else None)

    def _leg(titulo, **kw):
        return legenda_filtros(titulo, ignorar=("cidade", "coordenador"), hora_auto=hora_legenda, **kw)

    # ---------------- cards ----------------
    if total:
        meta_txt = str(config.META_BACKLOG_DIAS).replace(".", ",")
        acima = _acima(total["total_dias"])
        with st.container(key=f"bl_cards_{sufixo}"):
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                card("Backlog (BDs)", _int(total["total_bd"]), "#2E63C7",
                     f"Total geral c/ massiva: {_int(total['total_geral'])}", icon="🛠️")
            with c2:
                card("Backlog em dias", _dec(total["total_dias"]),
                     config.TLP_RED if acima else VERDE, f"Meta ≤ {meta_txt} dia", icon="⏱️")
            with c3:
                card("Pend. agend. / reten.", _int(total["pend_agend_reten"]), config.TLP_GOLD,
                     f"{_int(total['pend_agend'])} agendamento · {_int(total['retencao'])} retenção", icon="📅")
            with c4:
                card("Outliers ≥ 5 dias", _int(total["outl_5d"]), config.TLP_RED,
                     f"{_dec(total['outl_5d_pct'], 1)}% do total geral", icon="🚨")
            with c5:
                card("TMR", total["tmr"] if not _vazio(total["tmr"]) else "–", config.TLP_ORANGE,
                     f"Massiva: {_int(total['aberta_massiva'])} aberta · {_int(total['massiva_analise'])} análise",
                     icon="🕒")
        st.markdown("<br>", unsafe_allow_html=True)

    # ---------------- tabela Fila D0 (caixa atual x meta + produção TT + projeção de amanhã) ----------------
    # Segue as mesmas segmentações: Data/Estado/Cluster filtram a produção (df) e Estado/Cluster
    # também filtram os clusters do relatório da Vivo.
    hist = historico_segmentado(filtrar_historico(carregar_historico(), tec, emp), permitidos)

    # Entrante médio de BDs no dia da semana de amanhã (usa a base completa, sem a segmentação de Data,
    # porque precisa dos encerrados de cada dia anterior).
    # O dia de referência é a Data marcada no filtro do topo (se marcou vários dias, vale o mais recente);
    # sem seleção, usa a data da última coleta. A projeção é sempre para o dia seguinte a essa referência.
    data_coleta = pd.Timestamp(coletado_em).normalize()
    sel_data = st.session_state.get("filtro_sel_data") or []
    datas_sel = pd.to_datetime(pd.Series(sel_data, dtype="object"), format="%d/%m/%Y", errors="coerce").dropna()
    hoje = datas_sel.max().normalize() if not datas_sel.empty else data_coleta
    amanha = hoje + pd.Timedelta(days=1)
    encerrados, datas_base = encerrados_tt_por_dia(carregar_base())
    # O backlog "agora" da Vivo só serve para completar o dia da própria coleta.
    bd_hoje = ({_chave_cluster(c): b for c, b in zip(clusters["cluster"], clusters["total_bd"])}
               if hoje == data_coleta else {})
    entrantes = entrante_medio_por_cluster(hist, encerrados, datas_base, hoje, bd_hoje, amanha.weekday())
    dia_amanha = DIAS_SEMANA[amanha.weekday()].upper()

    # Hoje = ao vivo (e gravado). Dia que já virou = linha congelada no fechamento; se não houver fechamento
    # gravado, é reconstruída pelo histórico (Caixa/Fila) e pela matriz TT (Encerrados).
    linhas_fila, total_fila, estado_fila, gravado_em = fila_d0_do_dia(
        clusters, df, entrantes, hist, hoje, data_coleta, len(datas_sel))
    # FILA D0 é de um dia de referência: hoje -> normal; dia que já virou -> FECHAMENTO.
    _dia_fechado = hoje.date() < agora_local().date()
    with area_com_print(
        "backlog_reparo_fila_d0", nome_arquivo="backlog_reparo_fila_d0",
        **_leg(f"BACKLOG REPARO {tec} - FILA D0", data=f"{hoje:%d/%m/%Y}", fechamento=_dia_fechado),
    ):
        with st.container(key=f"bl_fila_{sufixo}"):
            st.markdown(barra_titulo("FILA D0", []), unsafe_allow_html=True)
            render_tabela_fila_d0(linhas_fila, total_fila, emp, dia_amanha)
    if estado_fila == "congelado":
        st.caption(f"🔒 Linha congelada no fechamento de {hoje:%d/%m/%Y} (última atualização às {gravado_em:%H:%M}). "
                   f"Compare BDs/Fila de amanhã com o backlog real de {amanha:%d/%m/%Y} na tabela Histórico.")
    elif estado_fila == "reconstruido":
        st.caption(f"🧮 {hoje:%d/%m/%Y} não tinha fechamento gravado: Caixa e Fila vêm do histórico (backlog medido "
                   "no início da manhã), Encerrados vêm do OK / HC Ativo / PU da matriz Produção TT do dia, e "
                   "BDs/Fila de amanhã foram recalculados com esses valores.")
    elif estado_fila == "sem_registro":
        st.caption(f"ℹ️ Sem fechamento gravado nem histórico de backlog para {hoje:%d/%m/%Y}.")
    if entrantes:
        ocorr = [n for _, n in entrantes.values()]
        st.caption(f"ℹ️ Entrante médio de {dia_amanha}: média de {min(ocorr)}"
                   f"{'' if min(ocorr) == max(ocorr) else f' a {max(ocorr)}'} ocorrência(s) nos últimos 30 dias. "
                   "Entrante do dia = backlog do dia − (backlog do dia anterior − encerrados OK TT do dia anterior). "
                   "Os encerrados vêm da base de produção, que só guarda o mês corrente — por isso, no começo do mês, "
                   "há poucas ocorrências por dia da semana.")
    else:
        st.caption(f"ℹ️ Ainda não há histórico suficiente (backlog diário + encerrados do dia anterior) para "
                   f"calcular o entrante médio de {dia_amanha}.")
    if "Data" in df.columns:
        qtd_datas = pd.to_datetime(df["Data"], errors="coerce", dayfirst=True).dt.date.nunique()
        if qtd_datas > 1:
            st.caption(f"⚠️ A segmentação de Data está com {qtd_datas} dias: TT atribuído, NOK e Projeção TT "
                       "somam todos esses dias. Para ver o D0, selecione só a data de hoje.")
    st.markdown("<br>", unsafe_allow_html=True)

    # ---------------- tabela atual ----------------
    # Chips do título (entram na imagem copiada): hora da Vivo x hora da nossa coleta.
    chips = [("🕒 Atualizado na Vivo", hora_vivo),
             ("Coletado no site", f"{coletado_em:%H:%M}" if hasattr(coletado_em, "strftime") else "")]
    with area_com_print(
        "backlog_reparo_atual", nome_arquivo="backlog_reparo_atual",
        **_leg(f"BACKLOG REPARO {tec} - ATUAL", data=f"{data_coleta:%d/%m/%Y}",
               fechamento=data_coleta.date() < agora_local().date()),
    ):
        with st.container(key=f"bl_atual_{sufixo}"):
            render_tabela_atual(clusters, total, emp, chips)

    # ---------------- histórico ----------------
    st.markdown("<br>", unsafe_allow_html=True)
    secao_titulo("Histórico", "Backlog (BDs) e backlog em dias, dia a dia")

    if hist.empty:
        st.info(f"Ainda não há histórico gravado. {DICA_BACKFILL}")
        return

    dias_disponiveis = hist["data"].nunique()
    janela = st.radio("Janela da tabela", [7, 14, 30], horizontal=True, key="backlog_reparo_janela",
                      format_func=lambda d: f"Últimos {d} dias")
    _dias_tab = sorted(hist["data"].unique())[-janela:]
    with area_com_print(
        "backlog_reparo_historico", nome_arquivo="backlog_reparo_historico",
        **_leg(f"BACKLOG REPARO {tec} - HISTÓRICO ({janela} DIAS)", fechamento=False,
               data=f"{pd.Timestamp(_dias_tab[0]):%d/%m} a {pd.Timestamp(_dias_tab[-1]):%d/%m/%Y}"),
    ):
        with st.container(key=f"bl_hist_{sufixo}_{janela}"):
            render_tabela_historico(hist, janela, emp)
    _avisar_historico_curto(dias_disponiveis, janela)

    # ---------------- gráfico ----------------
    st.markdown("<br>", unsafe_allow_html=True)
    secao_titulo("Evolução do backlog",
                 "Barras = BDs e média produtiva · linha = backlog em dias (BD ÷ média produtiva)")

    nomes = {f"TOTAL {emp}": "TOTAL"}
    for c in ordenar_clusters(hist.loc[~hist["eh_total"], "cluster"]):
        nomes[nome_cluster(c)] = c
    col_cl, col_per, _ = st.columns([1.2, 1.4, 1.4])
    with col_cl:
        escolha = st.selectbox("Cluster", list(nomes), key="backlog_reparo_cluster")
    with col_per:
        periodo = st.radio("Período", [15, 30, 60], index=1, horizontal=True, key="backlog_reparo_periodo",
                           format_func=lambda d: f"{d} dias")

    serie = hist[hist["cluster"] == nomes[escolha]].sort_values("data").tail(periodo)
    if serie.empty:
        st.info("Sem histórico para este cluster.")
        return
    with area_com_print(
        "backlog_reparo_grafico", nome_arquivo="backlog_reparo_evolucao",
        **_leg(f"EVOLUÇÃO DO BACKLOG - {escolha} ({periodo} DIAS)", fechamento=False,
               data=f"{serie['data'].min():%d/%m} a {serie['data'].max():%d/%m/%Y}"),
    ):
        st.plotly_chart(grafico_historico(serie), width="stretch", config=opcoes_grafico("backlog_reparo_evolucao"))
    _avisar_historico_curto(hist.loc[hist["cluster"] == nomes[escolha], "data"].nunique(), periodo)