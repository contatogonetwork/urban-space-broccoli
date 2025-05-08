import streamlit as st
import os
from db.extended_manager import ExtendedDatabaseManager
from views import *
from utils.constants import *
from config import *

# Configuração do Streamlit
st.set_page_config(
    page_title=PAGE_TITLE, 
    layout=PAGE_LAYOUT,
    initial_sidebar_state=INITIAL_SIDEBAR_STATE
)

def main():
    # Inicialização do banco de dados com a classe estendida
    if "db" not in st.session_state:
        st.session_state.db = ExtendedDatabaseManager(DB_PATH)
    
    db = st.session_state.db
    
    # Sidebar
    with st.sidebar:
        st.title("🛒 Menu")
        
        # Opções de navegação - Adicionado "Fazer Feira"
        page = st.radio(
            "Escolha uma opção:",
            ["📋 Inventário Geral", 
             "👶 Thomás", "👶 Perfil Thomás", 
             "🔄 Categorias", 
             "📊 Relatórios", 
             "📝 Registrar Consumo",
             "🛒 Fazer Feira",
             "➕ Adicionar Item"]
        )
        
        st.divider()
        
        # Backup e restauração na sidebar
        st.subheader("📤 Backup/Restauração")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Exportar CSV"):
                success, msg, csv_file = db.exportar_csv()
                if success:
                    with open(csv_file, "rb") as file:
                        st.download_button(
                            label="⬇️ Baixar CSV",
                            data=file,
                            file_name=csv_file,
                            mime="text/csv"
                        )
                else:
                    st.error(msg)
        
        with col2:
            uploaded_file = st.file_uploader("Importar CSV", type="csv")
            if uploaded_file is not None:
                if st.button("📤 Carregar Dados"):
                    success, msg = db.importar_csv(uploaded_file)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
        
        # Opção de resetar banco de dados
        st.subheader("⚙️ Manutenção do Banco")
        if st.button("🔄 Resetar Banco de Dados"):
            if st.checkbox("Confirmar RESET completo (fará backup do atual)"):
                success, msg = db.resetar_banco()
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
        
        # Alterar localização do banco de dados
        st.subheader("📁 Configuração")
        db_location = st.text_input("Localização do banco:", value=DB_PATH, 
                                   help="Altere e clique em 'Atualizar' para mudar o local")
        if st.button("📂 Atualizar") and db_location != DB_PATH:
            # Armazenar nova configuração
            # (Em uma versão real, atualizaríamos o arquivo .env)
            st.session_state.db = ExtendedDatabaseManager(db_location)
            st.success(f"Banco alterado para: {db_location}")
            st.rerun()
        
        # Footer
        st.divider()
        st.caption(f"Última atualização: {CURRENT_DATE}")
        st.caption(f"Usuário: {CURRENT_USER}")
    
    # Corpo principal baseado na navegação
    if page == "📋 Inventário Geral":
        mostrar_inventario_geral(db)
    elif page == "👶 Thomás":
        mostrar_inventario_thomas(db)
    elif page == "👶 Perfil Thomás":
        mostrar_perfil_thomas(db)
    elif page == "🔄 Categorias":
        mostrar_categorias(db)
    elif page == "📊 Relatórios":
        mostrar_relatorios(db)
    elif page == "📝 Registrar Consumo":
        registrar_consumo(db)
    elif page == "🛒 Fazer Feira":
        mostrar_planejamento_feira(db)
    elif page == "➕ Adicionar Item":
        adicionar_item_form(db)

if __name__ == "__main__":
    main()