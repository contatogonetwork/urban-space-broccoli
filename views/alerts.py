import streamlit as st
import pandas as pd
from datetime import date

def mostrar_alertas(db):
    st.title("🔔 Sistema de Alertas")
    
    # Abas para diferentes tipos de alertas
    tab1, tab2, tab3 = st.tabs(["⏰ Vencimentos", "🚫 Restrições", "📉 Estoque"])
    
    with tab1:
        mostrar_alertas_vencimento(db)
    with tab2:
        mostrar_alertas_restricoes(db)
    with tab3:
        mostrar_alertas_estoque(db)

def mostrar_alertas_vencimento(db):
    """Exibe alertas de vencimento próximo"""
    st.header("⏰ Alertas de Vencimento")
    
    try:
        # Carregar todos os produtos perecíveis
        df = db.carregar_inventario()
        
        if df.empty:
            st.info("Não há itens no inventário para monitorar.")
            return
            
        # Filtrar apenas itens perecíveis com data de validade
        df_pereciveis = df[df["Perecível"] == 1].dropna(subset=["Validade"])
        
        if df_pereciveis.empty:
            st.info("Não há itens perecíveis com data de validade definida.")
            return
            
        # Definir período de alertas
        dias_alerta = st.session_state.get("dias_alerta_vencimento", 7)
        
        # Calcular dias até vencer
        df_pereciveis['Dias Até Vencer'] = (
            pd.to_datetime(df_pereciveis['Validade']).dt.date
            - date.today()
        ).dt.days
        
        # Filtrar por dias até vencer
        df_alertas = df_pereciveis[df_pereciveis['Dias Até Vencer'] <= dias_alerta]
        
        # Exibir alertas
        if df_alertas.empty:
            st.info("Nenhum vencimento próximo dentro do período configurado.")
        else:
            st.dataframe(df_alertas, use_container_width=True)
    except Exception as e:
        st.error(f"Erro ao processar alertas de vencimento: {str(e)}")

def mostrar_alertas_restricoes(db):
    """Exibe alertas relacionados a restrições alimentares"""
    st.header("🚫 Alertas de Restrições")
    try:
        df = db.carregar_inventario()
        if df.empty or "Para Thomas" not in df.columns:
            st.info("Não há itens com restrições alimentares cadastrados.")
            return
        restritos = df[(df["Para Thomas"] == 1) & (df["Compatibilidade Thomas"] == 0)]
        if restritos.empty:
            st.info("Nenhum alerta de restrição alimentar encontrado.")
        else:
            st.dataframe(restritos, use_container_width=True)
    except Exception as e:
        st.error(f"Erro ao processar alertas de restrições: {str(e)}")

def mostrar_alertas_estoque(db):
    """Exibe alertas de estoque baixo e sugestões"""
    st.header("📉 Alertas de Estoque")
    try:
        df = db.carregar_inventario()
        if df.empty or "Quantidade" not in df.columns:
            st.info("Não há itens para monitorar estoque.")
            return
        nivel_alerta = st.session_state.get("nivel_alerta_quantidade", 20)
        estoque_baixo = df[df["Quantidade"] < nivel_alerta]
        if estoque_baixo.empty:
            st.info("Nenhum item com estoque baixo.")
        else:
            st.dataframe(estoque_baixo, use_container_width=True)
    except Exception as e:
        st.error(f"Erro ao processar alertas de estoque: {str(e)}")
