import streamlit as st


def ativar_tabelas_expansiveis():
    """
    Liga o clique nas tabelas expansíveis Cluster -> Cidade (Produção e
    Análise P): qualquer elemento com a classe 'linha-cluster-expansivel'
    e um atributo 'data-alvo="{classe}"' passa a abrir/fechar (ao clicar)
    todo <tr> que tenha a classe '{classe}', vira a seta (▶/▼) dentro
    dele, e liga/desliga a classe 'cluster-aberto' na própria linha (usada
    pelo CSS de `estilo_tabela.estilo_expansivel` para o realce visual —
    fundo laranja clarinho + barra à esquerda — de quando o Cluster está
    aberto).

    IMPORTANTE — por que isso não é um simples `onclick="..."` no HTML da
    tabela: o `st.markdown(unsafe_allow_html=True)` do Streamlit permite
    tags HTML, mas remove atributos de evento (`onclick` etc.) por
    segurança — então um `onclick` embutido na tabela simplesmente não
    dispara. A solução é a mesma usada pelo botão "Copiar imagem"
    (`components/print_button.py`): rodar o JavaScript de verdade dentro
    de um `st.iframe`, que não sofre essa sanitização, e dali manipular a
    página principal via `window.parent.document`.

    Usa `document.onclick = ...` (que SUBSTITUI qualquer handler anterior,
    em vez de `addEventListener`, que ACUMULA) — assim, mesmo que esta
    função seja chamada várias vezes na mesma página (uma por tabela) ou a
    cada rerun do Streamlit, nunca corre o risco de ficar sem handler
    (nem de acumular handlers duplicados que se cancelariam mutuamente).

    Chame esta função uma vez em qualquer página que use
    `tabela_matriz_expansivel` ou `tabela_analise_p_cluster_cidade` (pode
    chamar mais de uma vez sem problema — é seguro/idempotente).
    """
    html = """
    <script>
    (function() {
        var doc = window.parent.document;

        doc.onclick = function(ev) {
            try {
                var linha = ev.target.closest('.linha-cluster-expansivel');
                if (!linha) { return; }
                var classeGrupo = linha.getAttribute('data-alvo');
                if (!classeGrupo) { return; }
                var linhasAlvo = doc.querySelectorAll('.' + classeGrupo);
                if (!linhasAlvo.length) { return; }
                var abrir = linhasAlvo[0].style.display === 'none';
                linhasAlvo.forEach(function(l) {
                    l.style.display = abrir ? 'table-row' : 'none';
                });
                linha.classList.toggle('cluster-aberto', abrir);
                var seta = linha.querySelector('.seta-exp');
                if (seta) { seta.textContent = abrir ? '▼' : '▶'; }
            } catch (erro) {
                // Nunca deixa uma falha inesperada aqui (ex.: um clique no
                // meio de um rerender do Streamlit, com a linha já tendo
                // sumido do DOM) escapar como exceção não tratada dentro do
                // handler de clique do documento — isso pode confundir a
                // reconciliação do React em volta (erro "removeChild" na
                // tela) mesmo sem relação direta com esta tabela.
                console.warn('Falha ao abrir/fechar Cluster:', erro);
            }
        };
    })();
    </script>
    """
    st.iframe(html, height=1, width="stretch")