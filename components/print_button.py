import json
import re
import unicodedata
import uuid
from contextlib import contextmanager

import streamlit as st


def montar_legenda(template: str, variaveis: dict, chave_horario: str) -> str:
    """
    Monta o texto da legenda a partir de um `template` fixo (ex.:
    "PRODUÇÃO GERAL {estado} | {data} {hora}") e das `variaveis` já
    resolvidas (ex.: {"estado": "SC", "data": "21/08/2026"}).

    O `{hora}` é preenchido sozinho com a hora de extração da base
    (`st.session_state["data_extracao_hora"]`, calculada em app.py) — o
    campinho de texto acima do botão só existe pra dar a chance de
    corrigir/trocar na hora, se precisar; edições manuais são respeitadas
    e não voltam a ser sobrescritas sozinhas enquanto a extração não mudar
    de novo.
    """
    hora_extracao = st.session_state.get("data_extracao_hora", "")
    chave_auto = f"__auto_{chave_horario}"
    # Só reaplica o valor automático se o campo ainda não foi tocado (1ª
    # vez) ou se ainda está igual ao último valor automático que a gente
    # mesmo colocou — assim uma edição manual do usuário não é perdida a
    # cada rerun, mas uma extração nova ainda atualiza sozinha.
    if chave_horario not in st.session_state or st.session_state[chave_horario] == st.session_state.get(chave_auto):
        st.session_state[chave_horario] = hora_extracao
    st.session_state[chave_auto] = hora_extracao

    hora = st.text_input(
        "Horário",
        key=chave_horario,
        placeholder="ex: 09:34",
        label_visibility="collapsed",
    )
    dados = {"hora": hora.strip(), **variaveis}
    texto = template.format(**dados)
    # Remove espaços/pipes sobrando quando algum campo (ex.: hora ainda
    # não digitada) fica vazio, sem quebrar o restante da legenda.
    texto = re.sub(r"\s+", " ", texto).strip()
    texto = re.sub(r"\|\s*$", "", texto).strip()
    return texto


def sanitizar_chave(texto: str) -> str:
    """Reduz qualquer string (nome de grupo, título etc.) a um identificador
    seguro (minúsculo, sem acento, só letras/números/underscore) — usado
    tanto na `key` do `st.container` quanto no seletor CSS que o botão de
    print procura, garantindo que os dois sempre batem."""
    sem_acento = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9_]+", "_", sem_acento).strip("_").lower() or "area"


def botao_copiar_imagem(chave_container: str, rotulo: str = "📋 Copiar imagem", nome_arquivo: str = None,
                         legenda: str = None):
    """
    Botão que "fotografa" a área envolvida por `st.container(key=chave_container)`
    — cards, tabelas/matrizes, qualquer bloco HTML do site — e COPIA a
    imagem direto para a área de transferência do usuário, pronta pra colar
    em outro lugar (WhatsApp, Word, PowerPoint, e-mail etc.), sem precisar
    salvar um arquivo primeiro.

    IMPORTANTE — ordem de uso: chame este botão logo ANTES do bloco
    `with st.container(key=chave_container):` que envolve a área a ser
    capturada (mesma `chave_container` nos dois).

    Funciona via html2canvas (carregado de um CDN público) + Clipboard API
    do navegador. Duas exigências do próprio navegador (não dá pra
    contornar):
    - precisa ser HTTPS ou localhost (Clipboard API não funciona em HTTP puro);
    - se o navegador não suportar copiar imagem (ex.: Firefox mais antigo),
      cai automaticamente para baixar a imagem como PNG.

    Se `legenda` for informada, ela vai junto na área de transferência
    como texto (além da imagem) no mesmo clique — cole a imagem
    (Ctrl+V) e, no campo de legenda do WhatsApp, cole de novo (Ctrl+V)
    para trazer o texto automaticamente, sem precisar digitar.
    """
    chave_container = sanitizar_chave(chave_container)
    nome_arquivo = sanitizar_chave(nome_arquivo or chave_container)
    id_botao = f"btn-print-{chave_container}-{uuid.uuid4().hex[:6]}"
    legenda_js = json.dumps(legenda) if legenda else "null"

    if legenda:
        st.caption(f"📝 Legenda que vai junto: \"{legenda}\"")

    html = f"""
    <div style="display:flex; justify-content:flex-end; align-items:center; margin:0 0 4px 0;">
      <button id="{id_botao}" type="button" style="
        display:inline-flex; align-items:center; gap:6px;
        background:#FFFFFF; border:1px solid #E4E7EC; color:#1F2430;
        border-radius:8px; padding:5px 12px; font-size:12.5px; font-weight:600;
        font-family:'Poppins', sans-serif; cursor:pointer; white-space:nowrap;
      ">{rotulo}</button>
      <span id="{id_botao}-status" style="margin-left:8px; font-size:12px; color:#6B7280;"></span>
    </div>
    <script>
    (function() {{
        function carregarHtml2Canvas(callback) {{
            var doc = window.parent.document;
            var win = doc.defaultView;
            if (win.html2canvas) {{ callback(win.html2canvas); return; }}
            if (win.__html2canvasCarregando) {{
                win.__html2canvasFilaDeEspera = win.__html2canvasFilaDeEspera || [];
                win.__html2canvasFilaDeEspera.push(callback);
                return;
            }}
            win.__html2canvasCarregando = true;
            var script = doc.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';
            script.onload = function() {{
                win.__html2canvasCarregando = false;
                callback(win.html2canvas);
                (win.__html2canvasFilaDeEspera || []).forEach(function(cb) {{ cb(win.html2canvas); }});
                win.__html2canvasFilaDeEspera = [];
            }};
            doc.head.appendChild(script);
        }}

        function baixarImagem(canvas) {{
            var doc = window.parent.document;
            var link = doc.createElement('a');
            link.download = '{nome_arquivo}.png';
            link.href = canvas.toDataURL('image/png');
            doc.body.appendChild(link);
            link.click();
            doc.body.removeChild(link);
        }}

        function removerCortes(raiz) {{
            // Qualquer elemento com "overflow" diferente de visible (ex.: o
            // cartão da tabela, que tem cantos arredondados + rolagem
            // horizontal) corta uns pixels do conteúdo bem na borda —
            // normalmente imperceptível na tela, mas fica visível na
            // captura (cabeçalho cortado em cima, colunas cortadas do
            // lado). Aqui a gente neutraliza isso na cópia (garantindo
            // também que a largura acompanhe o conteúdo quando havia
            // rolagem de verdade).
            var candidatos = [raiz].concat(Array.prototype.slice.call(raiz.querySelectorAll('*')));
            candidatos.forEach(function(el) {{
                var estilo = window.getComputedStyle(el);
                if (estilo.overflow !== 'visible' || estilo.overflowX !== 'visible' || estilo.overflowY !== 'visible') {{
                    el.style.overflow = 'visible';
                    el.style.overflowX = 'visible';
                    el.style.overflowY = 'visible';
                }}
                if (el.scrollWidth > el.clientWidth + 1) {{
                    el.style.maxWidth = 'none';
                    el.style.width = el.scrollWidth + 'px';
                }}
            }});
        }}

        function colSpanDe(el) {{
            var v = parseInt(el.getAttribute('colspan') || '1', 10);
            return (!v || v < 1) ? 1 : v;
        }}

        function colunaInicial(celula) {{
            // Soma o colspan de todos os irmãos anteriores na mesma linha
            // pra saber em que "coluna visual" essa célula começa — não dá
            // pra usar só a posição no DOM porque células com colspan (ex.:
            // "CONCLUÍDA", que ocupa 3 colunas) desalinham a contagem.
            var col = 0;
            var irmao = celula.previousElementSibling;
            while (irmao) {{
                col += colSpanDe(irmao);
                irmao = irmao.previousElementSibling;
            }}
            return col;
        }}

        function indiceParaColuna(linha, colunaAlvo) {{
            // Acha em que índice de filho inserir um novo elemento pra ele
            // cair exatamente na coluna visual "colunaAlvo" dentro de
            // "linha", considerando o colspan de quem já está lá.
            var col = 0;
            var filhos = linha.children;
            for (var i = 0; i < filhos.length; i++) {{
                if (col >= colunaAlvo) return i;
                col += colSpanDe(filhos[i]);
            }}
            return filhos.length;
        }}

        function desfazerRowspan(raiz, manterTextoClonado) {{
            // html2canvas tem um bug conhecido com células <td>/<th> que
            // usam rowspan (ex.: o nome do Coordenador mesclado em várias
            // linhas, ou os cabeçalhos que "olham" pra duas linhas) — o
            // texto às vezes some, fica mal posicionado ou sobrepõe a
            // linha seguinte. Solução: duplicar a célula em cada linha que
            // ela cobria e remover o rowspan — a tabela fica "desmesclada"
            // pro html2canvas (visualmente idêntica, já que as bordas
            // continuam as mesmas — só o agrupamento de células muda por
            // baixo). Leva em conta colspan pra não desalinhar colunas
            // (ex.: o cabeçalho "CONCLUÍDA", que ocupa 3 colunas).
            //
            // Usada só no cabeçalho: o rótulo já aparece na primeira
            // linha — a célula clonada na segunda linha só existe pra
            // manter a coluna alinhada, então o texto dela fica vazio
            // (senão o rótulo aparece duplicado, uma vez em cada linha do
            // cabeçalho).
            var celulas = raiz.querySelectorAll('td[rowspan], th[rowspan]');
            celulas.forEach(function(celula) {{
                var rowspan = parseInt(celula.getAttribute('rowspan'), 10);
                if (!rowspan || rowspan <= 1) return;
                var linha = celula.parentElement;
                var colunaAlvo = colunaInicial(celula);
                var linhaSeguinte = linha;
                for (var i = 1; i < rowspan; i++) {{
                    linhaSeguinte = linhaSeguinte.nextElementSibling;
                    if (!linhaSeguinte) break;
                    var clone = celula.cloneNode(true);
                    clone.removeAttribute('rowspan');
                    if (!manterTextoClonado) {{
                        clone.textContent = '';
                    }}
                    var indiceInsercao = indiceParaColuna(linhaSeguinte, colunaAlvo);
                    var referencia = linhaSeguinte.children[indiceInsercao] || null;
                    linhaSeguinte.insertBefore(clone, referencia);
                }}
                celula.removeAttribute('rowspan');
            }});
        }}

        function desfazerRowspanMesclado(corpoTabela, gruposMesclados) {{
            // Igual à ideia do desfazerRowspan (duplicar a célula em cada
            // linha que o rowspan cobria, pra fugir do bug do html2canvas)
            // só que, no corpo da tabela, NÃO queremos repetir o nome do
            // Coordenador em toda linha — queremos que ele apareça uma
            // única vez, centralizado (tanto na vertical quanto na
            // horizontal), exatamente como o rowspan de verdade se
            // comporta no navegador. Como html2canvas não faz isso
            // sozinho com rowspan real, a gente simula: mantém o texto só
            // na primeira célula do grupo, deixa as demais vazias (só de
            // "espaço", sem borda entre elas — viram um bloco
            // visualmente único), e registra o grupo em
            // `gruposMesclados` pra, depois que o navegador terminar de
            // calcular o layout, centralizar o texto na altura total do
            // bloco (feito em `centralizarGruposMesclados`, chamada já
            // com a tabela desenhada — antes disso as alturas de linha
            // ainda não existem pra medir).
            var celulas = corpoTabela.querySelectorAll('td[rowspan], th[rowspan]');
            celulas.forEach(function(celulaOriginal) {{
                var rowspan = parseInt(celulaOriginal.getAttribute('rowspan'), 10);
                if (!rowspan || rowspan <= 1) return;
                var linha = celulaOriginal.parentElement;
                var colunaAlvo = colunaInicial(celulaOriginal);
                var grupo = [celulaOriginal];
                var linhaSeguinte = linha;
                for (var i = 1; i < rowspan; i++) {{
                    linhaSeguinte = linhaSeguinte.nextElementSibling;
                    if (!linhaSeguinte) break;
                    var clone = celulaOriginal.cloneNode(true);
                    clone.removeAttribute('rowspan');
                    clone.textContent = ''; // texto só existe na 1ª célula do grupo
                    var indiceInsercao = indiceParaColuna(linhaSeguinte, colunaAlvo);
                    var referencia = linhaSeguinte.children[indiceInsercao] || null;
                    linhaSeguinte.insertBefore(clone, referencia);
                    grupo.push(clone);
                }}
                celulaOriginal.removeAttribute('rowspan');
                // Remove a borda entre as células do grupo (de ambos os
                // lados da divisa) pra virarem um retângulo único sem
                // linha cortando no meio — igual ao visual do rowspan
                // real.
                for (var g = 0; g < grupo.length - 1; g++) {{
                    grupo[g].style.borderBottom = 'none';
                    grupo[g + 1].style.borderTop = 'none';
                }}
                gruposMesclados.push(grupo);
            }});
        }}

        function centralizarGruposMesclados(gruposMesclados) {{
            // Chamada só depois que o navegador já calculou a altura real
            // de cada linha (por isso fica depois dos requestAnimationFrame
            // de layout). Para cada grupo de células "desmescladas", mede
            // a altura total (do topo da 1ª célula até o fim da última) e
            // sobrepõe o texto original numa camada absoluta, centralizada
            // vertical E horizontalmente nessa altura total — reproduzindo
            // o `vertical-align:middle` + `text-align:center` que o
            // rowspan real teria.
            gruposMesclados.forEach(function(grupo) {{
                var primeira = grupo[0];
                var ultima = grupo[grupo.length - 1];
                var altura = (ultima.offsetTop + ultima.offsetHeight) - primeira.offsetTop;
                if (!altura) return;

                var conteudoOriginal = primeira.innerHTML;
                primeira.innerHTML = '';
                primeira.style.position = 'relative';
                primeira.style.textAlign = 'center';

                var camada = document.createElement('div');
                camada.style.position = 'absolute';
                camada.style.top = '0';
                camada.style.left = '0';
                camada.style.right = '0';
                camada.style.height = altura + 'px';
                camada.style.display = 'flex';
                camada.style.alignItems = 'center';
                camada.style.justifyContent = 'center';
                camada.style.textAlign = 'center';
                camada.innerHTML = conteudoOriginal;
                primeira.appendChild(camada);
            }});
        }}

        var botao = document.getElementById('{id_botao}');
        var status = document.getElementById('{id_botao}-status');
        var legendaTexto = {legenda_js};

        botao.addEventListener('click', function() {{
            status.textContent = 'Gerando imagem...';
            carregarHtml2Canvas(function(html2canvas) {{
                var doc = window.parent.document;
                var alvo = doc.querySelector('[class*="st-key-{chave_container}"]');
                if (!alvo) {{
                    status.textContent = 'Não encontrei essa área na página.';
                    return;
                }}

                // Fotografa uma CÓPIA isolada fora da tela (não a área
                // visível de verdade). Assim: (1) não precisa rolar a
                // página nem se preocupar com a posição de rolagem do
                // usuário, e (2) dá pra "desmesclar" as células com
                // rowspan sem alterar a tabela que o usuário está vendo.
                var wrapper = doc.createElement('div');
                wrapper.style.position = 'absolute';
                wrapper.style.top = '0';
                wrapper.style.left = '-99999px';
                wrapper.style.background = '#FFFFFF';
                var copia = alvo.cloneNode(true);
                // Margem de segurança na PRÓPRIA cópia (não no wrapper —
                // como o html2canvas fotografa "copia" diretamente, um
                // padding no wrapper não tem efeito nenhum na captura).
                copia.style.padding = '6px';
                copia.style.background = '#FFFFFF';
                copia.style.boxSizing = 'border-box';
                wrapper.appendChild(copia);
                doc.body.appendChild(wrapper);

                removerCortes(copia);
                var gruposMesclados = [];
                var cabecalho = copia.querySelector('thead');
                if (cabecalho) {{
                    // Cabeçalho: mantém a célula pra não desalinhar as
                    // colunas, mas sem duplicar o texto do rótulo.
                    desfazerRowspan(cabecalho, false);
                }}
                var corpoTabela = copia.querySelector('tbody');
                if (corpoTabela) {{
                    // Corpo: nome do Coordenador aparece uma única vez,
                    // mesclado/centralizado — igual à tabela original do
                    // site (a centralização em si só acontece depois,
                    // quando a altura das linhas já existe pra medir).
                    desfazerRowspanMesclado(corpoTabela, gruposMesclados);
                }}

                // Espera o navegador terminar de aplicar todos os estilos e
                // recalcular o layout da cópia recém-inserida antes de
                // fotografar — sem isso, o html2canvas às vezes mede a
                // altura/posição com o layout ainda "cru", cortando uns
                // pixels do topo da imagem. Só depois disso dá pra medir a
                // altura real das linhas e centralizar os nomes mesclados.
                requestAnimationFrame(function() {{
                    requestAnimationFrame(function() {{
                        centralizarGruposMesclados(gruposMesclados);
                        requestAnimationFrame(function() {{
                            capturarCopia();
                        }});
                    }});
                }});

                function capturarCopia() {{
                html2canvas(copia, {{
                    backgroundColor: '#FFFFFF',
                    scale: 2,
                    useCORS: true,
                }}).then(function(canvas) {{
                    doc.body.removeChild(wrapper);
                    canvas.toBlob(function(blob) {{
                        if (!blob) {{
                            status.textContent = 'Erro ao gerar a imagem.';
                            return;
                        }}
                        if (navigator.clipboard && window.ClipboardItem) {{
                            var tiposClipboard = {{ 'image/png': blob }};
                            if (legendaTexto) {{
                                tiposClipboard['text/plain'] = new Blob([legendaTexto], {{ type: 'text/plain' }});
                            }}
                            navigator.clipboard.write([
                                new ClipboardItem(tiposClipboard)
                            ]).then(function() {{
                                status.textContent = legendaTexto
                                    ? '✅ Copiado (imagem + legenda)! Cole a imagem e, no campo de legenda, cole de novo.'
                                    : '✅ Copiado! Já pode colar (Ctrl+V).';
                                setTimeout(function() {{ status.textContent = ''; }}, 5000);
                            }}).catch(function() {{
                                baixarImagem(canvas);
                                status.textContent = 'Não consegui copiar — baixei a imagem.';
                            }});
                        }} else {{
                            baixarImagem(canvas);
                            status.textContent = 'Seu navegador não copia imagem — baixei o arquivo.';
                        }}
                    }});
                }}).catch(function() {{
                    doc.body.removeChild(wrapper);
                    status.textContent = 'Erro ao gerar a imagem.';
                }});
                }}
            }});
        }});
    }})();
    </script>
    """
    st.iframe(html, height=34, width="stretch")


@contextmanager
def area_com_print(chave: str, nome_arquivo: str = None, rotulo: str = "📋 Copiar imagem",
                    legenda_template: str = None, legenda_vars: dict = None):
    """
    Context manager que envolve QUALQUER bloco de conteúdo (gráfico,
    tabela/matriz, grupo de cards) com o botão "Copiar imagem" logo acima
    e o `st.container(key=...)` que ele efetivamente captura — tudo num só
    `with`, para não ter que repetir manualmente a sanitização da chave, a
    chamada do botão e a abertura do container em cada página do site (e
    arriscar as duas chaves ficarem diferentes por engano).

    Uso (sem legenda):
        with area_com_print("dashboard_matriz_ba", nome_arquivo="producao_ba"):
            tabela_matriz(matriz_ba, "PRODUÇÃO BA", cor_titulo="#00C9A7")

    Uso (com legenda automática — só nas áreas indicadas): o texto é fixo
    por área (`legenda_template`), preenchido com os valores já resolvidos
    em `legenda_vars` (ex.: estado/data vindos dos filtros do topo). O
    único campo digitado na hora é o horário ("{hora}" no template), que
    aparece como uma caixinha de texto pequena acima do botão:

        with area_com_print(
            "dashboard_cards_principais", nome_arquivo="indicadores_principais",
            legenda_template="PRODUÇÃO GERAL {estado} | {data} {hora}",
            legenda_vars={"estado": "SC", "data": "21/08/2026"},
        ):
            ...
    """
    chave_sanitizada = sanitizar_chave(chave)
    legenda = None
    if legenda_template:
        legenda = montar_legenda(legenda_template, legenda_vars or {}, chave_horario=f"horario_{chave_sanitizada}")
    botao_copiar_imagem(chave_sanitizada, rotulo=rotulo, nome_arquivo=nome_arquivo or chave_sanitizada,
                         legenda=legenda)
    with st.container(key=chave_sanitizada):
        yield