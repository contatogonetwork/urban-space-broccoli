import os
import streamlit as st
import traceback
import logging
from datetime import datetime, timedelta
# Corrigido: Usar o extended_database_manager que tem sido o foco da revisão
from db.extended_database_manager import ExtendedDatabaseManager 
# Melhoria: Importações explícitas de views
from views.inventory import mostrar_inventario_geral, adicionar_item_form
from views.thomas import mostrar_inventario_thomas, mostrar_perfil_thomas
from views.consumption import mostrar_categorias, registrar_consumo
from views.reports import mostrar_relatorios
from views.shopping import mostrar_planejamento_feira
from views.settings import mostrar_configuracoes
from views.recipes import mostrar_receitas # <--- Adicionado

# Melhoria: Importações explícitas de utils.constants
from utils.constants import CATEGORIAS_ALIMENTOS, UNIDADES_MEDIDA, LOCAIS_ARMAZENAMENTO
from utils.db_optimizer import otimizar_banco_dados, realizar_backup
from utils.validador import validar_produto, sanitizar_texto
# Melhoria: Importações explícitas de config
from config import DB_PATH, load_config, get_current_datetime, get_current_user

# Import or define DatabaseErrorHandler
class DatabaseErrorHandler:
    @staticmethod
    def handle_critical_error(db_path, error_message):
        try:
            # Log the error
            logging.error(f"Critical database error: {error_message}")
            
            # Attempt to create a backup of the corrupted database
            backup_success, backup_path = realizar_backup(db_path)
            if backup_success:
                logging.info(f"Backup of corrupted DB created successfully: {backup_path}")
            else:
                logging.warning(f"Failed to backup corrupted DB: {db_path}")

            # Melhoria: Renomear o banco de dados corrompido em vez de remover
            corrupted_db_path = f"{db_path}_corrupted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            try:
                os.rename(db_path, corrupted_db_path)
                logging.warning(f"Corrupted database renamed to: {corrupted_db_path}")
            except OSError as e:
                logging.error(f"Could not rename corrupted database {db_path}: {e}")
                try:
                    os.remove(db_path)
                    logging.warning(f"Corrupted database {db_path} removed as rename failed.")
                except OSError as remove_e:
                    logging.critical(f"Failed to remove or rename corrupted database {db_path}: {remove_e}. Manual intervention likely required.")
                    return False

            # Reinitialize the database
            db_manager = ExtendedDatabaseManager(db_path)
            init_success, init_msg = db_manager.inicializar_banco()
            
            if init_success:
                logging.info(f"Database successfully reinitialized at {db_path}.")
                st.warning("O banco de dados foi reinicializado devido a um problema. Os dados anteriores (exceto o último backup, se bem-sucedido) foram perdidos.")
                return True
            else:
                logging.critical(f"Failed to reinitialize database after corruption: {init_msg}")
                st.error(f"Falha crítica ao tentar recriar o banco de dados: {init_msg}")
                return False
        except Exception as e:
            logging.critical(f"Failed to handle critical database error: {str(e)}\n{traceback.format_exc()}")
            st.error("Ocorreu um erro crítico no sistema de recuperação do banco de dados.")
            return False

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("geladeira.log"),
        logging.StreamHandler()
    ]
)

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

# Função para verificar itens prestes a vencer com tratamento avançado
def verificar_itens_vencimento(db):
    try:
        dias_alerta = 5  # Padrão
        try:
            config = load_config()
            if 'dias_alerta_vencimento' in config:
                dias_alerta = config['dias_alerta_vencimento']
        except Exception:
            pass
            
        itens_proximos = db.obter_itens_proximos_vencimento(dias=dias_alerta)
        
        if not itens_proximos or len(itens_proximos) == 0:
            return
            
        itens_por_urgencia = {
            'hoje': [],
            'amanha': [],
            'semana': [],
            'outro': []
        }
        
        for item in itens_proximos:
            dias = item.get('dias_ate_vencer', 0)
            
            if dias <= 0:
                itens_por_urgencia['hoje'].append(item)
            elif dias == 1:
                itens_por_urgencia['amanha'].append(item)
            elif dias <= 7:
                itens_por_urgencia['semana'].append(item)
            else:
                itens_por_urgencia['outro'].append(item)
        
        total_itens = len(itens_proximos)
        if len(itens_por_urgencia['hoje']) > 0:
            st.error(f"🚨 **URGENTE!** {len(itens_por_urgencia['hoje'])} item(s) vencem HOJE!")
        elif len(itens_por_urgencia['amanha']) > 0:
            st.warning(f"⚠️ **ATENÇÃO!** {len(itens_por_urgencia['amanha'])} item(s) vencem AMANHÃ!")
        else:
            st.warning(f"⚠️ {total_itens} item(s) irão vencer nos próximos dias!")
        
        with st.expander(f"Ver {total_itens} item(s) próximos do vencimento"):
            if itens_por_urgencia['hoje']:
                st.markdown("### 🚨 Vencem HOJE")
                for item in itens_por_urgencia['hoje']:
                    st.markdown(f"**{item['nome']}**: {item['quantidade']} {item['unidade']} - {item.get('localizacao', 'Local desconhecido')}")
                st.divider()
            
            if itens_por_urgencia['amanha']:
                st.markdown("### ⚠️ Vencem AMANHÃ")
                for item in itens_por_urgencia['amanha']:
                    st.markdown(f"**{item['nome']}**: {item['quantidade']} {item['unidade']} - {item.get('localizacao', 'Local desconhecido')}")
                st.divider()
            
            if itens_por_urgencia['semana']:
                st.markdown("### 📅 Vencem esta semana")
                for item in itens_por_urgencia['semana']:
                    st.markdown(f"**{item['nome']}**: Vence em {item['dias_ate_vencer']} dias ({item['data_validade']})")
            
            if itens_por_urgencia['outro']:
                st.markdown("### 📆 Outros itens próximos do vencimento")
                for item in itens_por_urgencia['outro']:
                    st.markdown(f"**{item['nome']}**: Vence em {item['dias_ate_vencer']} dias ({item['data_validade']})")
    
    except Exception as e:
        st.error(f"Erro ao verificar vencimentos: {str(e)}")
        logging.error(f"Erro ao verificar vencimentos: {str(e)}")

@st.cache_resource(ttl=3600)
def carregar_banco_dados(db_path):
    try:
        db_manager = ExtendedDatabaseManager(db_path)
        success, msg = db_manager.verificar_integridade()
        
        if not success:
            st.error(f"Problema com o banco de dados: {msg}")
            if "corrompido" in msg.lower() or "danificado" in msg.lower():
                if DatabaseErrorHandler.handle_critical_error(db_path, msg):
                    st.success("Recuperação realizada. Alguns dados podem ter sido perdidos.")
                    db_manager = ExtendedDatabaseManager(db_path)
                else:
                    st.error("Falha na recuperação. O aplicativo pode estar instável.")
            else:
                st.warning("Tentando inicializar banco de dados...")
                init_success, init_msg = db_manager.inicializar_banco()
                if not init_success:
                    st.error(f"Falha ao inicializar banco: {init_msg}")
                    return None
        
        return db_manager
    except Exception as e:
        st.error(f"Erro crítico ao conectar ao banco de dados: {str(e)}")
        st.error("A aplicação não pode funcionar corretamente. Verifique a conexão com o banco.")
        st.code(traceback.format_exc())
        return None

def main():
    """
    Main application function for the inventory management system.
    This function initializes the application, sets up the user interface,
    and handles navigation between different sections of the app.
    Key responsibilities:
    - Initializes session state and theme settings
    - Connects to the database and handles connection errors
    - Performs periodic database integrity checks
    - Sets up the sidebar with search functionality and navigation options
    - Provides backup and restore functionality
    - Displays version and user information
    - Checks for items nearing expiration
    - Routes to the appropriate view based on user selection
    Error handling:
    - Database connection errors trigger automatic backup attempts
    - Critical initialization errors are displayed to the user
    - Page rendering errors are caught and displayed with stack traces
    Returns:
        None: The function exits early if critical initialization fails
    """
    try:
        if "tema" not in st.session_state:
            st.session_state.tema = "claro"
        
        if "db" not in st.session_state:
            with st.spinner("Conectando ao banco de dados..."):
                db_manager = carregar_banco_dados(DB_PATH)
                if db_manager:
                    st.session_state.db = db_manager
                    logging.info(f"Banco de dados inicializado com sucesso: {DB_PATH}")
                else:
                    st.error("Não foi possível inicializar o banco de dados. Verifique os logs.")
                    logging.error(f"Falha ao inicializar banco de dados: {DB_PATH}")
                    try:
                        backup_success, backup_path = realizar_backup(DB_PATH)
                        if backup_success:
                            st.info(f"Backup automático criado em: {backup_path}")
                            logging.info(f"Backup automático criado: {backup_path}")
                    except Exception as backup_error:
                        logging.error(f"Falha no backup automático: {str(backup_error)}")
                    return
        
        db = st.session_state.db
    
    except Exception as e:
        st.error(f"Erro crítico na inicialização: {str(e)}")
        logging.critical(f"Erro crítico na inicialização: {str(e)}")
        st.code(traceback.format_exc())
        return
    
    # Initialize ultima_verificacao if it doesn't exist
    if "ultima_verificacao" not in st.session_state:
        st.session_state.ultima_verificacao = datetime.now() - timedelta(hours=2)  # Force first verification
        
    if (datetime.now() - st.session_state.ultima_verificacao).total_seconds() > 3600:
        try:
            success, msg = db.verificar_integridade()
            st.session_state.ultima_verificacao = datetime.now()
            if not success:
                st.warning(f"Verificação periódica do banco de dados: {msg}")
        except Exception as e:
            st.error(f"Erro na verificação periódica: {str(e)}")
    
    with st.sidebar:
        st.title("🛒 Menu Principal")

        # Breadcrumbs para navegação
        st.markdown("### 🧭 Navegação Atual")
        st.caption("Você está em: Configurações > Alertas")

        st.text_input(
            "🔍 Busca rápida:", 
            key="busca_global", 
            placeholder="Digite para buscar...",
            help="Busque produtos no inventário pelo nome ou categoria.")
        
        if st.session_state.busca_global and len(st.session_state.busca_global) > 2:
            termo = st.session_state.busca_global
            with st.spinner(f"Buscando '{termo}'..."):
                resultados = db.buscar_itens(termo)
                if resultados:
                    st.success(f"Encontrado(s) {len(resultados)} item(ns)")
                    for item in resultados:
                        if st.button(f"{item['nome']} ({item['quantidade']} {item['unidade']})", key=f"btn_{item['id']}"):
                            st.session_state.item_selecionado = item['id']
                            st.session_state.page = "📋 Inventário Geral"
                            st.rerun()
                else:
                    st.info(f"Nenhum resultado encontrado para '{termo}'")
        
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
             "⚙️ Configurações", "🍽️ Receitas"
            ],
            help="Navegue entre as seções do sistema.")
        
        st.divider()
        
        st.subheader("📤 Backup/Restauração")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📤 Backup", use_container_width=True):
                st.session_state.page = "⚙️ Configurações"
                st.rerun()
        
        with col2:
            if st.button("📥 Restaurar", use_container_width=True):
                st.session_state.page = "⚙️ Configurações"
                st.rerun()
        
        st.divider()
        st.caption(f"Versão: {APP_VERSION}")
        st.caption(f"Data: {CURRENT_DATE}")
        st.caption(f"Usuário: {CURRENT_USER}")
    
    st.markdown("# ⚙️ Configurações Gerais")
    st.markdown("## 🔔 Alertas de Vencimento")

    verificar_itens_vencimento(db)
    
    try:
        # Use session state page if set, otherwise use radio selection
        current_page = st.session_state.get('page', page)
        if current_page == "📋 Inventário Geral":
            mostrar_inventario_geral(db)
        elif current_page == "👶 Thomás":
            mostrar_inventario_thomas(db)
        elif current_page == "👶 Perfil Thomás":
            mostrar_perfil_thomas(db)
        elif current_page == "🔄 Categorias":
            mostrar_categorias(db) 
        elif current_page == "📊 Relatórios":
            mostrar_relatorios(db)
        elif current_page == "📝 Registrar Consumo":
            registrar_consumo(db)
        elif current_page == "🛒 Fazer Feira":
            mostrar_planejamento_feira(db)
        elif current_page == "➕ Adicionar Item":
            adicionar_item_form(db)
        elif current_page == "⚙️ Configurações":
            mostrar_configuracoes(db)
        elif current_page == "🍽️ Receitas":
            mostrar_receitas(db)
    except Exception as e:
        st.error(f"Erro ao carregar a página {page}: {str(e)}")
        st.error("Por favor, recarregue a página ou contate o suporte.")
        st.code(traceback.format_exc())

if __name__ == "__main__":
    main()