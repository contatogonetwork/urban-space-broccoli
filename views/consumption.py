import streamlit as st
import pandas as pd
import datetime
import logging
from typing import List, Dict, Tuple, Optional
from utils.formatters import *
from utils.constants import *

# Configurar logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def validar_consumo(qtd_consumida: float, qtd_max: float, para_thomas: bool, pode_registrar: bool) -> List[str]:
    """
    Valida os dados de consumo antes de registrar.

    Args:
        qtd_consumida (float): Quantidade consumida.
        qtd_max (float): Quantidade máxima disponível.
        para_thomas (bool): Indica se o consumo é para Thomás.
        pode_registrar (bool): Indica se o registro é permitido.

    Returns:
        list: Lista de mensagens de erro, se houver.
    """
    erros = []
    if qtd_consumida <= 0:
        erros.append("A quantidade consumida deve ser maior que zero.")
    if qtd_consumida > qtd_max:
        erros.append("A quantidade consumida não pode ser maior que o disponível.")
    if para_thomas and not pode_registrar:
        erros.append("Não é permitido registrar consumo para Thomás neste item.")
    return erros

def calcular_nutrientes_consumidos(item_selecionado: pd.DataFrame, qtd_consumida: float, db) -> Dict[str, Tuple[float, Optional[float]]]:
    """
    Calcula os nutrientes consumidos com base na quantidade consumida.

    Args:
        item_selecionado (DataFrame): Dados do item selecionado.
        qtd_consumida (float): Quantidade consumida.
        db: Objeto de banco de dados para obter necessidades nutricionais.

    Returns:
        dict: Informações nutricionais calculadas.
    """
    nutrientes_info = {}
    
    # Verificar calorias tanto na versão nova quanto na antiga da coluna
    if "Calorias/100g" in item_selecionado.columns and pd.notna(item_selecionado["Calorias/100g"].values[0]):
        calorias = float(item_selecionado["Calorias/100g"].values[0]) * qtd_consumida / 100
        nutrientes_info["Calorias"] = calorias
    elif "calorias_100g" in item_selecionado.columns and pd.notna(item_selecionado["calorias_100g"].values[0]):
        calorias = float(item_selecionado["calorias_100g"].values[0]) * qtd_consumida / 100
        nutrientes_info["Calorias"] = calorias

    # Verificar cálcio tanto na versão nova quanto na antiga da coluna
    if "Cálcio (mg)" in item_selecionado.columns and pd.notna(item_selecionado["Cálcio (mg)"].values[0]):
        calcio = float(item_selecionado["Cálcio (mg)"].values[0]) * qtd_consumida / 100
        necessidades = db.obter_necessidades_thomas()
        necessidade_calcio = next((n["quantidade_diaria"] for n in necessidades if n["nutriente"] == "Cálcio"), 1000)
        percentual = (calcio / necessidade_calcio) * 100
        nutrientes_info["Cálcio"] = (calcio, percentual)
    elif "calcio_mg" in item_selecionado.columns and pd.notna(item_selecionado["calcio_mg"].values[0]):
        calcio = float(item_selecionado["calcio_mg"].values[0]) * qtd_consumida / 100
        necessidades = db.obter_necessidades_thomas()
        necessidade_calcio = next((n["quantidade_diaria"] for n in necessidades if n["nutriente"] == "Cálcio"), 1000)
        percentual = (calcio / necessidade_calcio) * 100
        nutrientes_info["Cálcio"] = (calcio, percentual)

    return nutrientes_info

def validar_data_consumo(data_consumo: datetime.date, data_compra: datetime.date) -> Optional[str]:
    """
    Valida se a data de consumo não é anterior à data de compra.

    Args:
        data_consumo (datetime.date): Data do consumo.
        data_compra (datetime.date): Data de compra do item.

    Returns:
        Optional[str]: Mensagem de erro, se houver.
    """
    # Garantir que ambos sejam do tipo datetime.date
    if isinstance(data_consumo, str):
        data_consumo = datetime.datetime.strptime(data_consumo, "%Y-%m-%d").date()
    if isinstance(data_compra, str):
        data_compra = datetime.datetime.strptime(data_compra, "%Y-%m-%d").date()

    if data_consumo < data_compra:
        return "A data de consumo não pode ser anterior à data de compra do item."
    return None

def registrar_consumo(db):
    """
    Registers the consumption of an item from the inventory.
    This function provides a Streamlit interface for users to log the consumption of items
    from an inventory. It includes features for selecting an item, specifying the type of 
    consumption (general or specific to Thomás), and validating nutritional compatibility 
    for Thomás. The function also calculates and displays nutritional information based on 
    the selected item and quantity consumed.
    """
    st.title("📝 Registrar Consumo")
    
    # Carregar inventário
    df = db.carregar_inventario()
    
    if df.empty:
        st.info("Ainda não há itens cadastrados para registrar consumo.")
        return
    
    # Remapear nomes de colunas para garantir compatibilidade
    df_remapped = df.copy()
    
    # Verificar e renomear colunas para exibição
    mapping = {
        'id': 'ID', 
        'nome': 'Nome', 
        'quantidade': 'Quantidade', 
        'unidade': 'Unidade',
        'localizacao': 'Localização',
        'validade': 'Validade',
        'data_cadastro': 'Data Compra',
        'para_thomas': 'Para Thomas',
        'compatibilidade_thomas': 'Compatibilidade Thomas',
        'calorias_100g': 'Calorias/100g',
        'calcio_mg': 'Cálcio (mg)'
    }
    
    for col_old, col_new in mapping.items():
        if col_old in df.columns and col_new not in df.columns:
            df_remapped[col_new] = df[col_old]
    
    # Formulário para registrar consumo
    with st.form("form_consumo"):
        st.subheader("Registrar Consumo de Item")
        
        col1, col2 = st.columns(2)
        
        with col1:
            item_id = st.selectbox(
                "Selecione o item consumido", 
                options=df_remapped["ID"].tolist(),
                format_func=lambda x: df_remapped[df_remapped["ID"] == x]["Nome"].values[0]
            )
            
            tipo_consumo = st.radio(
                "Tipo de consumo",
                ["Consumo geral", "Consumo de Thomás"]
            )
            para_thomas = tipo_consumo == "Consumo de Thomás"
            
            pode_registrar = True
            if para_thomas:
                if "Para Thomas" in df_remapped.columns:
                    is_thomas_item = bool(df_remapped[df_remapped["ID"] == item_id]["Para Thomas"].values[0])
                    if not is_thomas_item:
                        st.warning("⚠️ Este item não está marcado como adequado para Thomás. Deseja continuar mesmo assim?")
                        confirma_thomas = st.checkbox("Sim, registrar mesmo assim", key="confirma_consumo_thomas")
                        pode_registrar = confirma_thomas
                
                if "Compatibilidade Thomas" in df_remapped.columns:
                    compatibilidade = int(df_remapped[df_remapped["ID"] == item_id]["Compatibilidade Thomas"].values[0])
                    if compatibilidade == 0:
                        st.error("⚠️ **ALERTA!** Este alimento NÃO É RECOMENDADO para Thomás!")
                        confirma_alerta = st.checkbox("Confirmo que este alimento é adequado para Thomás mesmo não sendo recomendado")
                        pode_registrar = confirma_alerta
                    elif compatibilidade == 1:
                        st.warning("⚠️ Verifique os ingredientes antes de dar a Thomás.")
        
        with col2:
            item_selecionado = df_remapped[df_remapped["ID"] == int(item_id)]
            unidade = item_selecionado["Unidade"].values[0] if "Unidade" in item_selecionado.columns else "unidade"
            qtd_max = float(item_selecionado["Quantidade"].values[0]) if "Quantidade" in item_selecionado.columns else 0.0
            data_compra = item_selecionado["Data Compra"].values[0] if "Data Compra" in item_selecionado.columns else datetime.date.today()
            
            qtd_consumida = st.number_input(
                f"Quantidade consumida ({unidade})",
                min_value=0.01, 
                max_value=qtd_max,
                value=min(1.0, qtd_max),
                step=0.01
            )
            
            data_consumo = st.date_input(
                "Data do consumo",
                value=datetime.date.today(),
                max_value=datetime.date.today()
            )
        
        erros = validar_consumo(qtd_consumida, qtd_max, para_thomas, pode_registrar)
        erro_data = validar_data_consumo(data_consumo, data_compra)
        if erro_data:
            erros.append(erro_data)
        
        if st.form_submit_button("✅ Registrar Consumo"):
            if erros:
                for erro in erros:
                    st.error(erro)
            else:
                try:
                    sucesso, msg = db.registrar_consumo(item_id, qtd_consumida, para_thomas=para_thomas, data=data_consumo)
                    if sucesso:
                        st.success(msg)
                        nutrientes_info = calcular_nutrientes_consumidos(item_selecionado, qtd_consumida, db)
                        if "Calorias" in nutrientes_info:
                            st.text(f"Calorias consumidas: {nutrientes_info['Calorias']:.1f} kcal")
                        if "Cálcio" in nutrientes_info:
                            calcio, percentual = nutrientes_info["Cálcio"]
                            st.text(f"Cálcio consumido: {calcio:.1f} mg ({percentual:.1f}% da necessidade diária)")
                        st.rerun()
                    else:
                        st.error(msg)
                except Exception as e:
                    logger.error(f"Erro ao registrar consumo: {str(e)}")
                    st.error(f"Erro ao registrar consumo: {str(e)}")

def mostrar_categorias(db):
    st.title("🔄 Alimentos por Categoria")
    
    # Obter categorias cadastradas
    categorias = db.obter_categorias()
    
    if not categorias:
        st.info("Ainda não há categorias cadastradas. Adicione itens para começar.")
        return
    
    # Selecionar categoria
    categoria = st.selectbox(
        "Selecione uma categoria para visualizar", 
        options=["Todas"] + categorias
    )
    
    # Carregar dados
    if categoria == "Todas":
        df = db.carregar_inventario()
    else:
        df = db.carregar_por_categoria(categoria)
    
    # Exibir dados
    if df.empty:
        st.info(f"Nenhum item encontrado na categoria {categoria}.")
    else:
        # Remapear nomes de colunas para garantir compatibilidade
        df_remapped = df.copy()
        
        # Verificar e renomear colunas para exibição
        mapping = {
            'id': 'ID', 
            'nome': 'Nome', 
            'quantidade': 'Quantidade', 
            'unidade': 'Unidade',
            'localizacao': 'Localização',
            'categoria': 'Categoria',
            'validade': 'Validade',
            'para_thomas': 'Para Thomas',
            'contem_leite': 'Contém Leite',
            'compatibilidade_thomas': 'Compatibilidade Thomas',
            'nivel_saude': 'Nível Saúde'
        }
        
        for col_old, col_new in mapping.items():
            if col_old in df.columns and col_new not in df.columns:
                df_remapped[col_new] = df[col_old]
        
        # Contagem por categoria para visão geral
        if categoria == "Todas" and "Categoria" in df_remapped.columns:
            st.subheader("Distribuição por Categoria")
            contagem = df_remapped.groupby("Categoria").size().reset_index(name="Quantidade de Itens")
            
            # Usar gráfico de barras do Streamlit
            st.bar_chart(contagem.set_index("Categoria")["Quantidade de Itens"])
        
        # Preparar dataframe para exibição
        df_display = df_remapped.copy()
        
        # Aplicar formatação
        if "Para Thomas" in df_display.columns:
            df_display["Para Thomas"] = df_display["Para Thomas"].apply(format_thomas_status)
        if "Contém Leite" in df_display.columns:
            df_display["Contém Leite"] = df_display["Contém Leite"].apply(format_leite_status)
        if "Compatibilidade Thomas" in df_display.columns:
            df_display["Compatibilidade Thomas"] = df_display["Compatibilidade Thomas"].apply(format_compatibilidade)
        
        # Selecionar colunas para exibição baseado nas disponíveis
        available_columns = df_display.columns.tolist()
        default_columns = ["ID", "Nome", "Para Thomas", "Compatibilidade Thomas"]
        
        if "Contém Leite" in available_columns:
            default_columns.append("Contém Leite")
            
        default_columns.extend(["Quantidade", "Unidade", "Localização"])
        
        if "Validade" in available_columns:
            default_columns.append("Validade")
            
        if "Dias Até Vencer" in available_columns:
            default_columns.append("Dias Até Vencer")
            
        if "Nível Saúde" in available_columns:
            default_columns.append("Nível Saúde")
            
        # Filtrar colunas existentes
        colunas_exibir = [col for col in default_columns if col in available_columns]
        
        # Aplicar estilos possíveis
        styling_dict = {}
        if "Dias Até Vencer" in available_columns:
            styling_dict["Dias Até Vencer"] = highlight_expiration
        if "Nível Saúde" in available_columns:
            styling_dict["Nível Saúde"] = highlight_health
            
        # Criar estilo
        df_style = df_display.style
        for col, style_func in styling_dict.items():
            df_style = df_style.applymap(style_func, subset=[col])
        
        # Título dinâmico
        if categoria == "Todas":
            st.subheader("Todos os itens")
        else:
            st.subheader(f"Itens na categoria: {categoria}")
        
        # Configuração de colunas
        config_dict = {}
        if "ID" in colunas_exibir:
            config_dict["ID"] = st.column_config.NumberColumn("ID", width="small")
        if "Nome" in colunas_exibir:
            config_dict["Nome"] = st.column_config.TextColumn("Nome", width="medium")
        if "Para Thomas" in colunas_exibir:
            config_dict["Para Thomas"] = st.column_config.TextColumn("⭐ Thomás", width="small")
        if "Compatibilidade Thomas" in colunas_exibir:
            config_dict["Compatibilidade Thomas"] = st.column_config.TextColumn(
                "Compatibilidade", 
                width="small", 
                help="🟢=Seguro, 🟡=Verificar, 🔴=Não recomendado"
            )
        if "Contém Leite" in colunas_exibir:
            config_dict["Contém Leite"] = st.column_config.TextColumn("🥛 Leite", width="small")
        if "Quantidade" in colunas_exibir:
            config_dict["Quantidade"] = st.column_config.NumberColumn("Quantidade", format="%.2f")
        if "Unidade" in colunas_exibir:
            config_dict["Unidade"] = st.column_config.TextColumn("Unidade", width="small")
        if "Localização" in colunas_exibir:
            config_dict["Localização"] = st.column_config.TextColumn("Localização")
        if "Validade" in colunas_exibir:
            config_dict["Validade"] = st.column_config.DateColumn("Validade", format="DD/MM/YYYY")
        if "Dias Até Vencer" in colunas_exibir:
            config_dict["Dias Até Vencer"] = st.column_config.ProgressColumn(
                "Dias Até Vencer",
                format="%d dias",
                min_value=0,
                max_value=30,
            )
        if "Nível Saúde" in colunas_exibir:
            config_dict["Nível Saúde"] = st.column_config.NumberColumn(
                "Nível Saúde",
                format="%d",
                help="1=Saudável, 2=Intermediário, 3=Alto impacto"
            )
        
        # Exibir dataframe
        try:
            st.dataframe(
                df_display[colunas_exibir], 
                use_container_width=True,
                column_config=config_dict,
                hide_index=True
            )
        except Exception as e:
            logger.error(f"Erro ao exibir dataframe: {str(e)}")
            st.error(f"Erro ao exibir os dados: {str(e)}")