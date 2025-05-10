from views.inventario import mostrar_inventario_geral
from views.item import adicionar_item_form
from utils.validators import validar_nome

def configurar_rotas(db, page):
    """
    Configura as rotas da aplicação baseado na página selecionada
    
    Args:
        db: Conexão com o banco de dados
        page: String contendo o nome da página atual
    """
    if page == "📋 Inventário Geral":
        mostrar_inventario_geral(db)
    elif page == "➕ Adicionar Item":
        adicionar_item_form(db)
    else:
        # Página padrão ou tratamento de erro
        mostrar_inventario_geral(db)