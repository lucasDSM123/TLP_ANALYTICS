"""
Estilo único de tabela usado em todo o site (Coordenadores, Produção por
Cluster, Análise P etc.). Centralizado aqui para não duplicar CSS entre
componentes e manter a mesma "cara" em todas as tabelas.
"""
import config

CABECALHO_BG = f"background:{config.HEADER_GRADIENT}; color:#FFFFFF;"
TOTAL_BG = f"background:{config.HEADER_GRADIENT}; border-top:3px solid {config.TLP_RED};"
SUBTOTAL_BG = f"background:rgba(255,106,0,0.12); border-top:2px solid {config.TLP_ORANGE};"


def pill(texto: str, cor_texto: str, cor_fundo: str, negrito: bool = True) -> str:
    """
    Badge/chip com fundo tingido claro. Usar em linhas de fundo claro
    (branco/cinza) — ex.: linhas normais das tabelas.
    """
    peso = "800" if negrito else "600"
    return (
        f"<span style='display:inline-block; min-width:44px; padding:3px 10px; "
        f"border-radius:8px; background:{cor_fundo}; color:{cor_texto}; font-weight:{peso};'>{texto}</span>"
    )


def pill_total(texto) -> str:
    """
    Balão branco opaco com texto preto em negrito — usado em TODAS as
    células numéricas das linhas de Total/Total Geral (uniformiza o
    visual: todo valor de total vira um "balão" de alto contraste, sem
    variar a cor por indicador).
    """
    return (
        "<span style='display:inline-block; min-width:44px; padding:3px 10px; "
        f"border-radius:8px; background:rgba(255,255,255,0.96); color:#111827; font-weight:800;'>{texto}</span>"
    )


def pill_contraste(texto: str, cor_texto: str) -> str:
    """
    Badge com fundo quase-branco opaco + texto colorido. Usar sempre que o
    número estiver sobre um fundo saturado (gradiente laranja/vermelho da
    linha de Total/Cabeçalho) — garante leitura mesmo com cores próximas
    (ex.: dourado ou salmão sobre laranja, que ficam "apagados" com texto
    solto sem fundo).
    """
    return (
        "<span style='display:inline-block; min-width:44px; padding:3px 10px; "
        f"border-radius:8px; background:rgba(255,255,255,0.94); color:{cor_texto}; font-weight:800;'>{texto}</span>"
    )


def pill_clara(texto: str) -> str:
    """Badge translúcido branco (texto sempre branco) — para valores neutros sobre fundo escuro/gradiente."""
    return (
        "<span style='display:inline-block; min-width:44px; padding:3px 10px; "
        f"border-radius:8px; background:rgba(255,255,255,0.20); color:#FFFFFF; font-weight:800;'>{texto}</span>"
    )


def cor_faixa(valor: float, bom: float, medio: float = None) -> str:
    """Verde se >= bom, dourado se >= medio (quando informado), vermelho caso contrário."""
    if valor >= bom:
        return "#15803D"
    if medio is not None and valor >= medio:
        return config.TLP_GOLD
    return config.TLP_RED


def cor_faixa_bg(valor: float, bom: float, medio: float = None) -> str:
    if valor >= bom:
        return "rgba(34,197,94,0.14)"
    if medio is not None and valor >= medio:
        return "rgba(255,176,32,0.16)"
    return "rgba(232,57,29,0.10)"


def wrapper_tabela(conteudo_html: str) -> str:
    """Moldura padrão (card branco, borda, sombra) em volta de qualquer tabela do site."""
    return (
        f"<div style='overflow-x:auto; background:{config.CARD}; border:1px solid {config.CARD_BORDER}; "
        f"border-radius:10px; box-shadow:0 2px 14px rgba(20,20,30,0.08);'>{conteudo_html}</div>"
    )