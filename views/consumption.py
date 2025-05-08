import streamlit as st
import pandas as pd
import datetime
from utils.formatters import *
from utils.constants import *

def registrar_consumo(db):
    st.title("📝 Registrar Consumo")
    
    # Carregar inventário
    df = db.carregar_inventario()
    
    if df.empty:
        st.info("Ainda não há itens cadastrados para registrar consumo.")
        return
    
    # Formulário para registrar consumo
    with st.form("form_consumo"):
        st.subheader("Registrar Consumo de Item")
        
        col1, col2 = st.columns(2)
        
        with col1:
            item_id = st.selectbox(
                "Selecione o item consumido", 
                options=df["ID"].tolist(),
                format_func=lambda x: df[df["ID"] == x]["Nome"].values[0]
            )
            
            # Tipo de consumo
            tipo_consumo = st.radio(
                "Tipo de consumo",
                ["Consumo geral", "Consumo de Thomás"]
            )
            para_thomas = tipo_consumo == "Consumo de Thomás"
            
            # Verificar compatibilidade para Thomas
            pode_registrar = True
            if para_thomas:
                if "Para Thomas" in df.columns:
                    is_thomas_item = bool(df[df["ID"] == item_id]["Para Thomas"].values[0])
                    if not is_thomas_item:
                        st.warning("⚠️ Este item não está marcado como adequado para Thomás. Deseja continuar mesmo assim?")
                        confirma_thomas = st.checkbox("Sim, registrar mesmo assim", key="confirma_consumo_thomas")
                        pode_registrar = confirma_thomas
                
                # Verificar compatibilidade
                if "Compatibilidade Thomas" in df.columns:
                    compatibilidade = int(df[df["ID"] == item_id]["Compatibilidade Thomas"].values[0])
                    if compatibilidade == 0:  # Não recomendado
                        st.error("⚠️ **ALERTA!** Este alimento NÃO É RECOMENDADO para Thomás!")
                        confirma_alerta = st.checkbox("Confirmo que este alimento é adequado para Thomás mesmo não sendo recomendado")
                        pode_registrar = confirma_alerta
                    elif compatibilidade == 1:  # Verificar
                        st.warning("⚠️ Verifique os ingredientes antes de dar a Thomás.")
                        
            # Mostrar nutrientes
            item_selecionado = df[df["ID"] == item_id]
            if para_thomas:
                st.subheader("Informações Nutricionais")
                nutrientes_thomas = ["Proteínas (g)", "Cálcio (mg)", "Ferro (mg)", 
                                    "Vitamina C (mg)", "Vitamina D (mcg)"]
                
                for nutriente in nutrientes_thomas:
                    if nutriente in item_selecionado.columns and pd.notna(item_selecionado[nutriente].values[0]):
                        valor = float(item_selecionado[nutriente].values[0])
                        st.info(f"{nutriente}: {valor:.1f}")
            
        with col2:
            # Obter unidade e quantidade máxima do item selecionado
            item_selecionado = df[df["ID"] == item_id]
            unidade = item_selecionado["Unidade"].values[0] if "Unidade" in item_selecionado.columns else "unidade"
            qtd_max = float(item_selecionado["Quantidade"].values[0])
            
            qtd_consumida = st.number_input(
                f"Quantidade consumida ({unidade})",
                min_value=0.1, 
                max_value=qtd_max,
                value=min(1.0, qtd_max),
                step=0.1
            )
            
            data_consumo = st.date_input(
                "Data do consumo",
                value=datetime.date.today()
            )
            
            # Calcular valores nutricionais consumidos
            if "Calorias/100g" in item_selecionado.columns and pd.notna(item_selecionado["Calorias/100g"].values[0]):
                calorias = float(item_selecionado["Calorias/100g"].values[0]) * qtd_consumida / 100
                st.text(f"Calorias consumidas: {calorias:.1f} kcal")
            
            if para_thomas and "Cálcio (mg)" in item_selecionado.columns and pd.notna(item_selecionado["Cálcio (mg)"].values[0]):
                calcio = float(item_selecionado["Cálcio (mg)"].values[0]) * qtd_consumida / 100
                necessidades = db.obter_necessidades_thomas()
                necessidade_calcio = next((n["quantidade_diaria"] for n in necessidades if n["nutriente"] == "Cálcio"), 1000)
                
                percentual = (calcio / necessidade_calcio) * 100
                st.text(f"Cálcio consumido: {calcio:.1f} mg ({percentual:.1f}% da necessidade diária)")
        
        # Validar antes de submeter
        erros = []
        if qtd_consumida <= 0:
            erros.append("Quantidade consumida deve ser maior que zero")
        if qtd_consumida > qtd_max:
            erros.append(f"Quantidade máxima disponível é {qtd_max} {unidade}")
        if para_thomas and not pode_registrar:
            erros.append("Verificar compatibilidade para Thomás")
        
        # Botão de submissão
        if st.form_submit_button("✅ Registrar Consumo"):
            if erros:
                for erro in erros:
                    st.error(erro)
            else:
                success, msg = db.registrar_consumo(item_id, qtd_consumida, para_thomas=para_thomas, data=data_consumo)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

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
        # Contagem por categoria para visão geral
        if categoria == "Todas" and "Categoria" in df.columns:
            st.subheader("Distribuição por Categoria")
            contagem = df.groupby("Categoria").size().reset_index(name="Quantidade de Itens")
            
            # Usar gráfico de barras do Streamlit
            st.bar_chart(contagem.set_index("Categoria")["Quantidade de Itens"])
        
        # Preparar dataframe para exibição
        df_display = df.copy()
        
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
                df_style.data[colunas_exibir], 
                use_container_width=True,
                height=400,
                column_config=config_dict
            )
        except Exception as e:
            st.error(f"Erro ao exibir tabela: {e}")
            st.dataframe(df_display[colunas_exibir])
        
        # Resumo da categoria
        if categoria != "Todas":
            st.subheader(f"Resumo da categoria: {categoria}")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                total_itens = len(df)
                st.metric("Total de itens", total_itens)
                
            with col2:
                para_thomas = len(df[df["Para Thomas"] == 1]) if "Para Thomas" in df.columns else 0
                st.metric("Itens para Thomás", para_thomas)
                
            with col3:
                if "Nível Saúde" in df.columns:
                    nivel_saude = df["Nível Saúde"].mean()
                    status = "Saudável" if nivel_saude < 1.5 else ("Intermediário" if nivel_saude < 2.5 else "Alto impacto")
                    st.metric("Nível de saúde médio", f"{nivel_saude:.1f} - {status}")
                    
            with col4:
                if "Compatibilidade Thomas" in df.columns:
                    compatibilidade_thomas = df["Compatibilidade Thomas"].mean()
                    nivel_texto = "Não recomendada" if compatibilidade_thomas < 0.5 else ("Verificar" if compatibilidade_thomas < 1.5 else "Segura")
                    st.metric("Compatibilidade média", f"{nivel_texto}")