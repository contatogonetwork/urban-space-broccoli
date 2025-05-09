import os
import streamlit as st
import traceback
from datetime import datetime
from db.extended_manager import ExtendedDatabaseManager
from views import *
from utils.constants import *
from config import *
from config import get_current_datetime, get_current_user

# Configuração do ngrok para acesso externo (opcional)
if os.getenv("SHARE_PUBLIC", "false").lower() == "true":
    from pyngrok import ngrok
    public_url = ngrok.connect(port=8501)
    print(f"Aplicação disponível publicamente em: {public_url}")

# Variáveis para rodapé
CURRENT_DATE = get_current_datetime()
CURRENT_USER = get_current_user()
APP_VERSION = os.getenv("APP_VERSION", "1.0")

# Configuração do Streamlit
st.set_page_config(
    page_title=os.getenv("PAGE_TITLE", "GELADEIRA - Sistema de Gerenciamento de Alimentos"), 
    layout=os.getenv("PAGE_LAYOUT", "wide"),
    initial_sidebar_state=os.getenv("INITIAL_SIDEBAR_STATE", "expanded")
)

# Função para verificar itens prestes a vencer
def verificar_itens_vencimento(db):
    try:
        itens_proximos = db.obter_itens_proximos_vencimento(dias=5)
        if itens_proximos and len(itens_proximos) > 0:
            st.warning(f"⚠️ **ATENÇÃO!** {len(itens_proximos)} item(s) irão vencer nos próximos dias!")
            with st.expander("Ver itens próximos do vencimento"):
                for item in itens_proximos:
                    st.markdown(f"**{item['nome']}**: Vence em {item['dias_ate_vencer']} dias ({item['data_validade']})")
    except Exception as e:
        st.error(f"Erro ao verificar vencimentos: {str(e)}")

# Função para carregar o banco de dados com tratamento de erros
@st.cache_resource(ttl=3600)
def carregar_banco_dados(db_path):
    try:
        db_manager = ExtendedDatabaseManager(db_path)
        success, msg = db_manager.verificar_integridade()
        if not success:
            st.warning(f"Alerta do banco de dados: {msg}")
        return db_manager
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {str(e)}")
        st.error("A aplicação pode não funcionar corretamente. Verifique a conexão com o banco.")
        return None

def main():
    # Inicialização do tema (claro/escuro)
    if "tema" not in st.session_state:
        st.session_state.tema = "claro"
    
    # Inicialização do banco de dados com a classe estendida e cache
    if "db" not in st.session_state:
        with st.spinner("Conectando ao banco de dados..."):
            db_manager = carregar_banco_dados(DB_PATH)
            if db_manager:
                st.session_state.db = db_manager
            else:
                st.error("Não foi possível inicializar o banco de dados. Verifique os logs.")
                return
    
    db = st.session_state.db
    
    # Verificação de saúde do banco
    if "ultima_verificacao" not in st.session_state or \
       (datetime.now() - st.session_state.ultima_verificacao).total_seconds() > 3600:
        try:
            success, msg = db.verificar_integridade()
            st.session_state.ultima_verificacao = datetime.now()
            if not success:
                st.warning(f"Verificação periódica do banco de dados: {msg}")
        except Exception as e:
            st.error(f"Erro na verificação periódica: {str(e)}")
    
    # Sidebar
    with st.sidebar:
        st.title("🛒 Menu")
        
        # Barra de pesquisa global
        st.text_input("🔍 Busca rápida:", 
                     key="busca_global", 
                     placeholder="Digite para buscar...",
                     help="Busque produtos no inventário")
        
        if st.session_state.busca_global and len(st.session_state.busca_global) > 2:
            termo = st.session_state.busca_global
            with st.spinner(f"Buscando '{termo}'..."):
                resultados = db.buscar_itens(termo)
                if resultados:
                    st.success(f"Encontrado(s) {len(resultados)} item(ns)")
                    for item in resultados:
                        if st.button(f"{item['nome']} ({item['quantidade']} {item['unidade']})", key=f"btn_{item['id']}"):
                            st.session_state.item_selecionado = item['id']
                            st.session_state.page = "Inventário Geral"
                            st.rerun()
                else:
                    st.info(f"Nenhum resultado encontrado para '{termo}'")
        
        # Opções de navegação
        st.subheader("Navegação")
        page = st.radio(
            "Escolha uma opção:",
            [
             "📋 Inventário Geral", 
             "👶 Thomás", "👶 Perfil Thomás", 
             "🔄 Categorias", 
             "📊 Relatórios", 
             "📝 Registrar Consumo",
             "🛒 Fazer Feira",
             "➕ Adicionar Item",
             "⚙️ Configurações", "🍽️ Receitas"]
        )
        
        st.divider()
        
        # Backup e restauração na sidebar
        st.subheader("📤 Backup/Restauração")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📤 Backup", use_container_width=True):
                st.session_state.page = "Configurações"
                st.rerun()
        
        with col2:
            if st.button("📥 Restaurar", use_container_width=True):
                st.session_state.page = "Configurações"
                st.rerun()
        
        # Footer com mais informações
        st.divider()
        st.caption(f"Versão: {APP_VERSION}")
        st.caption(f"Data: {CURRENT_DATE}")
        st.caption(f"Usuário: {CURRENT_USER}")
    
    # Alertas de vencimento no topo da página principal
    verificar_itens_vencimento(db)
    
    # Corpo principal baseado na navegação
    try:
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
        elif page == "⚙️ Configurações":
            mostrar_configuracoes(db)
        elif page == "🍽️ Receitas":
            mostrar_receitas(db)
    except Exception as e:
        st.error(f"Erro ao carregar a página {page}: {str(e)}")
        st.error("Por favor, recarregue a página ou contate o suporte.")
        st.code(traceback.format_exc())

def mostrar_receitas(db):
    """Exibe receitas sugeridas com base no inventário"""
    st.title("🍽️ Receitas Sugeridas")
    
    try:
        # Carregar inventário
        df = db.carregar_inventario()
        
        if df.empty:
            st.info("Inventário vazio. Adicione itens para obter sugestões de receitas.")
            return
            
        # Importar funções de receitas
        from utils.assistente import sugerir_receitas, gerar_lista_compras_para_receitas
        
        # Sugere receitas
        receitas = sugerir_receitas(df)
        
        if not receitas:
            st.info("Não foi possível obter sugestões de receitas com base no seu inventário atual.")
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
            import pandas as pd
            st.table(pd.DataFrame(lista))
            
    except Exception as e:
        st.error(f"Erro ao processar receitas: {str(e)}")
        st.code(traceback.format_exc())

if __name__ == "__main__":
    main()