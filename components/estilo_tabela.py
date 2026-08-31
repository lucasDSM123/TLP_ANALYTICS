"""
Estilo único de tabela usado em todo o site (Coordenadores, Produção por
Cluster, Análise P etc.). Centralizado aqui para não duplicar CSS entre
componentes e manter a mesma "cara" em todas as tabelas.
"""
import re
import unicodedata

import config

def CABECALHO_BG() -> str:
    return f"background:{config.HEADER_GRADIENT}; color:#FFFFFF;"


def TOTAL_BG() -> str:
    return f"background:{config.HEADER_GRADIENT}; border-top:3px solid {config.TLP_RED};"


def _hex_para_rgba(cor_hex: str, alpha: float) -> str:
    cor_hex = (cor_hex or "").lstrip("#")
    r, g, b = int(cor_hex[0:2], 16), int(cor_hex[2:4], 16), int(cor_hex[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def SUBTOTAL_BG() -> str:
    return f"background:{_hex_para_rgba(config.TLP_ORANGE, 0.12)}; border-top:2px solid {config.TLP_ORANGE};"


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
        return _hex_para_rgba(config.TLP_GOLD, 0.16)
    return _hex_para_rgba(config.TLP_RED, 0.10)


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
      • Nível 1 (Cluster/Coordenador) aberto: vira um SUBCABEÇALHO de
        verdade — fundo sólido e opaco em `config.TLP_ORANGE_LIGHT` (o
        tom "um pouco mais claro que o cabeçalho principal" de cada
        tema: laranja claro no tema laranja, azul-marinho claro no tema
        navy), texto escuro (`config.TEXT` — testado com >4.5:1 de
        contraste nos dois temas, melhor leitura que texto branco nesse
        tom claro) e a mesma barra grossa em degradê de marca à esquerda
        usada no resto do site. Antes era só um
        tingimento translúcido sobre branco — ficava quase da mesma
        intensidade das linhas já expandidas por baixo, dificultando
        notar onde acaba o grupo e começam os detalhes; com fundo sólido
        o subcabeçalho agora contrasta claramente tanto com o cabeçalho
        principal (mais escuro/saturado) quanto com as linhas internas
        (brancas/zebradas).
      • Nível 2, quando também é clicável (Supervisor, no caso de 3
        níveis): mesmo espírito — usa o mesmo tom claro do subcabeçalho,
        só que translúcido (não sólido) e mais fraco quando fechado, pra
        ficar visualmente "abaixo" do nível 1 mas ainda assim destacado
        das linhas-folha.
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
    cor_subcabecalho = config.TLP_ORANGE_LIGHT
    gradiente_marca = f"linear-gradient(180deg, {config.TLP_RED} 0%, {cor} 55%, {config.TLP_GOLD} 100%)"
    gradiente_suave = f"linear-gradient(180deg, {cor} 0%, {config.TLP_GOLD} 100%)"
    return (
        "<style>"
        # Divisória vertical em degradê entre colunas — em toda linha de
        # detalhe (cidade/supervisor/técnico), menos na 1ª coluna (nome).
        ".linha-cidade-expansivel td:not(:first-child){"
        f"background-image:{gradiente_marca}; background-repeat:no-repeat; "
        "background-position:left center; background-size:1.5px 62%;}"
        # Nível 1 (Cluster/Coordenador) aberto — subcabeçalho sólido.
        f".linha-cluster-expansivel.cluster-aberto{{background:{cor_subcabecalho} !important;}}"
        # Força texto escuro (mesma cor do corpo do site) em qualquer
        # célula/rótulo sem fundo próprio — testado: >4.5:1 de contraste
        # nos dois temas, bem melhor que texto branco sobre esse tom
        # claro (o badge de % já tem seu próprio fundo claro opaco — via
        # `[style*=\"background\"]` — então continua com sua cor original,
        # sempre legível independente da cor do subcabeçalho).
        f".linha-cluster-expansivel.cluster-aberto td:not([style*=\"background\"]){{color:{config.TEXT} !important;}}"
        f".linha-cluster-expansivel.cluster-aberto td span:not([style*=\"background\"]){{color:{config.TEXT} !important;}}"
        # O badge de %, por sua vez, TEM fundo próprio — mas era um verde/
        # vermelho bem clarinho e translúcido (pensado pra ficar sobre
        # branco); em cima do subcabeçalho sólido ele "camuflava". Reforça
        # pra um branco quase opaco só dentro das linhas de subcabeçalho
        # abertas (nível 1 e nível 2), deixando o texto colorido do badge
        # de fora dessa regra — assim ele volta a se destacar.
        ".cluster-aberto td span[style*=\"background\"]{"
        "background:rgba(255,255,255,0.92) !important; "
        "box-shadow:inset 0 0 0 1px rgba(0,0,0,0.05);}"
        ".linha-cluster-expansivel.cluster-aberto td:first-child{"
        f"background-image:{gradiente_marca}; background-repeat:no-repeat; "
        "background-position:left center; background-size:4px 100%; padding-left:16px !important;}"
        # Nível 2 clicável (Supervisor, nas tabelas de 3 níveis) — sempre
        # com um tapete leve pra se diferenciar da folha, e um tom
        # translúcido do MESMO subcabeçalho do Nível 1 quando aberto
        # (mais fraco que o sólido de cima — mantém a hierarquia:
        # cabeçalho > subcabeçalho Nível 1 > subcabeçalho Nível 2 > folha).
        f".linha-cidade-expansivel.linha-cluster-expansivel{{background:{cor}14 !important;}}"
        f".linha-cidade-expansivel.linha-cluster-expansivel.cluster-aberto{{background:{_hex_para_rgba(cor_subcabecalho, 0.38)} !important;}}"
        ".linha-cidade-expansivel.linha-cluster-expansivel td:first-child{"
        f"background-image:{gradiente_suave}; background-repeat:no-repeat; "
        "background-position:left center; background-size:3px 100%; padding-left:12px !important;}"
        # Nível-folha (sem filhos, não clicável): sem tingir — fica no
        # branco/cinza padrão do site; sem !important pra deixar o
        # zebrado inline (quando o Python já manda um) prevalecer.
        f".linha-cidade-expansivel:not(.linha-cluster-expansivel){{background:{config.CARD};}}"
        "</style>"
    )