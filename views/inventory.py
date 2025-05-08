import streamlit as st
import pandas as pd
from utils.formatters import *
from utils.constants import *
import datetime

def mostrar_inventario_geral(db):
    st.title("📋 Inventário Geral")
    
    # Carregar dados
    df = db.carregar_inventario()
    
    # Tentar carregar estatísticas de preços (para tendências) com tratamento de erro
    try:
        tendencias_df, _, _ = db.calcular_estatisticas_preco()
        
        # Mesclar dados de tendências com o inventário se ambos existirem
        if not tendencias_df.empty and not df.empty:
            df = pd.merge(
                df, 
                tendencias_df[["ID", "Tendência", "Posição vs Média (%)"]],
                left_on="ID", 
                right_on="ID", 
                how="left"
            )
    except Exception as e:
        st.warning(f"Não foi possível carregar tendências de preço: {e}")
        # Continuar sem as tendências
        pass
    
    # Filtros
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        filtro_nome = st.text_input("🔍 Filtrar por nome:", key="filtro_nome_geral")
    with col2:
        localizacoes = sorted(df["Localização"].unique()) if not df.empty else []
        filtro_local = st.multiselect("📍 Filtrar por localização:", options=localizacoes, key="filtro_local_geral")
    with col3:
        categorias = sorted(df["Categoria"].unique()) if not df.empty and "Categoria" in df.columns else []
        filtro_categoria = st.multiselect("🏷️ Filtrar por categoria:", options=categorias, key="filtro_categoria_geral")
    with col4:
        filtro_vencimento = st.slider(
            "⏱️ Filtrar por dias até vencer:", 
            min_value=0, 
            max_value=30,
            value=(0, 30),
            disabled=df.empty,
            key="filtro_vencimento_geral"
        )
    
    # Aplicar filtros
    if not df.empty:
        if filtro_nome:
            df = df[df["Nome"].str.contains(filtro_nome, case=False)]
        if filtro_local:
            df = df[df["Localização"].isin(filtro_local)]
        if filtro_categoria and "Categoria" in df.columns:
            df = df[df["Categoria"].isin(filtro_categoria)]
        if "Dias Até Vencer" in df.columns:
            df = df[(df["Perecível"] == 0) | 
                  (df["Dias Até Vencer"].isna()) |
                  ((df["Dias Até Vencer"] >= filtro_vencimento[0]) & 
                   (df["Dias Até Vencer"] <= filtro_vencimento[1]))]
    
    # Exibir dados
    if df.empty:
        st.info("Nenhum item cadastrado ou correspondente aos filtros.")
    else:
        # Preparar dataframe para exibição
        df_display = df.copy()
        
        # Aplicar formatação para valores de colunas específicas
        if "Para Thomas" in df_display.columns:
            df_display["Para Thomas"] = df_display["Para Thomas"].apply(format_thomas_status)
        if "Contém Leite" in df_display.columns:
            df_display["Contém Leite"] = df_display["Contém Leite"].apply(format_leite_status)
        if "Compatibilidade Thomas" in df_display.columns:
            df_display["Compatibilidade Thomas"] = df_display["Compatibilidade Thomas"].apply(format_compatibilidade)
            
        # Adicionar coluna para tendência de preço
        if "Tendência" in df_display.columns:
            df_display["Tendência Preço"] = df_display["Tendência"].apply(format_tendencia_preco)
        
        # Selecionar colunas para exibição baseado nas disponíveis
        available_columns = df_display.columns.tolist()
        
        # Reordenar colunas para colocar Tendência e Thomás mais visíveis
        default_columns = ["ID", "Nome"]
        
        if "Tendência Preço" in available_columns:
            default_columns.append("Tendência Preço")
            
        default_columns.extend(["Para Thomas", "Compatibilidade Thomas"])
        
        if "Contém Leite" in available_columns:
            default_columns.append("Contém Leite")
            
        default_columns.extend(["Quantidade", "Unidade", "Localização"])
            
        if "Categoria" in available_columns:
            default_columns.append("Categoria")
            
        default_columns.extend(["Validade", "Dias Até Vencer"])
        
        if "Custo Unitário" in available_columns:
            default_columns.append("Custo Unitário")
            
        if "Posição vs Média (%)" in available_columns:
            default_columns.append("Posição vs Média (%)")
            
        if "Nível Saúde" in available_columns:
            default_columns.append("Nível Saúde")
            
        # Filtrar colunas existentes
        colunas_exibir = [col for col in default_columns if col in available_columns]
        
        # Aplicar estilos possíveis
        styling_dict = {}
        if "Dias Até Vencer" in available_columns:
            styling_dict["Dias Até Vencer"] = highlight_expiration
        if "Quantidade" in available_columns:
            styling_dict["Quantidade"] = highlight_quantity
        if "Nível Saúde" in available_columns:
            styling_dict["Nível Saúde"] = highlight_health
        if "Posição vs Média (%)" in available_columns:
            styling_dict["Posição vs Média (%)"] = highlight_price_position
            
        # Criar estilo
        df_style = df_display.style
        for col, style_func in styling_dict.items():
            df_style = df_style.applymap(style_func, subset=[col])
            
        # Preparar configurações de colunas
        config_dict = {}
        if "ID" in colunas_exibir:
            config_dict["ID"] = st.column_config.NumberColumn("ID", width="small")
        if "Nome" in colunas_exibir:
            config_dict["Nome"] = st.column_config.TextColumn("Nome", width="medium")
        if "Tendência Preço" in colunas_exibir:
            config_dict["Tendência Preço"] = st.column_config.TextColumn(
                "Tendência", 
                width="small", 
                help="🔺=Preço acima da média, ➖=Na média, 🔽=Abaixo da média"
            )
        if "Para Thomas" in colunas_exibir:
            config_dict["Para Thomas"] = st.column_config.TextColumn("⭐ Thomás", width="small", help="Item disponível para Thomás")
        if "Compatibilidade Thomas" in colunas_exibir:
            config_dict["Compatibilidade Thomas"] = st.column_config.TextColumn(
                "Compatibilidade", 
                width="small", 
                help="🟢=Seguro, 🟡=Verificar, 🔴=Não recomendado"
            )
        if "Contém Leite" in colunas_exibir:
            config_dict["Contém Leite"] = st.column_config.TextColumn("🥛 Leite", width="small", help="Contém derivados lácteos")
        if "Quantidade" in colunas_exibir:
            config_dict["Quantidade"] = st.column_config.NumberColumn("Quantidade", format="%.2f")
        if "Unidade" in colunas_exibir:
            config_dict["Unidade"] = st.column_config.TextColumn("Unidade", width="small")
        if "Localização" in colunas_exibir:
            config_dict["Localização"] = st.column_config.TextColumn("Localização")
        if "Categoria" in colunas_exibir:
            config_dict["Categoria"] = st.column_config.TextColumn("Categoria")
        if "Validade" in colunas_exibir:
            config_dict["Validade"] = st.column_config.DateColumn("Validade", format="DD/MM/YYYY")
        if "Dias Até Vencer" in colunas_exibir:
            config_dict["Dias Até Vencer"] = st.column_config.ProgressColumn(
                "Dias Até Vencer",
                format="%d dias",
                min_value=0,
                max_value=30,
            )
        if "Custo Unitário" in colunas_exibir:
            config_dict["Custo Unitário"] = st.column_config.TextColumn("Custo Unitário")
        if "Posição vs Média (%)" in colunas_exibir:
            config_dict["Posição vs Média (%)"] = st.column_config.NumberColumn(
                "vs Média (%)",
                format="%.1f%%"
            )
        if "Nível Saúde" in colunas_exibir:
            config_dict["Nível Saúde"] = st.column_config.NumberColumn(
                "Nível Saúde",
                format="%d",
                help="1=Saudável, 2=Intermediário, 3=Alto impacto"
            )
        
        # Exibir dataframe com as colunas disponíveis
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
            
        # Adicionar legenda dos indicadores de preço
        if "Tendência Preço" in df_display.columns:
            st.markdown("""
            <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                <strong>Legenda de indicadores de preço:</strong>
                <span style="color: #cc0000; margin-left: 10px;">🔺 Preço acima da média</span>
                <span style="color: #806600; margin-left: 10px;">➖ Preço na média</span>
                <span style="color: #1e6f50; margin-left: 10px;">🔽 Preço abaixo da média</span>
            </div>
            """, unsafe_allow_html=True)
        
        # Legenda de tendência de preços
        with st.expander("ℹ️ Legenda de Tendências de Preço"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown('<div style="background-color: #ffcccc; color: #cc0000; padding: 10px; border-left: 3px solid #cc0000; border-radius: 5px;">🔺 Preço acima da média</div>', unsafe_allow_html=True)
            with col2:
                st.markdown('<div style="background-color: #fff4cc; color: #806600; padding: 10px; border-left: 3px solid #ffcc00; border-radius: 5px;">➖ Preço na média</div>', unsafe_allow_html=True)
            with col3:
                st.markdown('<div style="background-color: #d5f5d5; color: #1e6f50; padding: 10px; border-left: 3px solid #4caf50; border-radius: 5px;">🔽 Preço abaixo da média</div>', unsafe_allow_html=True)
            
            st.markdown("""
            **Como são calculadas as tendências:**
            - Utilizamos dados históricos de preços para cada item
            - Calculamos a média de preço por unidade ao longo do tempo
            - Comparamos o preço atual com a média histórica
            - Classificamos como "acima da média" se o preço atual estiver mais de 5% acima da média
            - Classificamos como "abaixo da média" se o preço atual estiver mais de 5% abaixo da média
            - Classificamos como "na média" se o preço estiver dentro de 5% da média
            """)
        
        # Legenda de compatibilidade
        with st.expander("ℹ️ Legenda de compatibilidade para Thomás"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown('<div style="background-color: #d5f5d5; color: #1e6f50; padding: 10px; border-left: 3px solid #4caf50; border-radius: 5px;">🟢 Seguro para Thomás</div>', unsafe_allow_html=True)
            with col2:
                st.markdown('<div style="background-color: #fff4cc; color: #806600; padding: 10px; border-left: 3px solid #ffcc00; border-radius: 5px;">🟡 Verificar ingredientes</div>', unsafe_allow_html=True)
            with col3:
                st.markdown('<div style="background-color: #ffcccc; color: #cc0000; padding: 10px; border-left: 3px solid #cc0000; border-radius: 5px;">🔴 Não recomendado</div>', unsafe_allow_html=True)
                
        # Resto da função permanece igual

def editar_item(db, item_id):
    """Formulário para editar um item"""
    df = db.carregar_inventario()
    item_data = df[df["ID"] == item_id]
    
    if item_data.empty:
        st.error(f"Item ID {item_id} não encontrado!")
        return
        
    item = item_data.iloc[0]
    
    with st.form("form_edit"):
        col1, col2 = st.columns(2)
        
        with col1:
            nome = st.text_input("Nome do item", value=item["Nome"])
            
            # Quantidade e unidade lado a lado
            qcol1, qcol2 = st.columns([2, 1])
            with qcol1:
                qtd = st.number_input(
                    "Quantidade", 
                    min_value=0.0, 
                    value=float(item["Quantidade"]), 
                    step=0.1, 
                    format="%.2f"
                )
            with qcol2:
                unidade = st.selectbox(
                    "Unidade", 
                    options=UNIDADES_MEDIDA,
                    index=UNIDADES_MEDIDA.index(item["Unidade"]) if "Unidade" in item and item["Unidade"] in UNIDADES_MEDIDA else 0
                )
            
            # Localização e categoria
            local = st.selectbox(
                "Local de armazenamento", 
                options=LOCAIS_ARMAZENAMENTO,
                index=LOCAIS_ARMAZENAMENTO.index(item["Localização"]) 
                      if item["Localização"] in LOCAIS_ARMAZENAMENTO else 0
            )
            
            # Categoria (se existir na tabela)
            if "Categoria" in item:
                categoria = st.selectbox(
                    "Categoria", 
                    options=CATEGORIAS_ALIMENTOS,
                    index=CATEGORIAS_ALIMENTOS.index(item["Categoria"]) 
                          if item["Categoria"] in CATEGORIAS_ALIMENTOS else 0
                )
            else:
                categoria = st.selectbox("Categoria", options=CATEGORIAS_ALIMENTOS)
            
            # Perecível e validade
            perecivel = st.checkbox("É perecível?", value=bool(item["Perecível"]))
            
            validade = None
            if perecivel:
                try:
                    val_date = datetime.datetime.strptime(item["Validade"], '%Y-%m-%d').date() \
                        if item["Validade"] else datetime.date.today()
                except:
                    val_date = datetime.date.today()
                    
                validade = st.date_input(
                    "Data de validade",
                    min_value=datetime.date.today(),
                    value=val_date
                )
                
            # Ingredientes
            ingredientes = st.text_area(
                "Ingredientes", 
                value=item["Ingredientes"] if "Ingredientes" in item and pd.notna(item["Ingredientes"]) else "",
                help="Lista de ingredientes separados por vírgulas"
            )
                
            # Contém leite - mais destaque
            contem_leite = st.checkbox("🥛 Contém leite ou derivados?", 
                                     value=bool(item["Contém Leite"]) if "Contém Leite" in item else False,
                                     help="Marque para produtos lácteos como leite, queijo, iogurte, etc.")
        
        with col2:
            # Para Thomas - Destacado acima
            para_thomas = st.checkbox("⭐ Item adequado para Thomás?", 
                                   value=bool(item["Para Thomas"]) if "Para Thomas" in item else False,
                                   help="Marque para itens adequados para Thomás")
            
            if para_thomas and contem_leite:
                st.warning("⚠️ **ATENÇÃO!** Este item contém leite e está marcado para Thomás.")
                st.markdown("Verifique se é adequado para as restrições alimentares de Thomás.")
            elif para_thomas:
                st.success("✅ Este item será visível na aba Thomás")
                
            # Valor e local de compra
            valor_compra = st.number_input(
                "Valor da compra (R$)", 
                min_value=0.0, 
                value=float(item["Valor Compra"]) if "Valor Compra" in item and pd.notna(item["Valor Compra"]) else 0.0, 
                step=0.01,
                format="%.2f"
            )
            
            existing_locals = db.obter_locais_compra()
            local_options = existing_locals + ["Outro"]
            
            if "Local Compra" in item and item["Local Compra"] and item["Local Compra"] in existing_locals:
                local_index = existing_locals.index(item["Local Compra"])
                local_compra_sel = st.selectbox("Local de compra", options=local_options, index=local_index)
            else:
                local_compra_sel = st.selectbox("Local de compra", options=local_options)
                
            if local_compra_sel == "Outro":
                local_compra = st.text_input("Especifique o local de compra:")
            else:
                local_compra = local_compra_sel
            
            # Informações nutricionais
            st.subheader("Informações Nutricionais (por 100g/ml)")
            
            # Layout em duas colunas para os nutrientes
            ncol1, ncol2 = st.columns(2)
            
            with ncol1:
                calorias = st.number_input(
                    "Calorias (kcal)", 
                    min_value=0.0, 
                    value=float(item["Calorias/100g"]) if "Calorias/100g" in item and pd.notna(item["Calorias/100g"]) else 0.0, 
                    step=0.1
                )
                
                proteinas = st.number_input(
                    "Proteínas (g)", 
                    min_value=0.0, 
                    value=float(item["Proteínas (g)"]) if "Proteínas (g)" in item and pd.notna(item["Proteínas (g)"]) else 0.0, 
                    step=0.1
                )
                
                carboidratos = st.number_input(
                    "Carboidratos (g)", 
                    min_value=0.0, 
                    value=float(item["Carboidratos (g)"]) if "Carboidratos (g)" in item and pd.notna(item["Carboidratos (g)"]) else 0.0, 
                    step=0.1
                )
                
                acucar = st.number_input(
                    "Açúcar (g)", 
                    min_value=0.0, 
                    value=float(item["Açúcar/100g"]) if "Açúcar/100g" in item and pd.notna(item["Açúcar/100g"]) else 0.0, 
                    step=0.1
                )
                
                gorduras = st.number_input(
                    "Gorduras Totais (g)", 
                    min_value=0.0, 
                    value=float(item["Gorduras (g)"]) if "Gorduras (g)" in item and pd.notna(item["Gorduras (g)"]) else 0.0, 
                    step=0.1
                )
                
            with ncol2:
                calcio = st.number_input(
                    "Cálcio (mg)", 
                    min_value=0.0, 
                    value=float(item["Cálcio (mg)"]) if "Cálcio (mg)" in item and pd.notna(item["Cálcio (mg)"]) else 0.0, 
                    step=1.0,
                    help="Nutriente importante para Thomás"
                )
                
                vitamina_d = st.number_input(
                    "Vitamina D (mcg)", 
                    min_value=0.0, 
                    value=float(item["Vitamina D (mcg)"]) if "Vitamina D (mcg)" in item and pd.notna(item["Vitamina D (mcg)"]) else 0.0, 
                    step=0.1,
                    help="Nutriente importante para Thomás"
                )
                
                ferro = st.number_input(
                    "Ferro (mg)", 
                    min_value=0.0, 
                    value=float(item["Ferro (mg)"]) if "Ferro (mg)" in item and pd.notna(item["Ferro (mg)"]) else 0.0, 
                    step=0.1
                )
                
                vitamina_c = st.number_input(
                    "Vitamina C (mg)", 
                    min_value=0.0, 
                    value=float(item["Vitamina C (mg)"]) if "Vitamina C (mg)" in item and pd.notna(item["Vitamina C (mg)"]) else 0.0, 
                    step=0.1
                )
                
                sodio = st.number_input(
                    "Sódio (mg)", 
                    min_value=0.0, 
                    value=float(item["Sódio/100g"]) if "Sódio/100g" in item and pd.notna(item["Sódio/100g"]) else 0.0, 
                    step=1.0
                )
        
        # Botão de submit
        if st.form_submit_button("✅ Atualizar"):
            success, msg = db.atualizar_item(
                item_id, nome, qtd, unidade, local, categoria, perecivel, 
                validade, valor_compra, local_compra, calorias, proteinas, 
                carboidratos, gorduras, None, calcio, ferro, None, vitamina_c, 
                vitamina_d, acucar, sodio, ingredientes, para_thomas, contem_leite
            )
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

def excluir_item(db, item_id):
    """Excluir um item do inventário"""
    df = db.carregar_inventario()
    item_data = df[df["ID"] == item_id]
    
    if item_data.empty:
        st.error(f"Item ID {item_id} não encontrado!")
        return
    
    item = item_data.iloc[0]
    st.warning(f"Tem certeza que deseja excluir **{item['Nome']}**?")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Sim, excluir"):
            success, msg = db.excluir_item(item_id)
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
    with col2:
        if st.button("❌ Cancelar"):
            st.rerun()

def marcar_para_thomas(db, item_id):
    """Marca ou desmarca um item para Thomas"""
    df = db.carregar_inventario()
    item_data = df[df["ID"] == item_id]
    
    if item_data.empty:
        st.error(f"Item ID {item_id} não encontrado!")
        return
    
    item = item_data.iloc[0]
    atual_thomas = bool(item["Para Thomas"]) if "Para Thomas" in item else False
    contem_leite = bool(item["Contém Leite"]) if "Contém Leite" in item else False
    
    if atual_thomas:
        msg = f"Deseja remover **{item['Nome']}** da lista de Thomás?"
        btn_txt = "Remover da lista"
    else:
        msg = f"Deseja marcar **{item['Nome']}** como adequado para Thomás?"
        btn_txt = "Adicionar à lista"
    
    st.info(msg)
    
    # Obter status de compatibilidade
    compatibilidade = int(item["Compatibilidade Thomas"]) if "Compatibilidade Thomas" in item else 0
    
    # Alertas baseados na compatibilidade
    if not atual_thomas:
        if compatibilidade == 0:  # Não recomendado
            st.error("⚠️ **ESTE ALIMENTO NÃO É RECOMENDADO PARA THOMÁS!**")
            st.markdown("Este item contém ingredientes que não são compatíveis com as restrições alimentares de Thomás.")
            confirma_alerta = st.checkbox("✓ Confirmo que este produto é adequado para Thomás mesmo com restrições")
        elif compatibilidade == 1:  # Verificar
            st.warning("⚠️ **ATENÇÃO! Verifique os ingredientes deste produto para Thomás.**")
            st.markdown("Este item pode conter ingredientes que não são compatíveis com as restrições de Thomás.")
            confirma_alerta = st.checkbox("✓ Confirmo que verifiquei os ingredientes")
        else:  # Seguro
            st.success("✅ Este item parece seguro para Thomás.")
            confirma_alerta = True
    else:
        confirma_alerta = True
    
    col1, col2 = st.columns(2)
    with col1:
        disabled_button = not confirma_alerta and not atual_thomas
        
        if st.button(f"✅ Sim, {btn_txt}", disabled=disabled_button):
            # Obter os valores necessários para atualizar
            unidade = item["Unidade"] if "Unidade" in item else "unidade"
            categoria = item["Categoria"] if "Categoria" in item else "Outros"
            
            # Nutrientes
            calorias = item["Calorias/100g"] if "Calorias/100g" in item and pd.notna(item["Calorias/100g"]) else None
            proteinas = item["Proteínas (g)"] if "Proteínas (g)" in item and pd.notna(item["Proteínas (g)"]) else None
            carboidratos = item["Carboidratos (g)"] if "Carboidratos (g)" in item and pd.notna(item["Carboidratos (g)"]) else None
            gorduras = item["Gorduras (g)"] if "Gorduras (g)" in item and pd.notna(item["Gorduras (g)"]) else None
            calcio = item["Cálcio (mg)"] if "Cálcio (mg)" in item and pd.notna(item["Cálcio (mg)"]) else None
            ferro = item["Ferro (mg)"] if "Ferro (mg)" in item and pd.notna(item["Ferro (mg)"]) else None
            vitamina_c = item["Vitamina C (mg)"] if "Vitamina C (mg)" in item and pd.notna(item["Vitamina C (mg)"]) else None
            vitamina_d = item["Vitamina D (mcg)"] if "Vitamina D (mcg)" in item and pd.notna(item["Vitamina D (mcg)"]) else None
            acucar = item["Açúcar/100g"] if "Açúcar/100g" in item and pd.notna(item["Açúcar/100g"]) else None
            sodio = item["Sódio/100g"] if "Sódio/100g" in item and pd.notna(item["Sódio/100g"]) else None
            
            # Outros campos
            ingredientes = item["Ingredientes"] if "Ingredientes" in item and pd.notna(item["Ingredientes"]) else None
            
            success, msg = db.atualizar_item(
                item_id, item["Nome"], item["Quantidade"], unidade,
                item["Localização"], categoria, bool(item["Perecível"]),
                item["Validade"] if pd.notna(item["Validade"]) else None,
                item["Valor Compra"] if "Valor Compra" in item and pd.notna(item["Valor Compra"]) else None,
                item["Local Compra"] if "Local Compra" in item and pd.notna(item["Local Compra"]) else None,
                calorias, proteinas, carboidratos, gorduras, None, calcio, ferro, 
                None, vitamina_c, vitamina_d, acucar, sodio, ingredientes,
                not atual_thomas,  # Inverte o estado atual
                contem_leite  # Mantém o estado de contém leite
            )
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
    with col2:
        if st.button("❌ Cancelar"):
            st.rerun()

def adicionar_item_form(db):
    st.title("➕ Adicionar Novo Item")
    
    with st.form("form_add"):
        col1, col2 = st.columns(2)
        
        with col1:
            nome = st.text_input("Nome do item")
            
            # Quantidade e unidade lado a lado
            qcol1, qcol2 = st.columns([2, 1])
            with qcol1:
                qtd = st.number_input("Quantidade", min_value=0.01, value=1.0, step=0.1, format="%.2f")
            with qcol2:
                unidade = st.selectbox("Unidade", options=UNIDADES_MEDIDA)
            
            # Localização e categoria
            local = st.selectbox("Local de armazenamento", options=LOCAIS_ARMAZENAMENTO)
            categoria = st.selectbox("Categoria", options=CATEGORIAS_ALIMENTOS)
            
            # Perecível e validade
            perecivel = st.checkbox("É perecível?", value=True)
            validade = st.date_input(
                "Data de validade",
                min_value=datetime.date.today()
            ) if perecivel else None
            
            # Ingredientes
            ingredientes = st.text_area(
                "Ingredientes", 
                help="Lista de ingredientes separados por vírgulas",
                placeholder="Ex: farinha de trigo, açúcar, fermento..."
            )
            
            # Detecção automática de produtos lácteos
            leite_detectado = False
            if ingredientes:
                ingredientes_lower = ingredientes.lower()
                for termo in TERMOS_LACTEOS:
                    if termo in ingredientes_lower:
                        leite_detectado = True
                        break
            
            if nome and not leite_detectado:
                nome_lower = nome.lower()
                if any(termo in nome_lower for termo in TERMOS_LACTEOS):
                    leite_detectado = True
            
            # Contém leite - destacado
            contem_leite = st.checkbox(
                "🥛 Contém leite ou derivados?", 
                value=leite_detectado,
                help="Marque para produtos lácteos como leite, queijo, iogurte, etc."
            )
            
            if leite_detectado and not contem_leite:
                st.warning(f"⚠️ Este item pode conter leite/derivados com base no nome ou ingredientes. Confirme marcando a opção acima se necessário.")
            
        with col2:
            # Para Thomas - destacado no topo
            para_thomas = st.checkbox(
                "⭐ Item adequado para Thomás?", 
                help="Marque para itens adequados para Thomás"
            )
            
            confirma_leite = True
            
            if para_thomas and contem_leite:
                st.warning("⚠️ **ATENÇÃO! Este alimento contém LEITE ou DERIVADOS!**")
                st.markdown("Thomás tem restrições alimentares. Certifique-se que este alimento é adequado para ele.")
                confirma_leite = st.checkbox("✓ Confirmo que este produto é adequado para Thomás mesmo contendo leite")
                
            elif para_thomas:
                st.success("✅ Este item será visível na aba Thomás")
            
            # Valor e local de compra
            valor_compra = st.number_input("Valor da compra (R$)", min_value=0.0, value=0.0, step=0.01)
            
            existing_locals = db.obter_locais_compra()
            local_options = existing_locals + ["Outro"]
            
            local_compra_sel = st.selectbox("Local de compra", options=local_options)
            
            if local_compra_sel == "Outro":
                local_compra = st.text_input("Especifique o local de compra:")
            else:
                local_compra = local_compra_sel
            
            # Informações nutricionais
            st.subheader("Informações Nutricionais (por 100g/ml)")
            
            # Layout em duas colunas para os nutrientes
            ncol1, ncol2 = st.columns(2)
            
            with ncol1:
                calorias = st.number_input("Calorias (kcal)", min_value=0.0, value=0.0, step=0.1)
                proteinas = st.number_input("Proteínas (g)", min_value=0.0, value=0.0, step=0.1)
                carboidratos = st.number_input("Carboidratos (g)", min_value=0.0, value=0.0, step=0.1)
                acucar = st.number_input("Açúcar (g)", min_value=0.0, value=0.0, step=0.1)
                gorduras = st.number_input("Gorduras Totais (g)", min_value=0.0, value=0.0, step=0.1)
                
            with ncol2:
                calcio = st.number_input(
                    "Cálcio (mg)", 
                    min_value=0.0, 
                    value=0.0, 
                    step=1.0,
                    help="Nutriente importante para Thomás"
                )
                vitamina_d = st.number_input(
                    "Vitamina D (mcg)", 
                    min_value=0.0, 
                    value=0.0, 
                    step=0.1,
                    help="Nutriente importante para Thomás"
                )
                ferro = st.number_input("Ferro (mg)", min_value=0.0, value=0.0, step=0.1)
                vitamina_c = st.number_input("Vitamina C (mg)", min_value=0.0, value=0.0, step=0.1)
                sodio = st.number_input("Sódio (mg)", min_value=0.0, value=0.0, step=1.0)
        
        # Removido o parâmetro 'disabled' para sempre permitir cliques
        if st.form_submit_button("➕ Adicionar"):
            # Validação após o clique no botão
            erros = []
            if not nome:
                erros.append("Nome do item é obrigatório")
            if qtd <= 0:
                erros.append("Quantidade deve ser maior que zero")
            if perecivel and not validade:
                erros.append("Data de validade é obrigatória para itens perecíveis")
            if para_thomas and contem_leite and not confirma_leite:
                erros.append("É necessário confirmar que o produto é adequado para Thomás mesmo contendo leite")
                
            if erros:
                for erro in erros:
                    st.error(erro)
            else:
                # Processar o formulário
                success, msg = db.adicionar_item(
                    nome, qtd, unidade, local, categoria, perecivel, 
                    validade, valor_compra, local_compra, calorias, proteinas, 
                    carboidratos, gorduras, None, calcio, ferro, None, 
                    vitamina_c, vitamina_d, acucar, sodio, ingredientes, 
                    para_thomas, contem_leite
                )
                
                if success:
                    st.success(msg)
                    st.balloons()
                    st.rerun()
                else:
                    st.error(msg)