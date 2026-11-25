"""
Cache dos cálculos pesados da camada de serviços.

Mudar um flag (st.segmented_control / st.radio) reexecuta o script inteiro. Como
a base e os filtros não mudaram, os mesmos cálculos (matrizes, tabelas por
técnico/coordenador...) davam o MESMO resultado e eram refeitos do zero.
Com `@cache_calculo` o resultado fica guardado pela chave (conteúdo do DataFrame
+ argumentos): mudar de flag vira só um acerto de cache. Se a base ou os
filtros mudarem, o conteúdo muda, a chave muda e o cálculo roda de novo.
"""
import streamlit as st


def cache_calculo(func):
    """st.cache_data para funções puras que recebem um DataFrame.

    - max_entries: limita a memória (várias combinações de filtros x vários usuários).
    - ttl: entradas antigas expiram sozinhas (a base também é recarregada a cada 10 min).
    - o Streamlit devolve uma CÓPIA do resultado, então quem chama pode alterá-lo à vontade.
    """
    return st.cache_data(show_spinner=False, max_entries=48, ttl=900)(func)
