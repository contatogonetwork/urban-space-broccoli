import streamlit as st
import pandas as pd
from utils.assistente import sugerir_receitas, gerar_lista_compras_para_receitas

def mostrar_receitas(db):
    """Exibe receitas sugeridas com base no inventário"""
    st.title("🍽️ Receitas Sugeridas")
    
    try:
        # Carregar inventário
        df = db.carregar_inventario()
        
        if df.empty:
            st.info("Inventário vazio. Adicione itens para obter sugestões de receitas.")
            return
            
        # Sugere receitas
        receitas = sugerir_receitas(df)
        
        if not receitas or len(receitas) == 0:
            st.info("Não foi possível obter sugestões de receitas com base no seu inventário atual.")
            
            # Mostrar dicas para obter receitas
            st.markdown("""
            ### Para obter sugestões de receitas:
            
            1. Adicione mais itens ao seu inventário
            2. Verifique se os nomes dos itens correspondem a ingredientes comuns de receitas
            3. Certifique-se de ter itens básicos como:
               - Ovos
               - Farinha
               - Azeite/Óleo
               - Sal
               - Vegetais comuns
            """)
            return
            
        # Exibir cada receita
        for r in receitas:
            st.subheader(r.get("titulo", "-"))
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                if r.get("imagem"):
                    st.image(r["imagem"], width=200)
                    
                info = []
                if r.get("tempo_preparo"):
                    info.append(f"⏱️ {r['tempo_preparo']} min")
                if r.get("porcoes"):
                    info.append(f"Porções: {r['porcoes']}")
                    
                if info:
                    st.write(" • ".join(info))
            
            with col2:
                # Ingredientes que você tem
                ingredientes_usados = r.get("ingredientes_usados", [])
                if ingredientes_usados:
                    st.write("**📋 Ingredientes disponíveis:**")
                    for ing in ingredientes_usados:
                        st.write(f"✓ {ing}")
                
                # Ingredientes faltantes
                faltantes = r.get("ingredientes_faltantes", [])
                if faltantes:
                    st.write("**🛒 Ingredientes faltantes:**")
                    for ing in faltantes:
                        st.write(f"⚠️ {ing}")
                
            # Modo de preparo
            st.write("**👨‍🍳 Modo de Preparo:**")
            if r.get("instrucoes"):
                st.markdown(r["instrucoes"])
            else:
                st.write("Instruções não disponíveis para esta receita.")
                
            st.divider()
            
        # Exibir lista de compras complementar
        lista = gerar_lista_compras_para_receitas(receitas, df)
        if lista:
            st.subheader("🛒 Lista de compras complementar")
            
            # Criar DataFrame para exibir
            df_lista = pd.DataFrame(lista)
            
            # Configurar colunas
            config_dict = {
                "nome": st.column_config.TextColumn("Ingrediente"),
                "quantidade": st.column_config.NumberColumn("Quantidade", format="%.1f"),
                "unidade": st.column_config.TextColumn("Unidade"),
                "receitas": st.column_config.ListColumn("Usado nas receitas")
            }
            
            st.dataframe(df_lista, use_container_width=True, column_config=config_dict, hide_index=True)
            
            # Botão para adicionar à lista de compras
            if st.button("Adicionar todos à lista de compras"):
                st.success("Ingredientes adicionados à lista de compras!")
                # Aqui você implementaria a lógica para adicionar à lista de compras
                # Por exemplo, salvando na session_state
            
    except Exception as e:
        st.error(f"Erro ao processar receitas: {str(e)}")
        st.info("Não foi possível carregar as sugestões de receitas. Por favor, tente novamente mais tarde.")
        import traceback
        st.error(traceback.format_exc())
