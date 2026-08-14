"""
Estilo único de tabela usado em todo o site (Coordenadores, Produção por
Cluster, Análise P etc.). Centralizado aqui para não duplicar CSS entre
componentes e manter a mesma "cara" em todas as tabelas.
"""
import re
import unicodedata

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


def wrapper_tabela(conteudo_html: str, altura_max: int = None) -> str:
    """
    Moldura padrão (card branco, borda, sombra) em volta de qualquer tabela
    do site. Se `altura_max` (em px) for informado, a moldura ganha rolagem
    vertical própria (a tabela cresce por dentro dela, sem esticar a
    página) e o cabeçalho em degradê fica fixo (sticky) no topo enquanto o
    corpo rola — pensado pra tabelas que crescem com o tempo, como o
    fechamento diário do mês (uma linha a mais por dia) ou matrizes com
    muitos grupos abertos.
    """
    if altura_max:
        return (
            f"<div class='tlp-tabela-scroll' style='overflow:auto; max-height:{altura_max}px; "
            f"background:{config.CARD}; border:1px solid {config.CARD_BORDER}; "
            f"border-radius:10px; box-shadow:0 2px 14px rgba(20,20,30,0.08);'>{conteudo_html}</div>"
        )
    return (
        f"<div style='overflow-x:auto; background:{config.CARD}; border:1px solid {config.CARD_BORDER}; "
        f"border-radius:10px; box-shadow:0 2px 14px rgba(20,20,30,0.08);'>{conteudo_html}</div>"
    )


def sanitizar_id(texto: str) -> str:
    """Reduz qualquer string (nome de cluster, tabela etc.) a um identificador
    seguro pra usar como classe/id de HTML (minúsculo, sem acento, só
    letras/números/underscore) — usado nas tabelas expansíveis (Cluster ->
    Cidade) pra ligar a linha do Cluster às linhas de Cidade que ela
    abre/fecha."""
    sem_acento = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9_]+", "_", sem_acento).strip("_").lower() or "grupo"


def estilo_expansivel(cor_destaque: str = None) -> str:
    """
    `<style>` compartilhado pelas tabelas expansíveis (Cluster -> Cidade,
    ou Coordenador -> Supervisor -> Técnico).

    Reformulado pra resolver o "fundo laranja morto" que cobria TODAS as
    linhas internas por igual (o `!important` antigo em cima de uma cor
    quase transparente, que também apagava o zebrado branco/cinza que o
    Python já mandava pronto pra linha de Cidade): agora cada nível tem
    sua própria identidade —
      • Nível 1 (Cluster/Coordenador) aberto: realce em degrade de marca
        (vermelho -> laranja -> dourado) numa barra grossa à esquerda,
        igual ao "bar" usado no resto do site (`tlp-section-title`).
      • Nível 2, quando também é clicável (Supervisor, no caso de 3
        níveis): mesmo espírito, barra mais fina e tom mais suave, pra
        ficar visualmente "abaixo" do nível 1.
      • Nível-folha (Cidade final / Técnico): SEM tingir de laranja — fica
        no branco/cinza padrão do site (herda o zebrado que o Python já
        define quando existe; sem `!important` pra não brigar com ele),
        só com recuo/itálico marcando a profundidade.
      • Todas as linhas de detalhe ganham uma linha divisória vertical
        entre colunas em degradê de marca (não mais um azul genérico) —
        feita com `background-image` em vez de `border`, que é a forma
        confiável de desenhar um degradê em <td> mesmo com
        `border-collapse:collapse`.

    A classe `cluster-aberto` é ligada/desligada pelo próprio ativador de
    clique (`components/tabela_expansivel.py`).
    """
    cor = cor_destaque or config.TLP_ORANGE
    gradiente_marca = f"linear-gradient(180deg, {config.TLP_RED} 0%, {cor} 55%, {config.TLP_GOLD} 100%)"
    gradiente_suave = f"linear-gradient(180deg, {cor} 0%, {config.TLP_GOLD} 100%)"
    return (
        "<style>"
        # Divisória vertical em degradê entre colunas — em toda linha de
        # detalhe (cidade/supervisor/técnico), menos na 1ª coluna (nome).
        ".linha-cidade-expansivel td:not(:first-child){"
        f"background-image:{gradiente_marca}; background-repeat:no-repeat; "
        "background-position:left center; background-size:1.5px 62%;}"
        # Nível 1 (Cluster/Coordenador) aberto.
        f".linha-cluster-expansivel.cluster-aberto{{background:linear-gradient(90deg,{cor}29 0%,{cor}0F 65%,transparent 100%) !important;}}"
        ".linha-cluster-expansivel.cluster-aberto td:first-child{"
        f"background-image:{gradiente_marca}; background-repeat:no-repeat; "
        "background-position:left center; background-size:4px 100%; padding-left:16px !important;}"
        # Nível 2 clicável (Supervisor, nas tabelas de 3 níveis) — sempre
        # com um tapete leve pra se diferenciar da folha, mais forte
        # quando aberto.
        f".linha-cidade-expansivel.linha-cluster-expansivel{{background:{cor}0D !important;}}"
        f".linha-cidade-expansivel.linha-cluster-expansivel.cluster-aberto{{background:linear-gradient(90deg,{cor}22 0%,{cor}0A 65%,transparent 100%) !important;}}"
        ".linha-cidade-expansivel.linha-cluster-expansivel td:first-child{"
        f"background-image:{gradiente_suave}; background-repeat:no-repeat; "
        "background-position:left center; background-size:3px 100%; padding-left:12px !important;}"
        # Nível-folha (sem filhos, não clicável): sem tingir — fica no
        # branco/cinza padrão do site; sem !important pra deixar o
        # zebrado inline (quando o Python já manda um) prevalecer.
        f".linha-cidade-expansivel:not(.linha-cluster-expansivel){{background:{config.CARD};}}"
        "</style>"
    )