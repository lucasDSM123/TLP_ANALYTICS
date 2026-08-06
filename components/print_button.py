import re
import unicodedata
import uuid
from contextlib import contextmanager

import streamlit as st


def sanitizar_chave(texto: str) -> str:
    """Reduz qualquer string (nome de grupo, título etc.) a um identificador
    seguro (minúsculo, sem acento, só letras/números/underscore) — usado
    tanto na `key` do `st.container` quanto no seletor CSS que o botão de
    print procura, garantindo que os dois sempre batem."""
    sem_acento = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9_]+", "_", sem_acento).strip("_").lower() or "area"


def botao_copiar_imagem(chave_container: str, rotulo: str = "📋 Copiar imagem", nome_arquivo: str = None):
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
    """
    chave_container = sanitizar_chave(chave_container)
    nome_arquivo = sanitizar_chave(nome_arquivo or chave_container)
    id_botao = f"btn-print-{chave_container}-{uuid.uuid4().hex[:6]}"

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

        var botao = document.getElementById('{id_botao}');
        var status = document.getElementById('{id_botao}-status');

        botao.addEventListener('click', function() {{
            status.textContent = 'Gerando imagem...';
            carregarHtml2Canvas(function(html2canvas) {{
                var doc = window.parent.document;
                var alvo = doc.querySelector('[class*="st-key-{chave_container}"]');
                if (!alvo) {{
                    status.textContent = 'Não encontrei essa área na página.';
                    return;
                }}
                html2canvas(alvo, {{ backgroundColor: '#FFFFFF', scale: 2, useCORS: true }}).then(function(canvas) {{
                    canvas.toBlob(function(blob) {{
                        if (!blob) {{
                            status.textContent = 'Erro ao gerar a imagem.';
                            return;
                        }}
                        if (navigator.clipboard && window.ClipboardItem) {{
                            navigator.clipboard.write([
                                new ClipboardItem({{ 'image/png': blob }})
                            ]).then(function() {{
                                status.textContent = '✅ Copiado! Já pode colar (Ctrl+V).';
                                setTimeout(function() {{ status.textContent = ''; }}, 4000);
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
                    status.textContent = 'Erro ao gerar a imagem.';
                }});
            }});
        }});
    }})();
    </script>
    """
    st.iframe(html, height=34, width="stretch")


@contextmanager
def area_com_print(chave: str, nome_arquivo: str = None, rotulo: str = "📋 Copiar imagem"):
    """
    Context manager que envolve QUALQUER bloco de conteúdo (gráfico,
    tabela/matriz, grupo de cards) com o botão "Copiar imagem" logo acima
    e o `st.container(key=...)` que ele efetivamente captura — tudo num só
    `with`, para não ter que repetir manualmente a sanitização da chave, a
    chamada do botão e a abertura do container em cada página do site (e
    arriscar as duas chaves ficarem diferentes por engano).

    Uso:
        with area_com_print("dashboard_matriz_ba", nome_arquivo="producao_ba"):
            tabela_matriz(matriz_ba, "PRODUÇÃO BA", cor_titulo="#00C9A7")

        with area_com_print("dashboard_grafico_status"):
            st.plotly_chart(grafico_status_pizza(status), config=opcoes_grafico("status_geral"))
    """
    chave_sanitizada = sanitizar_chave(chave)
    botao_copiar_imagem(chave_sanitizada, rotulo=rotulo, nome_arquivo=nome_arquivo or chave_sanitizada)
    with st.container(key=chave_sanitizada):
        yield
