import streamlit as st
import pandas as pd
from utils.formatters import (
    format_thomas_status,
    format_leite_status,
    format_compatibilidade,
    format_tendencia_preco,
    highlight_expiration,
    highlight_quantity,
    highlight_health,
    highlight_price_position,
)
import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from utils.constants import (
    UNIDADES_MEDIDA,
    LOCAIS_ARMAZENAMENTO,
    CATEGORIAS_ALIMENTOS,
    TERMOS_LACTEOS,
)
from utils.validador import sanitizar_texto, validar_produto
from datetime import datetime
import traceback

def mostrar_inventario_geral(db):
    """
    Exibe o inventário geral utilizando a biblioteca Streamlit
    """
    st.title("📋 Inventário Geral")
    
    # Carregar dados
    df = db.carregar_inventario()

    # Remapear nomes de colunas para garantir compatibilidade
    df_remapped = df.copy()
    mapping = {
        'id': 'ID', 
        'nome': 'Nome', 
        'quantidade': 'Quantidade', 
        'unidade': 'Unidade',
        'localizacao': 'Localização',
        'categoria': 'Categoria',
        'validade': 'Validade',
        'para_thomas': 'Para Thomas',
        'compatibilidade_thomas': 'Compatibilidade Thomas',
        'nivel_saude': 'Nível Saúde'
    }

    for col_old, col_new in mapping.items():
        if col_old in df.columns and col_new not in df.columns:
            df_remapped[col_new] = df[col_old]

    # Tentar carregar estatísticas de preços (para tendências) com tratamento de erro
    try:
        tendencias_df, _, _ = db.calcular_estatisticas_preco()
        
        # Mesclar dados de tendências com o inventário se ambos existirem
        if not tendencias_df.empty and not df_remapped.empty:
            df_remapped = pd.merge(
                df_remapped, 
                tendencias_df[["ID", "Tendência", "Posição vs Média (%)"]],
                left_on="ID", 
                right_on="ID", 
                how="left"
            )
    except Exception as e:
        logger.warning(f"Não foi possível carregar tendências de preço: {e}")
        # Continuar sem as tendências
    
    # Filtros
    filtro_nome = st.text_input("Filtrar por nome", "")
    if filtro_nome and isinstance(filtro_nome, str):
        if "Nome" in df_remapped.columns:
            df_remapped = df_remapped[df_remapped["Nome"].str.contains(filtro_nome, case=False)]

    # Exibir dados
    if df_remapped.empty:
        st.info("Nenhum item encontrado no inventário.")
    else:
        st.dataframe(df_remapped)

def adicionar_item_form(db):
    """Formulário para adicionar um novo item ao inventário."""
    st.title("➕ Adicionar Item ao Inventário")
    
    with st.form("form_adicionar_item"):
        nome = st.text_input("Nome do Item", placeholder="Ex.: Leite")
        categoria = st.selectbox("Categoria", CATEGORIAS_ALIMENTOS)
        quantidade = st.number_input("Quantidade", min_value=0.01, step=0.1, value=1.0)
        unidade = st.selectbox("Unidade de Medida", UNIDADES_MEDIDA)
        data_validade = st.date_input("Data de Validade", value=None)
        local = st.selectbox("Local de Armazenamento", LOCAIS_ARMAZENAMENTO)
        custo_unitario = st.number_input("Custo Unitário (opcional)", min_value=0.0, step=0.01, format="%.2f")
        para_thomas = st.checkbox("Seguro para Thomas?")
        contem_leite = st.checkbox("Contém Leite?")
        
        submit = st.form_submit_button("Adicionar Item")
        
        if submit:
            dados_formulario = {
                "nome": nome,
                "categoria": categoria,
                "quantidade": quantidade,
                "unidade": unidade,
                "validade": data_validade,
                "localizacao": local,
                "custo_unitario": custo_unitario,
                "para_thomas": para_thomas,
                "contem_leite": contem_leite,
                "perecivel": True if data_validade else False
            }

            valido, mensagem_erro, dados_validados = validar_produto(dados_formulario)

            if not valido:
                for erro in mensagem_erro.split('\n'):
                    st.error(erro)
                return

            item_data_final = {
                "nome": dados_validados.get("nome"),
                "categoria": dados_validados.get("categoria"),
                "quantidade": dados_validados.get("quantidade"),
                "unidade": dados_validados.get("unidade"),
                "validade": dados_validados.get("validade"),
                "localizacao": dados_validados.get("localizacao"),
                "custo_unitario": dados_validados.get("custo_unitario", 0.0),
                "para_thomas": dados_validados.get("para_thomas", False),
                "contem_leite": dados_validados.get("contem_leite", False)
            }
            
            try:
                item_id = db.adicionar_item(**item_data_final)
                st.success(f"Item '{item_data_final['nome']}' adicionado com sucesso! ID: {item_id}")
            except Exception as e:
                st.error(f"Erro ao adicionar item: {str(e)}")
                logger.error(f"Erro ao adicionar item: {str(e)}\n{traceback.format_exc()}")