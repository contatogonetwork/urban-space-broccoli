import streamlit as st
import pandas as pd
import datetime
from utils.formatters import *
from utils.constants import *

def mostrar_inventario_thomas(db):
    st.title("👶 Inventário Thomás")
    
    # Descrição da área
    st.markdown("""
    Esta área é dedicada ao gerenciamento dos alimentos adequados para Thomás, 
    que possui restrições alimentares específicas.
    """)
    
    # Carregar dados apenas de Thomas
    df = db.carregar_inventario(apenas_thomas=True)
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        filtro_nome = st.text_input("🔍 Filtrar por nome:", key="filtro_nome_thomas")
    with col2:
        localizacoes = sorted(df["Localização"].unique()) if not df.empty else []
        filtro_local = st.multiselect("📍 Filtrar por localização:", options=localizacoes, key="filtro_local_thomas")
    with col3:
        categorias = sorted(df["Categoria"].unique()) if not df.empty and "Categoria" in df.columns else []
        filtro_categoria = st.multiselect("🏷️ Filtrar por categoria:", options=categorias, key="filtro_categoria_thomas")
    
    # Aplicar filtros
    if not df.empty:
        if filtro_nome:
            df = df[df["Nome"].str.contains(filtro_nome, case=False)]
        if filtro_local:
            df = df[df["Localização"].isin(filtro_local)]
        if filtro_categoria and "Categoria" in df.columns:
            df = df[df["Categoria"].isin(filtro_categoria)]
    
    # Exibir dados
    if df.empty:
        st.info("Nenhum item cadastrado para Thomás.")
        st.markdown("""
            Para adicionar itens ao inventário de Thomás:
            1. Vá para a aba "Inventário Geral"
            2. Selecione um item e clique em "⭐ Thomas"
            
            Ou adicione um novo item marcando a opção "Item adequado para Thomás"
        """)
    else:
        # Preparar dataframe para exibição
        df_display = df.copy()
        
        # Aplicar formatação
        if "Contém Leite" in df_display.columns:
            df_display["Contém Leite"] = df_display["Contém Leite"].apply(format_leite_status)
        if "Compatibilidade Thomas" in df_display.columns:
            df_display["Compatibilidade Thomas"] = df_display["Compatibilidade Thomas"].apply(format_compatibilidade)
        
        # Selecionar colunas para exibição baseado nas disponíveis
        available_columns = df_display.columns.tolist()
        default_columns = ["ID", "Nome", "Compatibilidade Thomas"]
        
        if "Contém Leite" in available_columns:
            default_columns.append("Contém Leite")
            
        default_columns.extend(["Quantidade", "Unidade", "Localização"])
        
        if "Categoria" in available_columns:
            default_columns.append("Categoria")
            
        default_columns.extend(["Validade", "Dias Até Vencer"])
        
        # Adicionar informações nutricionais relevantes para Thomas
        nutrientes_thomas = [
            "Proteínas (g)", "Cálcio (mg)", "Vitamina D (mcg)", "Ferro (mg)", "Vitamina C (mg)"
        ]
        
        for nutriente in nutrientes_thomas:
            if nutriente in available_columns:
                default_columns.append(nutriente)
        
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
            
        # Criar estilo
        df_style = df_display.style
        for col, style_func in styling_dict.items():
            df_style = df_style.applymap(style_func, subset=[col])
        
        # Configuração de colunas
        config_dict = {}
        if "ID" in colunas_exibir:
            config_dict["ID"] = st.column_config.NumberColumn("ID", width="small")
        if "Nome" in colunas_exibir:
            config_dict["Nome"] = st.column_config.TextColumn("Nome", width="medium")
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
                max_value=30
            )
        if "Nível Saúde" in colunas_exibir:
            config_dict["Nível Saúde"] = st.column_config.NumberColumn(
                "Nível Saúde",
                format="%d",
                help="1=Saudável, 2=Intermediário, 3=Alto impacto"
            )
            
        # Configurar colunas nutricionais
        for nutriente in nutrientes_thomas:
            if nutriente in colunas_exibir:
                config_dict[nutriente] = st.column_config.NumberColumn(nutriente, format="%.1f")
        
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
        
        # Legenda de compatibilidade
        with st.expander("ℹ️ Legenda de compatibilidade para Thomás"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown('<div style="background-color: #d5f5d5; color: #1e6f50; padding: 10px; border-left: 3px solid #4caf50; border-radius: 5px;">🟢 Seguro para Thomás</div>', unsafe_allow_html=True)
            with col2:
                st.markdown('<div style="background-color: #fff4cc; color: #806600; padding: 10px; border-left: 3px solid #ffcc00; border-radius: 5px;">🟡 Verificar ingredientes</div>', unsafe_allow_html=True)
            with col3:
                st.markdown('<div style="background-color: #ffcccc; color: #cc0000; padding: 10px; border-left: 3px solid #cc0000; border-radius: 5px;">🔴 Não recomendado</div>', unsafe_allow_html=True)
        
        # Alertas para itens com leite
        itens_leite = df[df["Contém Leite"] == 1] if "Contém Leite" in df.columns else pd.DataFrame()
        if not itens_leite.empty:
            st.warning(f"⚠️ **Atenção!** {len(itens_leite)} item(s) contém leite ou derivados.")
            with st.expander("Ver itens com leite"):
                for _, row in itens_leite.iterrows():
                    st.write(f"- {row['Nome']}")
        
        # Consumo de Thomas
        st.subheader("📝 Registrar Consumo de Thomás")
        
        with st.form("form_consumo_thomas"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                item_id = st.selectbox(
                    "Selecione o item consumido", 
                    options=df["ID"].tolist(),
                    format_func=lambda x: df[df["ID"] == x]["Nome"].values[0]
                )
                
                # Mostrar compatibilidade do item selecionado
                item_comp = df[df["ID"] == item_id]["Compatibilidade Thomas"].values[0]
                comp_icon = format_compatibilidade(item_comp)
                
                if item_comp == 0:  # Não recomendado
                    st.error(f"{comp_icon} Item não recomendado para Thomás!")
                elif item_comp == 1:  # Verificar
                    st.warning(f"{comp_icon} Verifique os ingredientes antes de servir a Thomás.")
                else:  # Seguro
                    st.success(f"{comp_icon} Item seguro para Thomás.")
                
            with col2:
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
                
                # Nutrientes consumidos
                if "Proteínas (g)" in item_selecionado.columns and pd.notna(item_selecionado["Proteínas (g)"].values[0]):
                    proteina_cons = float(item_selecionado["Proteínas (g)"].values[0]) * qtd_consumida / 100
                    st.info(f"Proteínas: {proteina_cons:.1f}g")
                
                if "Cálcio (mg)" in item_selecionado.columns and pd.notna(item_selecionado["Cálcio (mg)"].values[0]):
                    calcio_cons = float(item_selecionado["Cálcio (mg)"].values[0]) * qtd_consumida / 100
                    st.info(f"Cálcio: {calcio_cons:.1f}mg")
                
            with col3:
                data_consumo = st.date_input(
                    "Data do consumo",
                    value=datetime.date.today()
                )
            
            if st.form_submit_button("✅ Registrar Consumo"):
                success, msg = db.registrar_consumo(item_id, qtd_consumida, para_thomas=True, data=data_consumo)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

def mostrar_perfil_thomas(db):
    """Exibe e gerencia o perfil nutricional e restrições de Thomas"""
    st.title("👶 Perfil Nutricional de Thomás")
    
    tab1, tab2, tab3 = st.tabs(["🚫 Restrições Alimentares", "🥗 Necessidades Nutricionais", "📊 Análise de Consumo"])
    
    with tab1:
        mostrar_restricoes_alimentares(db)
        
    with tab2:
        mostrar_necessidades_nutricionais(db)
        
    with tab3:
        mostrar_analise_nutricional_thomas(db)

def mostrar_restricoes_alimentares(db):
    """Exibe e gerencia as restrições alimentares de Thomas"""
    st.header("🚫 Restrições Alimentares")
    
    restricoes = db.obter_restricoes_thomas()
    
    # Exibir restrições existentes
    if restricoes:
        st.subheader("Restrições Cadastradas")
        
        for restricao in restricoes:
            # Cores baseadas na gravidade
            gravidade = restricao["nivel_gravidade"]
            cor_gravidade = "#ffcccc" if gravidade >= 4 else "#fff4cc" if gravidade >= 2 else "#e6f3ff"
            
            with st.expander(f"{restricao['tipo']}: {restricao['substancia']} (Nível: {gravidade}/5)"):
                st.markdown(f"""
                <div style="background-color: {cor_gravidade}; padding: 10px; border-radius: 5px;">
                    <p><strong>Sintomas:</strong> {', '.join(restricao['sintomas']) if restricao['sintomas'] else 'Não especificados'}</p>
                    <p><strong>Substituições recomendadas:</strong> {', '.join(restricao['substituicoes']) if restricao['substituicoes'] else 'Não especificadas'}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Botão para remover restrição
                if st.button(f"🗑️ Remover Restrição", key=f"del_restricao_{restricao['id']}"):
                    success, msg = db.remover_restricao_thomas(restricao['id'])
                    if success:
                        st.success(msg)
                        # Recalcular compatibilidade de todos os itens após modificação
                        recalc_success, recalc_msg = db.recalcular_compatibilidade_todos_itens()
                        if recalc_success:
                            st.info(recalc_msg)
                        st.rerun()
                    else:
                        st.error(msg)
    else:
        st.info("Não há restrições alimentares cadastradas para Thomás.")
    
    # Formulário para adicionar nova restrição
    st.subheader("Adicionar Nova Restrição")
    
    with st.form("form_adicionar_restricao"):
        col1, col2 = st.columns(2)
        
        with col1:
            tipo = st.selectbox("Tipo", ["Intolerância", "Alergia", "Sensibilidade", "Outro"])
            substancia = st.text_input("Substância/Ingrediente", placeholder="Ex: Lactose, Glúten, etc.")
            
        with col2:
            nivel_gravidade = st.slider("Nível de Gravidade", min_value=1, max_value=5, value=3, 
                                      help="1=Leve, 5=Muito grave")
            sintomas = st.text_input("Sintomas", placeholder="Ex: Dor abdominal, Diarreia, etc.")
            
        substituicoes = st.text_input("Substituições Recomendadas", placeholder="Ex: Leite vegetal, Queijos veganos, etc.")
        
        if st.form_submit_button("✅ Adicionar Restrição"):
            if not substancia:
                st.error("Você precisa informar a substância ou ingrediente.")
            else:
                # Converter para listas
                sintomas_lista = [s.strip() for s in sintomas.split(",")] if sintomas else []
                substituicoes_lista = [s.strip() for s in substituicoes.split(",")] if substituicoes else []
                
                success, msg = db.adicionar_restricao_thomas(tipo, substancia, nivel_gravidade, sintomas_lista, substituicoes_lista)
                if success:
                    st.success(msg)
                    # Recalcular compatibilidade de todos os itens após modificação
                    recalc_success, recalc_msg = db.recalcular_compatibilidade_todos_itens()
                    if recalc_success:
                        st.info(recalc_msg)
                    st.rerun()
                else:
                    st.error(msg)

def mostrar_necessidades_nutricionais(db):
    """Exibe e gerencia as necessidades nutricionais de Thomas"""
    st.header("🥗 Necessidades Nutricionais")
    
    necessidades = db.obter_necessidades_thomas()
    
    if necessidades:
        st.subheader("Necessidades Diárias")
        
        # Criar DataFrame para melhor visualização
        df_necessidades = pd.DataFrame(necessidades)
        
        # Converter prioridade para texto
        def prioridade_texto(nivel):
            if nivel == 3:
                return "🔴 Alta"
            elif nivel == 2:
                return "🟡 Média" 
            else:
                return "🔵 Baixa"
                
        df_necessidades["prioridade_texto"] = df_necessidades["prioridade"].apply(prioridade_texto)
        
        # Exibir tabela
        st.dataframe(
            df_necessidades[["nutriente", "quantidade_diaria", "unidade", "prioridade_texto"]],
            column_config={
                "nutriente": st.column_config.TextColumn("Nutriente"),
                "quantidade_diaria": st.column_config.NumberColumn("Quantidade Diária"),
                "unidade": st.column_config.TextColumn("Unidade"),
                "prioridade_texto": st.column_config.TextColumn("Prioridade")
            },
            hide_index=True
        )
        
        # Interface para atualizar necessidades
        st.subheader("Atualizar Necessidade Nutricional")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            nutriente_id = st.selectbox(
                "Selecione o nutriente", 
                options=[n["id"] for n in necessidades],
                format_func=lambda id: next((n["nutriente"] for n in necessidades if n["id"] == id), "")
            )
        
        with col2:
            # Obter detalhes do nutriente selecionado
            nutriente_selecionado = next((n for n in necessidades if n["id"] == nutriente_id), None)
            
            if nutriente_selecionado:
                qtd = st.number_input(
                    "Quantidade diária", 
                    min_value=0.0, 
                    value=float(nutriente_selecionado["quantidade_diaria"]),
                    step=0.1
                )
                unidade = nutriente_selecionado["unidade"]  # Não permitimos mudança de unidade
                
        with col3:
            prioridade = st.selectbox(
                "Prioridade", 
                options=[1, 2, 3],
                index=nutriente_selecionado["prioridade"]-1 if nutriente_selecionado else 0,
                format_func=lambda p: "Alta" if p == 3 else "Média" if p == 2 else "Baixa"
            )
        
        if st.button("✅ Atualizar"):
            success, msg = db.atualizar_necessidade_thomas(nutriente_id, qtd, prioridade)
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
    else:
        st.info("Não há necessidades nutricionais cadastradas para Thomás.")

def mostrar_analise_nutricional_thomas(db):
    """Exibe análise do consumo nutricional de Thomas"""
    st.header("📊 Análise de Consumo Nutricional")
    
    # Selecionar período de análise
    periodo = st.selectbox(
        "Período de análise", 
        options=[7, 14, 30, 60, 90],
        index=0,
        format_func=lambda d: f"Últimos {d} dias"
    )
    
    # Obter dados de consumo nutricional de Thomas
    df_nutrientes = db.obter_nutrientes_consumidos(apenas_thomas=True, periodo_dias=periodo)
    
    if df_nutrientes.empty:
        st.info(f"Não há registros de consumo para Thomás nos últimos {periodo} dias.")
        return
    
    # Obter necessidades nutricionais recomendadas
    necessidades = db.obter_necessidades_thomas()
    
    # Criar dicionário para fácil acesso
    necessidades_dict = {n["nutriente"].replace(" ", "_").lower(): {
        "qtd": n["quantidade_diaria"],
        "unidade": n["unidade"],
        "prioridade": n["prioridade"]
    } for n in necessidades}
    
    # Calcular médias diárias
    media_proteinas = df_nutrientes["Proteínas (g)"].mean()
    media_calcio = df_nutrientes["Cálcio (mg)"].mean()
    media_ferro = df_nutrientes["Ferro (mg)"].mean()
    media_vit_d = df_nutrientes["Vitamina D (mcg)"].mean()
    media_vit_c = df_nutrientes["Vitamina C (mg)"].mean()
    
    # Exibir métricas com comparação às necessidades
    st.subheader(f"Média diária de consumo (últimos {periodo} dias)")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        proteina_rec = necessidades_dict.get("proteínas", {"qtd": 30, "unidade": "g"})
        proteina_pct = (media_proteinas / proteina_rec["qtd"]) * 100
        st.metric(
            "Proteínas", 
            f"{media_proteinas:.1f}g", 
            f"{proteina_pct:.1f}% da meta" if proteina_pct <= 100 else f"+{proteina_pct - 100:.1f}%",
            delta_color="normal" if proteina_pct >= 90 else "inverse"
        )
        
    with col2:
        calcio_rec = necessidades_dict.get("cálcio", {"qtd": 1000, "unidade": "mg"})
        calcio_pct = (media_calcio / calcio_rec["qtd"]) * 100
        st.metric(
            "Cálcio", 
            f"{media_calcio:.1f}mg", 
            f"{calcio_pct:.1f}% da meta" if calcio_pct <= 100 else f"+{calcio_pct - 100:.1f}%",
            delta_color="normal" if calcio_pct >= 90 else "inverse"
        )
        
    with col3:
        vit_d_rec = necessidades_dict.get("vitamina_d", {"qtd": 15, "unidade": "mcg"})
        vit_d_pct = (media_vit_d / vit_d_rec["qtd"]) * 100
        st.metric(
            "Vitamina D", 
            f"{media_vit_d:.1f}mcg", 
            f"{vit_d_pct:.1f}% da meta" if vit_d_pct <= 100 else f"+{vit_d_pct - 100:.1f}%",
            delta_color="normal" if vit_d_pct >= 90 else "inverse"
        )
        
    with col4:
        ferro_rec = necessidades_dict.get("ferro", {"qtd": 10, "unidade": "mg"})
        ferro_pct = (media_ferro / ferro_rec["qtd"]) * 100
        st.metric(
            "Ferro", 
            f"{media_ferro:.1f}mg", 
            f"{ferro_pct:.1f}% da meta" if ferro_pct <= 100 else f"+{ferro_pct - 100:.1f}%",
            delta_color="normal" if ferro_pct >= 90 else "inverse"
        )
        
    with col5:
        vit_c_rec = necessidades_dict.get("vitamina_c", {"qtd": 45, "unidade": "mg"})
        vit_c_pct = (media_vit_c / vit_c_rec["qtd"]) * 100
        st.metric(
            "Vitamina C", 
            f"{media_vit_c:.1f}mg", 
            f"{vit_c_pct:.1f}% da meta" if vit_c_pct <= 100 else f"+{vit_c_pct - 100:.1f}%",
            delta_color="normal" if vit_c_pct >= 90 else "inverse"
        )
    
    # Gráfico de tendência
    st.subheader("Tendência de consumo nutricional")
    
    # Preparar dados para o gráfico
    df_chart = df_nutrientes.copy()
    
    # Normalizar os valores para uma escala comum (0-100%)
    for nutriente, info in necessidades_dict.items():
        col_name = None
        if nutriente == "proteínas":
            col_name = "Proteínas (g)"
        elif nutriente == "cálcio":
            col_name = "Cálcio (mg)"
        elif nutriente == "ferro":
            col_name = "Ferro (mg)"
        elif nutriente == "vitamina_d":
            col_name = "Vitamina D (mcg)"
        elif nutriente == "vitamina_c":
            col_name = "Vitamina C (mg)"
            
        if col_name and col_name in df_chart.columns:
            df_chart[f"{nutriente}_pct"] = (df_chart[col_name] / info["qtd"]) * 100
    
    # Gráfico de área
    st.line_chart(
        df_chart.set_index("Data")[
            ["proteínas_pct", "cálcio_pct", "ferro_pct", "vitamina_d_pct", "vitamina_c_pct"]
        ].rename(columns={
            "proteínas_pct": "Proteínas",
            "cálcio_pct": "Cálcio",
            "ferro_pct": "Ferro",
            "vitamina_d_pct": "Vitamina D",
            "vitamina_c_pct": "Vitamina C"
        })
    )
    
    # Recomendações
    st.subheader("💡 Recomendações")
    
    # Identificar deficiências significativas (menos de 80% da necessidade)
    deficiencias = []
    
    if proteina_pct < 80:
        deficiencias.append({
            "nutriente": "Proteínas", 
            "valor": proteina_pct,
            "alimentos": "carnes magras, ovos, leguminosas, tofu, iogurte"
        })
        
    if calcio_pct < 80:
        deficiencias.append({
            "nutriente": "Cálcio", 
            "valor": calcio_pct,
            "alimentos": "leites vegetais fortificados, brócolis, couve, sardinhas"
        })
        
    if vit_d_pct < 80:
        deficiencias.append({
            "nutriente": "Vitamina D", 
            "valor": vit_d_pct,
            "alimentos": "cogumelos, alimentos fortificados, exposição solar matinal"
        })
        
    if ferro_pct < 80:
        deficiencias.append({
            "nutriente": "Ferro", 
            "valor": ferro_pct,
            "alimentos": "carnes vermelhas magras, feijão, lentilha, espinafre"
        })
        
    if vit_c_pct < 80:
        deficiencias.append({
            "nutriente": "Vitamina C", 
            "valor": vit_c_pct,
            "alimentos": "laranja, morango, kiwi, pimentão, brócolis"
        })
    
    # Exibir recomendações
    if deficiencias:
        st.warning("**Foram identificadas deficiências nutricionais para Thomás:**")
        
        for def_item in deficiencias:
            st.markdown(f"""
            **{def_item['nutriente']}**: apenas {def_item['valor']:.1f}% da necessidade diária
            - **Alimentos recomendados**: {def_item['alimentos']}
            """)
            
        # Lista de alimentos compatíveis com Thomas que atendam às deficiências
        if "ferro" in [d["nutriente"].lower() for d in deficiencias]:
            st.markdown("#### Alimentos ricos em ferro seguros para Thomás:")
            
            # Buscar alimentos compatíveis ricos em ferro no inventário
            df_inventario = db.carregar_inventario()
            if "Compatibilidade Thomas" in df_inventario.columns and "Ferro (mg)" in df_inventario.columns:
                alimentos_ferro = df_inventario[
                    (df_inventario["Compatibilidade Thomas"] >= 1) & 
                    (df_inventario["Ferro (mg)"] > 1)
                ].sort_values("Ferro (mg)", ascending=False).head(5)
                
                if not alimentos_ferro.empty:
                    for _, alimento in alimentos_ferro.iterrows():
                        st.markdown(f"- **{alimento['Nome']}**: {alimento['Ferro (mg)']:.1f}mg por 100g")
    else:
        st.success("✅ **Thomás está recebendo os nutrientes necessários!**")
        st.markdown("Continue com a alimentação atual e o monitoramento regular.")