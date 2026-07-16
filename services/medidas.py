# %%
import pandas as pd
import os

df = pd.read_excel('data/PRODUCAO_TLP_TRATADA.xlsx', engine='openpyxl')

# %%
df.columns

# %%

# calculando MSK
msk_count = df.loc[df["Perfil Técnico"] == "MSK", "Técnico"].nunique()

# garantir que não seja None
MSK = msk_count if pd.notnull(msk_count) else 0
MSK

# %% [markdown]
# 

# %%
# calculando BA
ba_count = df.loc[df["Perfil Técnico"] == "BA", "Técnico"].nunique()
BA = ba_count if pd.notnull(ba_count) else 0
BA

# %%
# calculando TT
tt_count = df.loc[df["Perfil Técnico"] == "TT", "Técnico"].nunique()
TT = tt_count if pd.notnull(tt_count) else 0
TT

# %%
# Filtrar contratada = "BUCKET TLP" e status diferente de "Cancelada"
df_bucket = df.loc[(df["Contratada"] == "BUCKET TLP")
                   & (df["Status"] != "Cancelada")]

# Contar registros
bucket = df_bucket["Contratada"].count()

# Garantir que não seja None
BUCKET = bucket if pd.notnull(bucket) else 0
print(BUCKET)

# %%
# calculando bucket BA
BUCKET_BA = df_bucket.loc[df_bucket["Lado"] == "BA", "Contratada"].nunique()
BUCKET_BA

# %%
# calculando bucket TT
BUCKET_TT = df_bucket.loc[df_bucket["Lado"] == "TT", "Contratada"].nunique()
BUCKET_TT

# %%
import math
# calculando BA_REAL
# Filtrar apenas contratada = "TLP"
df_tlp = df.loc[df["Contratada"] == "TLP"]

# Calcular MSK e BA apenas dentro desse subconjunto
msk_tlp = df_tlp.loc[df_tlp["Perfil Técnico"] == "MSK", "Técnico"].nunique()
ba_tlp = df_tlp.loc[df_tlp["Perfil Técnico"] == "BA", "Técnico"].nunique()

# Fórmula final com subtração do BUCKET BA
BA_REAL = math.floor((msk_tlp / 2) + ba_tlp)
BA_REAL

# %%
# calculando TT_REAL
# Filtrar apenas contratada = "TLP"
df_tlp = df.loc[df["Contratada"] == "TLP"]

# Calcular MSK e BA apenas dentro desse subconjunto
msk_tlp = df_tlp.loc[df_tlp["Perfil Técnico"] == "MSK", "Técnico"].nunique()
ba_tlp = df_tlp.loc[df_tlp["Perfil Técnico"] == "TT", "Técnico"].nunique()

# Aplicar a fórmula com arredondamento para baixo
TT_REAL = math.floor((msk_tlp / 2) + ba_tlp)
TT_REAL

# %%
# calculando HC ATIVO
HC_ATIVO = BA_REAL + TT_REAL
HC_ATIVO

# %%
# SUSPENSA
suspensa = df.loc[df["Status"] == "Suspensa", "Status"].count()
print(suspensa)

# %%
# CANCELADA
cancelada = df.loc[df["Status"] == "Cancelada", "Status"].count()
print(cancelada)

# %%
# Contagem total de atividades
total_atividades = df["Tipo de Atividade"].count()

# Fórmula final
caixa_total = total_atividades - suspensa - cancelada
print(caixa_total)

# %%
# Função auxiliar para calcular CAIXA TOTAL dentro de um subconjunto
def calcular_caixa_total(df_subset):
    total_atividades = df_subset["Tipo de Atividade"].count()
    suspensa = df_subset.loc[df_subset["Status"]
                             == "Suspensa", "Status"].count()
    cancelada = df_subset.loc[df_subset["Status"]
                              == "Cancelada", "Status"].count()
    return total_atividades - suspensa - cancelada


# CAIXA TOT BA
df_ba = df.loc[df["Lado"] == "BA"]
CAIXA_TOT_BA = calcular_caixa_total(df_ba)

# CAIXA TOT TT
df_tt = df.loc[df["Lado"] == "TT"]
CAIXA_TOT_TT = calcular_caixa_total(df_tt) if not df_tt.empty else 0
print(CAIXA_TOT_BA)
print(CAIXA_TOT_TT)

# %%
# SOBRA DE ESTEIRA R2
sobra_esteira_r2 = df.loc[df["CAUSA"] == "SOBRA DE ESTEIRA", "CAUSA"].count()
print(sobra_esteira_r2)

# %%
# Contagem de registros com Esteira = "ESTEIRA"
esteira_count = df.loc[df["Esteira"] == "ESTEIRA", "Esteira"].count()

# BUCKET já calculado anteriormente
# SOBRA DE ESTEIRA R2 já calculado anteriormente

# Fórmula final
ESTEIRA = (esteira_count - BUCKET) + sobra_esteira_r2
print(ESTEIRA)

# %%
# Função auxiliar para calcular ESTEIRA dentro de um subconjunto
def calcular_esteira(df_subset):
    # Contagem de registros com Esteira = "ESTEIRA"
    esteira_count = df_subset.loc[df_subset["Esteira"]
                                  == "ESTEIRA", "Esteira"].count()

    # BUCKET dentro do filtro (Contratada = "BUCKET TLP" e Status != "Cancelada")
    bucket = df_subset.loc[(df_subset["Contratada"] == "BUCKET TLP") & (
        df_subset["Status"] != "Cancelada"), "Contratada"].count()

    # SOBRA DE ESTEIRA R2 dentro do filtro
    sobra_esteira_r2 = df_subset.loc[df_subset["CAUSA"]
                                     == "SOBRA DE ESTEIRA", "CAUSA"].count()

    return (esteira_count - bucket) + sobra_esteira_r2


# Filtrar apenas Lado = "BA"
df_ba = df.loc[df["Lado"] == "BA"]

# Calcular ESTEIRA BA
ESTEIRA_BA = calcular_esteira(df_ba) if not df_ba.empty else 0
print(ESTEIRA_BA)

# %%
# Função auxiliar para calcular ESTEIRA dentro de um subconjunto
def calcular_esteira(df_subset):
    # Contagem de registros com Esteira = "ESTEIRA"
    esteira_count = df_subset.loc[df_subset["Esteira"]
                                  == "ESTEIRA", "Esteira"].count()

    # BUCKET dentro do filtro (Contratada = "BUCKET TLP" e Status != "Cancelada")
    bucket = df_subset.loc[(df_subset["Contratada"] == "BUCKET TLP") & (
        df_subset["Status"] != "Cancelada"), "Contratada"].count()

    # SOBRA DE ESTEIRA R2 dentro do filtro
    sobra_esteira_r2 = df_subset.loc[df_subset["CAUSA"]
                                     == "SOBRA DE ESTEIRA", "CAUSA"].count()

    return (esteira_count - bucket) + sobra_esteira_r2


# Filtrar apenas Lado = "BA"
df_ba = df.loc[df["Lado"] == "TT"]

# Calcular ESTEIRA BA
ESTEIRA_TT = calcular_esteira(df_ba) if not df_ba.empty else 0
print(ESTEIRA_TT)

# %%
# CONCLUIDO OK
concluido_ok = df.loc[df["Status"] == "Concluída", "Status"].count()

# Garantir comportamento do COALESCE
CONCLUIDO_OK = concluido_ok if pd.notnull(concluido_ok) else 0
print(CONCLUIDO_OK)

# %%
# CONCLUIIDO NOK
concluido_ok = df.loc[df["Status"] == "Não Concluída", "Status"].count()

# Garantir comportamento do COALESCE
CONCLUIDO_NOK = concluido_ok if pd.notnull(concluido_ok) else 0
print(CONCLUIDO_NOK)

# %%
# CONCLUIIDO GERAL
CONCLUIIDO_GERAL = CONCLUIDO_OK + CONCLUIDO_NOK
print(CONCLUIIDO_GERAL)

# %%
# EFICACIA
if CONCLUIDO_OK == 0 and CONCLUIDO_NOK == 0:
    EFICACIA = 1.0
else:
    EFICACIA = CONCLUIDO_OK / (CONCLUIDO_OK + CONCLUIDO_NOK)

EFICACIA_FORMATADA = f"{EFICACIA:.2f}"
print(EFICACIA_FORMATADA)

# %%
def calcular_eficacia(df_subset):
    concluido_ok = df_subset.loc[df_subset["Status"]
                                 == "Concluída", "Status"].count()
    concluido_nok = df_subset.loc[df_subset["Status"]
                                  == "Não Concluída", "Status"].count()

    if concluido_ok == 0 and concluido_nok == 0:
        return 1
    else:
        return concluido_ok / (concluido_ok + concluido_nok)


# Filtrar apenas BA
df_ba = df.loc[df["BA-TT-Real"] == "BA"]

# Filtrar apenas BA
df_ba = df.loc[df["BA-TT-Real"] == "BA"]

EFICACIA_BA = calcular_eficacia(df_ba) if not df_ba.empty else 1
EFICACIA_BA_FORMATADA = f"{EFICACIA_BA:.2f}"

print(EFICACIA_BA_FORMATADA)

# Filtrar apenas TT
df_tt = df.loc[df["BA-TT-Real"] == "TT"]

EFICACIA_TT = calcular_eficacia(df_tt) if not df_tt.empty else 1
EFICACIA_TT_FORMATADA = f"{EFICACIA_TT:.2f}"

print(EFICACIA_TT_FORMATADA)

print(EFICACIA_BA)

# %%
# Função auxiliar para calcular EFICACIA dentro de um subconjunto
def calcular_eficacia(df_subset):
    concluido_ok = df_subset.loc[df_subset["Status"]
                                 == "Concluída", "Status"].count()
    concluido_nok = df_subset.loc[df_subset["Status"]
                                  == "Não Concluída", "Status"].count()

    if concluido_ok == 0 and concluido_nok == 0:
        return 1
    else:
        return concluido_ok / (concluido_ok + concluido_nok)


# Filtrar apenas TT
df_tt = df.loc[df["BA-TT-Real"] == "TT"]

# Calcular EFICACIA TT
EFICACIA_TT = calcular_eficacia(df_tt) if not df_tt.empty else 1
EFICACIA_TT = format(EFICACIA_TT, '.2f')  # Formata para duas casas decimais
print(EFICACIA_TT)

# %%
# MÉDIA ATRIBUIÇÃO
if HC_ATIVO == 0:
    MEDIA_ATRIBUICAO = 0  # evita divisão por zero
else:
    MEDIA_ATRIBUICAO = caixa_total / HC_ATIVO
# Formata para duas casas decimais
MEDIA_ATRIBUICAO = format(MEDIA_ATRIBUICAO, '.2f')

print(MEDIA_ATRIBUICAO)

# %%
# Função auxiliar para calcular MÉDIA ATRIBUIÇÃO dentro de um subconjunto
def calcular_media_atribuicao(df_subset):
    # CAIXA TOTAL dentro do filtro
    total_atividades = df_subset["Tipo de Atividade"].count()
    suspensa = df_subset.loc[df_subset["Status"]
                             == "Suspensa", "Status"].count()
    cancelada = df_subset.loc[df_subset["Status"]
                              == "Cancelada", "Status"].count()
    caixa_total = total_atividades - suspensa - cancelada

    # HC ATIVO dentro do filtro
    msk_tlp = df_subset.loc[(df_subset["Contratada"] == "TLP") & (
        df_subset["Perfil Técnico"] == "MSK"), "Técnico"].nunique()
    ba_tlp = df_subset.loc[(df_subset["Contratada"] == "TLP") & (
        df_subset["Perfil Técnico"] == "BA"), "Técnico"].nunique()
    tt_tlp = df_subset.loc[(df_subset["Contratada"] == "TLP") & (
        df_subset["Perfil Técnico"] == "TT"), "Técnico"].nunique()

    BA_REAL = math.floor((msk_tlp / 2) + ba_tlp)
    TT_REAL = math.floor((msk_tlp / 2) + tt_tlp)
    HC_ATIVO = BA_REAL + TT_REAL

    # Fórmula final
    return 0 if HC_ATIVO == 0 else caixa_total / HC_ATIVO


# MÉDIA ATRIB. BA
df_ba = df.loc[df["BA-TT-Real"] == "BA"]
MEDIA_ATRIB_BA = calcular_media_atribuicao(df_ba) if not df_ba.empty else 0
# Formata para duas casas decimais
MEDIA_ATRIB_BA = format(MEDIA_ATRIB_BA, '.2f')
print(MEDIA_ATRIB_BA)
# MÉDIA ATRIB. TT
df_tt = df.loc[df["BA-TT-Real"] == "TT"]
MEDIA_ATRIB_TT = calcular_media_atribuicao(df_tt) if not df_tt.empty else 0
# Formata para duas casas decimais
MEDIA_ATRIB_TT = format(MEDIA_ATRIB_TT, '.2f')
print(MEDIA_ATRIB_TT)

# %%
# INICIADA
iniciada_count = df.loc[df["Status"] == "Iniciada", "Status"].count()

# Garantir comportamento do COALESCE
INICIADA = iniciada_count if pd.notnull(iniciada_count) else 0
print(INICIADA)

# %%
# Função auxiliar para calcular INICIADA dentro de um subconjunto
def calcular_iniciada(df_subset):
    iniciada_count = df_subset.loc[df_subset["Status"]
                                   == "Iniciada", "Status"].count()
    return iniciada_count if pd.notnull(iniciada_count) else 0


# INICIADA BA
df_ba = df.loc[df["Lado"] == "BA"]
INICIADA_BA = calcular_iniciada(df_ba) if not df_ba.empty else 0
print(INICIADA_BA)

# INICIADA TT
df_tt = df.loc[df["Lado"] == "TT"]
INICIADA_TT = calcular_iniciada(df_tt) if not df_tt.empty else 0
print(INICIADA_TT)

# %%
# PROJECAO
if CONCLUIDO_OK == 0:
    PROJECAO = ESTEIRA
else:
    PROJECAO = (ESTEIRA * EFICACIA) + CONCLUIDO_OK
PROJECAO = int(PROJECAO)  # Convertendo para inteiro

print(PROJECAO)

# %%
import math

# Função auxiliar para calcular PROJECAO dentro de um subconjunto


def calcular_projecao(df_subset):
    concluido_ok = df_subset.loc[df_subset["Status"]
                                 == "Concluída", "Status"].count()
    esteira_count = df_subset.loc[df_subset["Esteira"]
                                  == "ESTEIRA", "Esteira"].count()
    bucket = df_subset.loc[(df_subset["Contratada"] == "BUCKET TLP") & (
        df_subset["Status"] != "Cancelada"), "Contratada"].count()
    sobra_esteira_r2 = df_subset.loc[df_subset["CAUSA"]
                                     == "SOBRA DE ESTEIRA", "CAUSA"].count()

    ESTEIRA = (esteira_count - bucket) + sobra_esteira_r2

    concluido_nok = df_subset.loc[df_subset["Status"]
                                  == "Não Concluída", "Status"].count()
    EFICACIA = 1 if (concluido_ok == 0 and concluido_nok ==
                     0) else concluido_ok / (concluido_ok + concluido_nok)

    if concluido_ok == 0:
        return ESTEIRA
    else:
        return (ESTEIRA * EFICACIA) + concluido_ok


# PROJEÇÃO BA (arredondamento para baixo)
df_ba = df.loc[df["Lado"] == "BA"]
PROJECAO_BA = math.floor(calcular_projecao(df_ba)) if not df_ba.empty else 0
print(PROJECAO_BA)

# PROJEÇÃO TT (arredondamento para cima)
df_tt = df.loc[df["Lado"] == "TT"]
PROJECAO_TT = math.ceil(calcular_projecao(df_tt)) if not df_tt.empty else 0
print(PROJECAO_TT)

# %%
# PU
PU = 0 if HC_ATIVO == 0 else CONCLUIDO_OK / HC_ATIVO
PU = format(PU, '.2f')  # Formata para duas casas decimais
print(PU)

# %%
# Função auxiliar para calcular PU dentro de um subconjunto
def calcular_pu(df_subset):
    concluido_ok = df_subset.loc[df_subset["Status"]
                                 == "Concluída", "Status"].count()

    # HC ATIVO dentro do filtro
    msk_tlp = df_subset.loc[(df_subset["Contratada"] == "TLP") & (
        df_subset["Perfil Técnico"] == "MSK"), "Técnico"].nunique()
    ba_tlp = df_subset.loc[(df_subset["Contratada"] == "TLP") & (
        df_subset["Perfil Técnico"] == "BA"), "Técnico"].nunique()
    tt_tlp = df_subset.loc[(df_subset["Contratada"] == "TLP") & (
        df_subset["Perfil Técnico"] == "TT"), "Técnico"].nunique()

    BA_REAL = math.floor((msk_tlp / 2) + ba_tlp)
    TT_REAL = math.floor((msk_tlp / 2) + tt_tlp)
    HC_ATIVO = BA_REAL + TT_REAL

    return 0 if HC_ATIVO == 0 else concluido_ok / HC_ATIVO


# PU BA
df_ba = df.loc[df["BA-TT-Real"] == "BA"]
PU_BA = calcular_pu(df_ba) if not df_ba.empty else 0
PU_BA = format(PU_BA, '.2f')  # Formata para duas casas decimais
print(PU_BA)

# PU TT
df_tt = df.loc[df["BA-TT-Real"] == "TT"]
PU_TT = calcular_pu(df_tt) if not df_tt.empty else 0
PU_TT = format(PU_TT, '.2f')  # Formata para duas casas decimais
print(PU_TT)

# %%
# PROJECAO PU
PROJECAO_PU = 0 if HC_ATIVO == 0 else PROJECAO / HC_ATIVO
PROJECAO_PU = format(PROJECAO_PU, '.2f')  # Formata para duas casas decimais
print(PROJECAO_PU)

# %%
# Função auxiliar para calcular PROJECAO PU dentro de um subconjunto
def calcular_projecao_pu(df_subset):
    # CONCLUIDO OK / NOK
    concluido_ok = df_subset.loc[df_subset["Status"]
                                 == "Concluída", "Status"].count()
    concluido_nok = df_subset.loc[df_subset["Status"]
                                  == "Não Concluída", "Status"].count()

    # ESTEIRA
    esteira_count = df_subset.loc[df_subset["Esteira"]
                                  == "ESTEIRA", "Esteira"].count()
    bucket = df_subset.loc[(df_subset["Contratada"] == "BUCKET TLP") & (
        df_subset["Status"] != "Cancelada"), "Contratada"].count()
    sobra_esteira_r2 = df_subset.loc[df_subset["CAUSA"]
                                     == "SOBRA DE ESTEIRA", "CAUSA"].count()
    ESTEIRA = (esteira_count - bucket) + sobra_esteira_r2

    # EFICACIA
    EFICACIA = 1 if (concluido_ok == 0 and concluido_nok ==
                     0) else concluido_ok / (concluido_ok + concluido_nok)

    # PROJECAO
    PROJECAO = ESTEIRA if concluido_ok == 0 else (
        ESTEIRA * EFICACIA) + concluido_ok

    # HC ATIVO
    msk_tlp = df_subset.loc[(df_subset["Contratada"] == "TLP") & (
        df_subset["Perfil Técnico"] == "MSK"), "Técnico"].nunique()
    ba_tlp = df_subset.loc[(df_subset["Contratada"] == "TLP") & (
        df_subset["Perfil Técnico"] == "BA"), "Técnico"].nunique()
    tt_tlp = df_subset.loc[(df_subset["Contratada"] == "TLP") & (
        df_subset["Perfil Técnico"] == "TT"), "Técnico"].nunique()

    BA_REAL = math.floor((msk_tlp / 2) + ba_tlp)
    TT_REAL = math.floor((msk_tlp / 2) + tt_tlp)
    HC_ATIVO = BA_REAL + TT_REAL

    # PROJECAO PU
    return 0 if HC_ATIVO == 0 else PROJECAO / HC_ATIVO


# PROJ. PU BA
df_ba = df.loc[df["BA-TT-Real"] == "BA"]
PROJECAO_PU_BA = calcular_projecao_pu(df_ba) if not df_ba.empty else 0
# Formata para duas casas decimais
PROJECAO_PU_BA = format(PROJECAO_PU_BA, '.2f')
print(PROJECAO_PU_BA)

# PROJ. PU TT
df_tt = df.loc[df["BA-TT-Real"] == "TT"]
PROJECAO_PU_TT = calcular_projecao_pu(df_tt) if not df_tt.empty else 0
# Formata para duas casas decimais
PROJECAO_PU_TT = format(PROJECAO_PU_TT, '.2f')
print(PROJECAO_PU_TT)


