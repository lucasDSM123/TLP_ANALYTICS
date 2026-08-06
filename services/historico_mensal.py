"""
Números CONGELADOS do fechamento de Julho/2026 (mês anterior já fechado),
extraídos do PAINEL do Excel/Power BI — usados como base de comparação
mês a mês na aba "Acumulado Mês" (Julho x Agosto/mês corrente).

Diferente do restante do site, esses valores NÃO são recalculados a partir
da base ao vivo: são uma "foto" fixa do mês fechado. O mês corrente
(Agosto e os que vierem depois) continua sendo calculado normalmente pelos
serviços existentes (services.grupos) a partir dos dados reais.

Quando um novo mês fechar, basta:
  1. Congelar os valores do mês corrente aqui (mover para um novo bloco,
     ex.: _AGOSTO_2026_ESTADO / _AGOSTO_2026_CLUSTER);
  2. Atualizar MES_REFERENCIA e as funções de lookup para apontar pro
     bloco mais recente.
"""

import unicodedata


def _normalizar(texto: str) -> str:
    """Normaliza nomes de Estado/Cluster para comparação robusta (maiúsculas,
    sem acento e sem espaços nas pontas) — a grafia exata usada na base ao
    vivo pode variar (ex.: 'Florianópolis' vs 'FLORIANOPOLIS')."""
    if texto is None:
        return ""
    sem_acento = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii")
    return sem_acento.strip().upper()


# Rótulo exibido nas tabelas de comparação (coluna da esquerda)
MES_REFERENCIA = "JULHO"

# Cada entrada: eficacia (fração 0-1), concluida, improdutiva, tecnicos
# (soma diária, mesma regra do site), atribuicao e pu (já divididos, 2 casas).

_JULHO_2026_ESTADO = {
    "SC": dict(eficacia=0.76, concluida=7768, improdutiva=2467, tecnicos=2560, atribuicao=4.00, pu=3.03),
    "RS": dict(eficacia=0.69, concluida=5877, improdutiva=2626, tecnicos=1883, atribuicao=4.52, pu=3.12),
}

_JULHO_2026_CLUSTER = {
    "FLORIANOPOLIS": dict(eficacia=0.78, concluida=2796, improdutiva=804, tecnicos=923, atribuicao=3.90, pu=3.03),
    "BLUMENAU":       dict(eficacia=0.74, concluida=1977, improdutiva=697, tecnicos=634, atribuicao=4.22, pu=3.12),
    "JOINVILLE":      dict(eficacia=0.75, concluida=2561, improdutiva=876, tecnicos=807, atribuicao=4.26, pu=3.17),
    "LAGES":          dict(eficacia=0.86, concluida=101,  improdutiva=17,  tecnicos=35,  atribuicao=3.37, pu=2.89),
    "CHAPECO":        dict(eficacia=0.76, concluida=333,  improdutiva=104, tecnicos=134, atribuicao=3.26, pu=2.49),
    "PORTO ALEGRE":   dict(eficacia=0.66, concluida=4096, improdutiva=2097, tecnicos=1379, atribuicao=4.49, pu=2.97),
    "CANOAS":         dict(eficacia=0.77, concluida=1781, improdutiva=529, tecnicos=536, atribuicao=4.31, pu=3.32),
}


def fechamento_mes_anterior(nome_grupo: str, coluna_grupo: str = "Cluster") -> dict | None:
    """
    Retorna o fechamento congelado do mês anterior (Julho/2026) para um
    Estado ou Cluster pelo nome, ou None se não houver referência
    cadastrada para esse nome (ex.: cluster novo, sem histórico ainda —
    nesse caso a comparação simplesmente não é exibida para o grupo).
    """
    tabela = _JULHO_2026_ESTADO if coluna_grupo == "Estado" else _JULHO_2026_CLUSTER
    chave = _normalizar(nome_grupo)
    for nome, valores in tabela.items():
        if _normalizar(nome) == chave:
            return dict(valores)
    return None
