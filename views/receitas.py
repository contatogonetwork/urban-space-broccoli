import streamlit as st
import pandas as pd
from utils.assistente import sugerir_receitas, gerar_lista_compras_para_receitas


def mostrar_receitas(db):
    """Exibe receitas sugeridas com base no inventário"""
    st.title("🍽️ Receitas Sugeridas")
    df = db.carregar_inventario()
    if df.empty:
        st.info("Inventário vazio. Adicione itens para obter sugestões de receitas.")
        return
    # Sugere receitas
    receitas = sugerir_receitas(df)
    if not receitas:
        st.info("Não foi possível obter sugestões de receitas.")
        return
    # Exibir cada receita
    for r in receitas:
        st.subheader(r.get("titulo", "-"))
        if r.get("imagem"):
            st.image(r["imagem"], width=200)
        info = []
        if r.get("tempo_preparo"):
            info.append(f"⏱️ {r['tempo_preparo']} min")
        if r.get("porcoes"):
            info.append(f"Porções: {r['porcoes']}")
        if info:
            st.write(" • ".join(info))
        if r.get("instrucoes"):
            st.markdown(r["instrucoes"])
        faltantes = r.get("ingredientes_faltantes", [])
        if faltantes:
            st.write("**Ingredientes faltantes:**", ", ".join(faltantes))
        st.write("---")
    # Exibir lista de compras complementar
    lista = gerar_lista_compras_para_receitas(receitas, df)
    if lista:
        st.subheader("🛒 Lista de compras complementar")
        st.table(pd.DataFrame(lista))
