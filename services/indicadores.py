import math
import pandas as pd

from services.analise_p import classificacao_tecnicos, FAIXAS_P, matriz_analise_p_cluster


class Indicadores:
    """
    Réplica em Python das medidas DAX do Power BI (ver medidas_power_bi.pdf).

    Ponto importante: no Power BI, os cartões "BA" e "TT" de cada medida NÃO
    usam sempre a mesma coluna de segmentação:

    - CAIXA TOTAL, HC (perfil), ESTEIRA, BUCKET, INICIADA, CONCLUÍDO (OK/NOK)
      e PROJEÇÃO são segmentados pela coluna 'Lado'.
    - PU, EFICÁCIA, MÉDIA ATRIBUIÇÃO e PROJEÇÃO PU são segmentados pela
      coluna 'BA-TT-Real' (uma coluna diferente de 'Lado').

    Essa diferença de coluna era a principal causa da divergência do PU
    entre o site e o BI.
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def _to_int(self, val):
        """Converte numpy int para Python int"""
        return int(val) if val is not None else 0

    def _to_float(self, val):
        """Converte numpy float para Python float"""
        return float(val) if val is not None else 0.0

    # ------------------------------------------------------------------
    # HC / HC ATIVO
    # ------------------------------------------------------------------

    def hc(self):
        """Calcula HC por perfil técnico (MSK, BA, TT)"""
        return {
            "MSK": self._to_int(self.df.loc[self.df["Perfil Técnico"] == "MSK", "Técnico"].nunique()),
            "BA": self._to_int(self.df.loc[self.df["Perfil Técnico"] == "BA", "Técnico"].nunique()),
            "TT": self._to_int(self.df.loc[self.df["Perfil Técnico"] == "TT", "Técnico"].nunique())
        }

    def _hc_real_calc(self, df_scope):
        """
        Calcula BA REAL / TT REAL dentro de um escopo (df_scope), replicando:

        BA REAL = CALCULATE(ROUNDDOWN(([MSK]/2)+[BA],0),Contratada="TLP") - [BUCKET BA]
        TT REAL = CALCULATE(ROUNDUP(([MSK]/2)+[TT],0),Contratada="TLP") - [BUCKET TT]

        BUCKET BA/TT = BUCKET filtrado por Lado="BA"/"TT" dentro do mesmo escopo.
        """
        if df_scope.empty:
            return {"BA": 0, "TT": 0, "HC": 0}

        tlp = df_scope[df_scope["Contratada"] == "TLP"]
        msk_tlp = tlp.loc[tlp["Perfil Técnico"] == "MSK", "Técnico"].nunique()
        ba_tlp = tlp.loc[tlp["Perfil Técnico"] == "BA", "Técnico"].nunique()
        tt_tlp = tlp.loc[tlp["Perfil Técnico"] == "TT", "Técnico"].nunique()

        bucket_scope = df_scope[(df_scope["Contratada"] == "BUCKET TLP") & (df_scope["Status"] != "Cancelada")]
        bucket_ba = bucket_scope.loc[bucket_scope["Lado"] == "BA", "Contratada"].count()
        bucket_tt = bucket_scope.loc[bucket_scope["Lado"] == "TT", "Contratada"].count()

        # ROUNDDOWN -> floor | ROUNDUP -> ceil
        ba_real = math.floor(msk_tlp / 2 + ba_tlp)
        tt_real = math.ceil(msk_tlp / 2 + tt_tlp)

        return {"BA": self._to_int(ba_real), "TT": self._to_int(tt_real), "HC": self._to_int(ba_real + tt_real)}

    def hc_real(self):
        """HC ATIVO geral (cartão principal, sem segmentação adicional)."""
        return self._hc_real_calc(self.df)

    def _hc_ativo_scope(self, df_subset):
        """
        HC ATIVO calculado dentro de um subconjunto já filtrado por
        BA-TT-Real, replicando as medidas DAX:

        BA_REAL = ROUNDDOWN((MSK/2) + BA, 0)  -> floor
        TT_REAL = ROUNDUP((MSK/2) + TT, 0)    -> ceil
        HC_ATIVO = BA_REAL + TT_REAL
        """
        if df_subset.empty:
            return 0

        msk_tlp = df_subset.loc[(df_subset["Contratada"] == "TLP") & (df_subset["Perfil Técnico"] == "MSK"), "Técnico"].nunique()
        ba_tlp = df_subset.loc[(df_subset["Contratada"] == "TLP") & (df_subset["Perfil Técnico"] == "BA"), "Técnico"].nunique()
        tt_tlp = df_subset.loc[(df_subset["Contratada"] == "TLP") & (df_subset["Perfil Técnico"] == "TT"), "Técnico"].nunique()

        ba_real = math.floor((msk_tlp / 2) + ba_tlp)
        tt_real = math.ceil((msk_tlp / 2) + tt_tlp)
        return self._to_int(ba_real + tt_real)

    def hc_real_batt(self, valor):
        """
        HC ATIVO calculado dentro do contexto de filtro BA-TT-Real = valor
        ("BA" ou "TT"), usado pelas medidas PU / MÉDIA ATRIBUIÇÃO /
        PROJEÇÃO PU segmentadas (cards do topo).
        """
        df_scope = self.df[self.df["BA-TT-Real"] == valor]
        return self._hc_ativo_scope(df_scope)

    def hc_lado(self, lado):
        """
        HC ATIVO calculado dentro do contexto de filtro 'Lado' = lado
        ("BA" ou "TT"), usando SOMENTE o lado correspondente do cálculo
        (BA_REAL = ROUNDDOWN(MSK/2+BA,0) *ou* TT_REAL = ROUNDUP(MSK/2+TT,0),
        nunca a soma dos dois).

        Esta é a fórmula usada pela MATRIZ POR CLUSTER (tabelas "PRODUÇÃO
        BA"/"PRODUÇÃO TT") — diferente da usada pelos cards do topo
        (hc_real_batt, que segmenta por 'BA-TT-Real' e soma BA_REAL+TT_REAL).
        Confirmado batendo célula a célula com o Power BI.
        """
        df_scope = self.df[self.df["Lado"] == lado]
        if df_scope.empty:
            return 0
        tlp = df_scope[df_scope["Contratada"] == "TLP"]
        msk_tlp = tlp.loc[tlp["Perfil Técnico"] == "MSK", "Técnico"].nunique()
        lado_tlp = tlp.loc[tlp["Perfil Técnico"] == lado, "Técnico"].nunique()

        if lado == "BA":
            hc = math.floor(msk_tlp / 2 + lado_tlp)
        else:
            hc = math.ceil(msk_tlp / 2 + lado_tlp)
        return self._to_int(hc)

    def pu_lado(self, lado):
        """
        PU calculado dentro do contexto de filtro 'Lado' = lado, usando
        hc_lado(lado) como denominador. Usado pela MATRIZ POR CLUSTER.
        """
        df_scope = self.df[self.df["Lado"] == lado]
        if df_scope.empty:
            return 0.0
        ok_scope = (df_scope["Status"] == "Concluída").sum()
        hc_scope = self.hc_lado(lado)
        return self._to_float(0 if hc_scope == 0 else ok_scope / hc_scope)

    # ------------------------------------------------------------------
    # BUCKET
    # ------------------------------------------------------------------

    def bucket(self):
        """Calcula BUCKET: Contratada = BUCKET TLP e Status != Cancelada"""
        df_bucket = self.df.loc[(self.df["Contratada"] == "BUCKET TLP") & (self.df["Status"] != "Cancelada")]
        total = df_bucket["Contratada"].count()
        bucket_ba = df_bucket.loc[df_bucket["Lado"] == "BA", "Contratada"].count()
        bucket_tt = df_bucket.loc[df_bucket["Lado"] == "TT", "Contratada"].count()
        return {"TOTAL": self._to_int(total), "BA": self._to_int(bucket_ba), "TT": self._to_int(bucket_tt)}

    # ------------------------------------------------------------------
    # CAIXA TOTAL / ESTEIRA (segmentados por 'Lado')
    # ------------------------------------------------------------------

    def caixa_total(self):
        """Calcula CAIXA TOTAL: Total - Suspensa - Cancelada"""
        total_atividades = self.df["Tipo de Atividade"].count()
        suspensa = self.df.loc[self.df["Status"] == "Suspensa", "Status"].count()
        cancelada = self.df.loc[self.df["Status"] == "Cancelada", "Status"].count()
        total = total_atividades - suspensa - cancelada

        df_ba = self.df[self.df["Lado"] == "BA"]
        caixa_ba = self._calcular_caixa_subset(df_ba)

        df_tt = self.df[self.df["Lado"] == "TT"]
        caixa_tt = self._calcular_caixa_subset(df_tt)

        return {"TOTAL": self._to_int(total), "BA": self._to_int(caixa_ba), "TT": self._to_int(caixa_tt), "SUSPENSA": self._to_int(suspensa), "CANCELADA": self._to_int(cancelada)}

    def _calcular_caixa_subset(self, df_subset):
        if df_subset.empty:
            return 0
        total = df_subset["Tipo de Atividade"].count()
        suspensa = df_subset.loc[df_subset["Status"] == "Suspensa", "Status"].count()
        cancelada = df_subset.loc[df_subset["Status"] == "Cancelada", "Status"].count()
        return total - suspensa - cancelada

    def esteira(self):
        """Calcula ESTEIRA: (Esteira - Bucket) + Sobra de Esteira"""
        esteira_count = self.df.loc[self.df["Esteira"] == "ESTEIRA", "Esteira"].count()
        bucket_total = self.bucket()["TOTAL"]
        sobra = self.df.loc[self.df["CAUSA"] == "SOBRA DE ESTEIRA", "CAUSA"].count()
        total = (esteira_count - bucket_total) + sobra

        df_ba = self.df[self.df["Lado"] == "BA"]
        esteira_ba = self._calcular_esteira_subset(df_ba)

        df_tt = self.df[self.df["Lado"] == "TT"]
        esteira_tt = self._calcular_esteira_subset(df_tt)

        return {"TOTAL": self._to_int(total), "BA": self._to_int(esteira_ba), "TT": self._to_int(esteira_tt)}

    def _calcular_esteira_subset(self, df_subset):
        if df_subset.empty:
            return 0
        esteira_count = df_subset.loc[df_subset["Esteira"] == "ESTEIRA", "Esteira"].count()
        bucket = df_subset.loc[(df_subset["Contratada"] == "BUCKET TLP") & (df_subset["Status"] != "Cancelada"), "Contratada"].count()
        sobra = df_subset.loc[df_subset["CAUSA"] == "SOBRA DE ESTEIRA", "CAUSA"].count()
        return (esteira_count - bucket) + sobra

    # ------------------------------------------------------------------
    # CONCLUÍDO / INICIADA (segmentados por 'Lado')
    # ------------------------------------------------------------------

    def concluido(self):
        """Calcula CONCLUÍDO: OK, NOK e GERAL (segmentado por 'Lado')"""
        ok = (self.df["Status"] == "Concluída").sum()
        nok = (self.df["Status"] == "Não Concluída").sum()

        df_ba = self.df[self.df["Lado"] == "BA"]
        ok_ba = (df_ba["Status"] == "Concluída").sum()

        df_tt = self.df[self.df["Lado"] == "TT"]
        ok_tt = (df_tt["Status"] == "Concluída").sum()

        return {"OK": self._to_int(ok), "NOK": self._to_int(nok), "GERAL": self._to_int(ok + nok), "OK_BA": self._to_int(ok_ba), "OK_TT": self._to_int(ok_tt)}

    def _concluido_subset(self, df_subset):
        ok = (df_subset["Status"] == "Concluída").sum()
        nok = (df_subset["Status"] == "Não Concluída").sum()
        return self._to_int(ok), self._to_int(nok)

    def iniciada(self):
        """Calcula INICIADA (segmentado por 'Lado')"""
        total = self.df.loc[self.df["Status"] == "Iniciada", "Status"].count()
        df_ba = self.df[self.df["Lado"] == "BA"]
        iniciada_ba = df_ba.loc[df_ba["Status"] == "Iniciada", "Status"].count()
        df_tt = self.df[self.df["Lado"] == "TT"]
        iniciada_tt = df_tt.loc[df_tt["Status"] == "Iniciada", "Status"].count()
        return {"TOTAL": self._to_int(total), "BA": self._to_int(iniciada_ba), "TT": self._to_int(iniciada_tt)}

    # ------------------------------------------------------------------
    # PROJEÇÃO (segmentada por 'Lado')
    # ------------------------------------------------------------------

    def _eficacia_subset(self, ok, nok):
        if ok + nok == 0:
            return 1.0
        return ok / (ok + nok)

    def eficacia(self):
        """
        EFICÁCIA geral: OK / (OK + NOK) -- sem segmentação.
        EFICÁCIA BA/TT: segmentada por 'BA-TT-Real' (ver eficacia_batt).
        """
        dados = self.concluido()
        total = dados["OK"] + dados["NOK"]
        eficacia_geral = 1.0 if total == 0 else dados["OK"] / total

        eficacia_ba = self.eficacia_batt("BA")
        eficacia_tt = self.eficacia_batt("TT")

        return {"GERAL": self._to_float(eficacia_geral), "BA": self._to_float(eficacia_ba), "TT": self._to_float(eficacia_tt)}

    def eficacia_batt(self, valor):
        """EFICÁCIA dentro do contexto BA-TT-Real = valor."""
        df_scope = self.df[self.df["BA-TT-Real"] == valor]
        if df_scope.empty:
            return 1.0
        ok, nok = self._concluido_subset(df_scope)
        return self._to_float(self._eficacia_subset(ok, nok))

    def projecao(self):
        """Calcula PROJEÇÃO: (Esteira * Eficácia) + Concluído OK (segmentado por 'Lado')"""
        esteira = self.esteira()
        concluido = self.concluido()

        df_ba = self.df[self.df["Lado"] == "BA"]
        ok_ba, nok_ba = self._concluido_subset(df_ba)
        eficacia_ba_lado = self._eficacia_subset(ok_ba, nok_ba)

        df_tt = self.df[self.df["Lado"] == "TT"]
        ok_tt, nok_tt = self._concluido_subset(df_tt)
        eficacia_tt_lado = self._eficacia_subset(ok_tt, nok_tt)

        ok_geral, nok_geral = concluido["OK"], concluido["NOK"]
        eficacia_geral_lado = self._eficacia_subset(ok_geral, nok_geral)

        projecao_geral = esteira["TOTAL"] if concluido["OK"] == 0 else (esteira["TOTAL"] * eficacia_geral_lado) + concluido["OK"]

        projecao_ba = esteira["BA"] if concluido["OK_BA"] == 0 else (esteira["BA"] * eficacia_ba_lado) + concluido["OK_BA"]
        projecao_ba = math.floor(projecao_ba)

        projecao_tt = esteira["TT"] if concluido["OK_TT"] == 0 else (esteira["TT"] * eficacia_tt_lado) + concluido["OK_TT"]
        projecao_tt = math.ceil(projecao_tt)

        return {"GERAL": self._to_int(int(projecao_geral)), "BA": self._to_int(projecao_ba), "TT": self._to_int(projecao_tt)}

    # ------------------------------------------------------------------
    # PU / MÉDIA ATRIBUIÇÃO / PROJEÇÃO PU (segmentadas por 'BA-TT-Real')
    # ------------------------------------------------------------------

    def media_atribuicao(self):
        """
        MÉDIA ATRIBUIÇÃO geral: Caixa Total / HC Ativo (sem segmentação).
        MÉDIA ATRIB. BA/TT: segmentada por 'BA-TT-Real'.
        """
        caixa = self.caixa_total()
        hc = self.hc_real()
        media_geral = 0 if hc["HC"] == 0 else caixa["TOTAL"] / hc["HC"]

        media_ba = self.media_atribuicao_batt("BA")
        media_tt = self.media_atribuicao_batt("TT")

        return {"GERAL": self._to_float(media_geral), "BA": self._to_float(media_ba), "TT": self._to_float(media_tt)}

    def media_atribuicao_batt(self, valor):
        df_scope = self.df[self.df["BA-TT-Real"] == valor]
        if df_scope.empty:
            return 0.0
        caixa_scope = self._calcular_caixa_subset(df_scope)
        hc_scope = self._hc_ativo_scope(df_scope)
        return self._to_float(0 if hc_scope == 0 else caixa_scope / hc_scope)

    def pu(self):
        """
        PU geral: Concluído OK / HC Ativo (sem segmentação).
        PU BA/TT: segmentada por 'BA-TT-Real' -- é aqui que estava a
        divergência em relação ao BI (antes usava 'Lado').
        """
        concluido = self.concluido()
        hc = self.hc_real()
        pu_geral = 0 if hc["HC"] == 0 else concluido["OK"] / hc["HC"]

        pu_ba = self.pu_batt("BA")
        pu_tt = self.pu_batt("TT")

        return {"GERAL": self._to_float(pu_geral), "BA": self._to_float(pu_ba), "TT": self._to_float(pu_tt)}

    def pu_batt(self, valor):
        """PU dentro do contexto BA-TT-Real = valor (replica calcular_pu do medidas.py)."""
        df_scope = self.df[self.df["BA-TT-Real"] == valor]
        if df_scope.empty:
            return 0.0
        ok_scope = (df_scope["Status"] == "Concluída").sum()
        hc_scope = self._hc_ativo_scope(df_scope)
        return self._to_float(0 if hc_scope == 0 else ok_scope / hc_scope)

    def projecao_pu(self):
        """
        PROJEÇÃO PU geral: Projeção / HC Ativo (sem segmentação).
        PROJ. PU BA/TT: segmentada por 'BA-TT-Real'.
        """
        projecao = self.projecao()
        hc = self.hc_real()
        projecao_pu_geral = 0 if hc["HC"] == 0 else projecao["GERAL"] / hc["HC"]

        projecao_pu_ba = self.projecao_pu_batt("BA")
        projecao_pu_tt = self.projecao_pu_batt("TT")

        return {"GERAL": self._to_float(projecao_pu_geral), "BA": self._to_float(projecao_pu_ba), "TT": self._to_float(projecao_pu_tt)}

    def projecao_pu_batt(self, valor):
        """
        PROJEÇÃO PU dentro do contexto BA-TT-Real = valor.
        PROJECAO PU = DIVIDE([PROJECAO],[HC ATIVO]) -- ambos recalculados
        dentro do filtro BA-TT-Real = valor.
        """
        df_scope = self.df[self.df["BA-TT-Real"] == valor]
        if df_scope.empty:
            return 0.0

        esteira_scope = self._calcular_esteira_subset(df_scope)
        ok_scope, nok_scope = self._concluido_subset(df_scope)
        eficacia_scope = self._eficacia_subset(ok_scope, nok_scope)
        projecao_scope = esteira_scope if ok_scope == 0 else (esteira_scope * eficacia_scope) + ok_scope

        hc_scope = self._hc_ativo_scope(df_scope)
        return self._to_float(0 if hc_scope == 0 else projecao_scope / hc_scope)

    # ------------------------------------------------------------------
    # ANÁLISE P (QTD_P0 / QTD_P1 / QTD_P2 / QTD_P3 / QTD_MAIOR_P3)
    # ------------------------------------------------------------------

    def analise_p(self):
        """
        Réplica das medidas DAX QTD_P0..QTD_MAIOR_P3: quantidade de
        técnicos (com ao menos 1 atividade não Cancelada) classificados
        pela quantidade de atividades Concluídas.

        Escopo: apenas Contratada = "TLP" e excluindo Supervisor = "BUCKET"
        (técnicos do bucket não entram na análise de produtividade P0..>P3).
        """
        df_scope = self.df[self.df["Contratada"] == "TLP"]
        if "Supervisor" in df_scope.columns:
            df_scope = df_scope[df_scope["Supervisor"] != "BUCKET"]

        tabela = classificacao_tecnicos(df_scope)
        if tabela.empty:
            return {faixa: 0 for faixa in FAIXAS_P}

        contagem = tabela["Classificação"].value_counts()
        return {faixa: self._to_int(contagem.get(faixa, 0)) for faixa in FAIXAS_P}

    def analise_p_cluster(self, coluna_grupo: str = "Cluster"):
        """
        Réplica da tabela "Contagem por Cluster" / "Percentual por Cluster"
        do site de referência: faixas P0..P5/P≥6 agrupadas por Cluster,
        no mesmo escopo da Análise P (Contratada = "TLP", excluindo
        Supervisor = "BUCKET").

        Retorna (contagem_df, percentual_df, resumo), onde `resumo` traz
        os totais de TÉCNICOS P0 / TÉCNICOS P1 / TOTAL TÉCNICOS usados
        nos cards de cabeçalho.
        """
        df_scope = self.df[self.df["Contratada"] == "TLP"]
        if "Supervisor" in df_scope.columns:
            df_scope = df_scope[df_scope["Supervisor"] != "BUCKET"]

        contagem, percentual = matriz_analise_p_cluster(df_scope, coluna_grupo=coluna_grupo)
        if contagem.empty:
            resumo = {"P0": 0, "P1": 0, "TOTAL": 0}
        else:
            linha_total = contagem[contagem[coluna_grupo] == "Total Geral"].iloc[0]
            resumo = {
                "P0": self._to_int(linha_total["P0"]),
                "P1": self._to_int(linha_total["P1"]),
                "TOTAL": self._to_int(linha_total["TOTAL"]),
            }

        return contagem, percentual, resumo