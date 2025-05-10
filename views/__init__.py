"""
Inicialização do pacote de views para o Sistema GELADEIRA
"""
import logging

logger = logging.getLogger(__name__)

# Configuração inicial do logging para o módulo views
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

# Importações seguras com try/except para evitar erros de inicialização
try:
    from .inventory import mostrar_inventario_geral, adicionar_item_form
except ImportError as e:
    logger.warning(f"Erro ao importar módulo inventory: {e}")
    # Definir stub para função que não existe
    def mostrar_inventario_geral(db):
        import streamlit as st
        st.error("Função mostrar_inventario_geral não implementada")
        
    def adicionar_item_form(db):
        import streamlit as st
        st.error("Função adicionar_item_form não implementada")

try:
    from .thomas import mostrar_inventario_thomas, mostrar_perfil_thomas
except ImportError:
    # Definir stubs para funções que não existem
    def mostrar_inventario_thomas(db):
        import streamlit as st
        st.error("Função mostrar_inventario_thomas não implementada")
        
    def mostrar_perfil_thomas(db):
        import streamlit as st
        st.error("Função mostrar_perfil_thomas não implementada")

try:
    from .reports import mostrar_relatorios
except ImportError:
    def mostrar_relatorios(db):
        import streamlit as st
        st.error("Função mostrar_relatorios não implementada")

try:
    from .consumption import registrar_consumo, mostrar_categorias
except ImportError:
    def registrar_consumo(db):
        import streamlit as st
        st.error("Função registrar_consumo não implementada")
        
    def mostrar_categorias(db):
        import streamlit as st
        st.error("Função mostrar_categorias não implementada")

try:
    from .shopping import mostrar_planejamento_feira
except ImportError:
    def mostrar_planejamento_feira(db):
        import streamlit as st
        st.error("Função mostrar_planejamento_feira não implementada")

try:
    from .settings import mostrar_configuracoes
except ImportError:
    def mostrar_configuracoes(db):
        import streamlit as st
        st.error("Função mostrar_configuracoes não implementada")

try:
    from .receitas import mostrar_receitas
except ImportError:
    def mostrar_receitas(db):
        import streamlit as st
        st.error("Função mostrar_receitas não implementada")

# Definir __all__ para uso com import *
__all__ = [
    'mostrar_inventario_geral',
    'adicionar_item_form',
    'mostrar_inventario_thomas',
    'mostrar_perfil_thomas',
    'mostrar_relatorios',
    'registrar_consumo',
    'mostrar_categorias',
    'mostrar_planejamento_feira',
    'mostrar_configuracoes',
    'mostrar_receitas'
]
