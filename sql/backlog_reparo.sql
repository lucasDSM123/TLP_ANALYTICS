-- =====================================================================
-- BACKLOG REPARO (BD) — tabelas do Neon
-- Fonte: relatório "Relatório de BD - Regional Sul" (site interno da Vivo)
-- Alimentadas por: upload_backlog_reparo.py
-- É seguro rodar este arquivo várias vezes (CREATE ... IF NOT EXISTS).
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1) FOTO ATUAL — uma linha por (tecnologia, empreiteira, cluster).
--    Cada coleta sobrescreve a linha anterior (upsert pela chave).
--    A linha com eh_total = true é o total da empreiteira (a linha "TLP"
--    do rodapé da tabela do site).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS backlog_reparo_atual (
    chave               text PRIMARY KEY,          -- tecnologia|empreiteira|cluster
    tecnologia          text        NOT NULL,      -- GPON | UGR | METALICO
    empreiteira         text        NOT NULL,      -- TLP | RS | VIVO | TLSV | ...
    cluster             text        NOT NULL,      -- nome do cluster (ou 'TOTAL')
    eh_total            boolean     NOT NULL DEFAULT false,
    coletado_em         timestamp   NOT NULL,      -- quando o script coletou (hora local)
    ultimo_bd_encerrado text,                      -- "HH:MM" mostrado no topo da tabela
    bd_historico_ate    date,                      -- data do último BD histórico encerrado

    -- ENCERRADOS: BD / TEC = PU
    enc_bd              integer,
    enc_tec             integer,
    enc_pu              double precision,

    -- BACKLOG por serviço: quantidade de BDs e backlog em dias
    voz_bd              integer,
    voz_dias            double precision,
    bl_bd               integer,                   -- banda larga
    bl_dias             double precision,
    tv_bd               integer,
    tv_dias             double precision,
    total_bd            integer,
    total_dias          double precision,

    tmr                 text,                      -- "HH:MM" como vem do site
    tmr_horas           double precision,          -- mesmo valor em horas decimais
    aberta_massiva      integer,
    massiva_analise     integer,
    total_geral         integer,                   -- total_bd + massivas
    pend_agend_reten    integer,

    -- OUTLIERS
    outl_total          integer,
    outl_pct            double precision,
    outl_5d             integer,
    outl_5d_pct         double precision,
    outl_10d            integer,
    outl_10d_pct        double precision,

    -- Distribuição do total (tooltip da coluna TOTAL do site)
    d0                  integer,
    d1                  integer,
    d2                  integer,
    d3_mais             integer,
    pend                integer,
    pend_agend          integer,
    retencao            integer,

    -- Colunas ocultas do site (TOTAL_VOZ / TOTAL_BANDA / TOTAL_TV).
    -- Parecem ser a produção dos últimos 6 dias úteis por serviço:
    -- dias = bd / (prod_6d / 6). Usadas para calcular a linha de total.
    prod_6d_voz         integer,
    prod_6d_bl          integer,
    prod_6d_tv          integer
);

CREATE INDEX IF NOT EXISTS ix_backlog_reparo_atual_filtro
    ON backlog_reparo_atual (tecnologia, empreiteira, coletado_em);

-- ---------------------------------------------------------------------
-- 2) HISTÓRICO DIÁRIO — uma linha por (tecnologia, empreiteira, cluster, dia).
--    Acumula para sempre (o site só mostra 8 dias na tabela e 30 no gráfico).
--    coef = média produtiva diária usada no cálculo; dias = bd / coef.
--    (sem coluna de data de coleta de propósito: assim o upsert só reescreve
--    os dias que de fato mudaram, em vez de todas as linhas a cada coleta.)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS backlog_reparo_historico (
    chave               text PRIMARY KEY,          -- tecnologia|empreiteira|cluster|AAAA-MM-DD
    tecnologia          text        NOT NULL,
    empreiteira         text        NOT NULL,
    cluster             text        NOT NULL,
    eh_total            boolean     NOT NULL DEFAULT false,
    data                date        NOT NULL,
    bd                  integer,
    dias                double precision,
    coef                double precision,
    fonte               text                       -- 'tabela' (8 dias) ou 'grafico' (backfill 30 dias)
);

CREATE INDEX IF NOT EXISTS ix_backlog_reparo_historico_filtro
    ON backlog_reparo_historico (tecnologia, empreiteira, data);

-- ---------------------------------------------------------------------
-- 3) FILA D0 CONGELADA — uma linha por (dia de referência, cluster).
--    Durante o dia, o site regrava (upsert) a tabela Fila D0 do dia atual.
--    Quando o dia vira, o último valor fica congelado: dias anteriores a hoje
--    só leem esta tabela, nunca recalculam (serve para conferir a projeção
--    "BDs/Fila amanhã" de ontem contra o backlog que realmente amanheceu).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS backlog_reparo_fila_d0 (
    data_ref    date NOT NULL,                -- dia ao qual a linha pertence (o "hoje" da época)
    cluster     text NOT NULL,                -- nome normalizado (FLORIANOPOLIS...)
    caixa       double precision,
    fila        double precision,
    ritmo       double precision,
    meta        double precision,
    gap         double precision,
    esteira     double precision,
    enc_bd      double precision,
    enc_tec     double precision,
    enc_pu      double precision,
    tt_atrib    double precision,
    tt_nok      double precision,
    tt_proj     double precision,
    ent_med     double precision,
    bd_amanha   double precision,
    fila_amanha double precision,
    gravado_em  timestamp,                    -- hora (Brasília) da última gravação
    PRIMARY KEY (data_ref, cluster)
);