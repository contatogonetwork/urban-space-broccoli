def mostrar_analise_nutricional_thomas(db):
    st.title("📊 Análise Nutricional de Thomás")
    
    try:
        # Período da análise
        col1, col2 = st.columns(2)
        with col1:
            periodo = st.selectbox(
                "Período de análise:",
                options=["Últimos 7 dias", "Últimos 30 dias", "Este mês", "Mês passado", "Personalizado"],
                key="periodo_analise"
            )
        
        if periodo == "Personalizado":
            with col2:
                data_inicio = st.date_input(
                    "Data inicial",
                    value=datetime.date.today() - datetime.timedelta(days=7),
                    max_value=datetime.date.today()
                )
                data_fim = st.date_input(
                    "Data final",
                    value=datetime.date.today(),
                    max_value=datetime.date.today()
                )
        else:
            # Definir datas com base no período selecionado
            hoje = datetime.date.today()
            if periodo == "Últimos 7 dias":
                data_inicio = hoje - datetime.timedelta(days=7)
                data_fim = hoje
            elif periodo == "Últimos 30 dias":
                data_inicio = hoje - datetime.timedelta(days=30)
                data_fim = hoje
            elif periodo == "Este mês":
                data_inicio = hoje.replace(day=1)
                data_fim = hoje
            elif periodo == "Mês passado":
                primeiro_dia_mes_atual = hoje.replace(day=1)
                ultimo_dia_mes_anterior = primeiro_dia_mes_atual - datetime.timedelta(days=1)
                data_inicio = ultimo_dia_mes_anterior.replace(day=1)
                data_fim = ultimo_dia_mes_anterior
        
        # Obter dados de consumo nutricional
        df_consumo = db.obter_consumo_nutricional_thomas(data_inicio, data_fim)
        
        if df_consumo is None or df_consumo.empty:
            st.info(f"Nenhum registro de consumo encontrado para o período de {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}.")
            return
        
        # Mostrar resumo de consumo
        st.subheader(f"Resumo do período: {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}")
        
        # Métricas principais em cards
        col1, col2, col3, col4 = st.columns(4)
        
        # Valores diários recomendados aproximados para um bebê (ajustar conforme a idade real)
        proteina_rec = 13  # g/dia
        calcio_rec = 500   # mg/dia
        ferro_rec = 7      # mg/dia
        vit_c_rec = 35     # mg/dia
        
        # Calcular médias diárias
        dias_periodo = (data_fim - data_inicio).days + 1  # +1 para incluir o dia final
        
        with col1:
            if "Proteínas (g)" in df_consumo.columns:
                proteina_total = df_consumo["Proteínas (g)"].sum()
                proteina_diaria = proteina_total / dias_periodo
                porcentagem = min(100, int(proteina_diaria / proteina_rec * 100))
                st.metric(
                    "Proteínas", 
                    f"{proteina_diaria:.1f}g/dia", 
                    f"{porcentagem}% do recomendado"
                )
                
        with col2:
            if "Cálcio (mg)" in df_consumo.columns:
                calcio_total = df_consumo["Cálcio (mg)"].sum()
                calcio_diario = calcio_total / dias_periodo
                porcentagem = min(100, int(calcio_diario / calcio_rec * 100))
                st.metric(
                    "Cálcio", 
                    f"{calcio_diario:.1f}mg/dia", 
                    f"{porcentagem}% do recomendado"
                )
                
        with col3:
            if "Ferro (mg)" in df_consumo.columns:
                ferro_total = df_consumo["Ferro (mg)"].sum()
                ferro_diario = ferro_total / dias_periodo
                porcentagem = min(100, int(ferro_diario / ferro_rec * 100))
                st.metric(
                    "Ferro", 
                    f"{ferro_diario:.1f}mg/dia", 
                    f"{porcentagem}% do recomendado"
                )
                
        with col4:
            if "Vitamina C (mg)" in df_consumo.columns:
                vit_c_total = df_consumo["Vitamina C (mg)"].sum()
                vit_c_diaria = vit_c_total / dias_periodo
                porcentagem = min(100, int(vit_c_diaria / vit_c_rec * 100))
                st.metric(
                    "Vitamina C", 
                    f"{vit_c_diaria:.1f}mg/dia", 
                    f"{porcentagem}% do recomendado"
                )
        
        # Gráficos de consumo
        st.subheader("Consumo ao longo do tempo")
        
        # Preparar dados para gráficos
        if "Data" in df_consumo.columns:
            df_diario = df_consumo.groupby("Data").sum().reset_index()
            df_diario["Data"] = pd.to_datetime(df_diario["Data"])
            
            # Gráfico de consumo de nutrientes
            import plotly.express as px
            
            if "Proteínas (g)" in df_diario.columns:
                fig_proteina = px.line(
                    df_diario, 
                    x="Data", 
                    y="Proteínas (g)",
                    title="Consumo de Proteínas",
                    markers=True,
                    labels={"Proteínas (g)": "Proteínas (g)", "Data": ""}
                )
                fig_proteina.add_hline(y=proteina_rec, line_dash="dash", line_color="green", annotation_text="Recomendado")
                st.plotly_chart(fig_proteina, use_container_width=True)
                
            if "Cálcio (mg)" in df_diario.columns and "Ferro (mg)" in df_diario.columns:
                # Gráfico combinado de cálcio e ferro
                fig_minerais = px.line(
                    df_diario, 
                    x="Data", 
                    y=["Cálcio (mg)", "Ferro (mg)"],
                    title="Consumo de Minerais",
                    markers=True,
                    labels={"value": "Quantidade", "Data": "", "variable": "Mineral"}
                )
                st.plotly_chart(fig_minerais, use_container_width=True)
        
        # Tabela detalhada de alimentos consumidos
        st.subheader("Detalhamento do consumo")
        
        if "Nome" in df_consumo.columns:
            # Agrupar por alimento
            alimentos_consumo = df_consumo.groupby("Nome").agg({
                "Quantidade": "sum",
                "Proteínas (g)": "sum",
                "Cálcio (mg)": "sum",
                "Ferro (mg)": "sum",
                "Vitamina C (mg)": "sum"
            }).reset_index().sort_values(by="Quantidade", ascending=False)
            
            # Filtrar apenas colunas não nulas
            colunas_validas = ["Nome", "Quantidade"] + [col for col in ["Proteínas (g)", "Cálcio (mg)", "Ferro (mg)", "Vitamina C (mg)"] 
                                                     if col in alimentos_consumo.columns and not alimentos_consumo[col].isna().all()]
            
            st.dataframe(
                alimentos_consumo[colunas_validas],
                use_container_width=True
            )
            
        # Recomendações baseadas na análise
        st.subheader("Recomendações")
        
        # Verificar deficiências
        recomendacoes = []
        
        if "Proteínas (g)" in df_consumo.columns:
            proteina_diaria = df_consumo["Proteínas (g)"].sum() / dias_periodo
            if proteina_diaria < proteina_rec * 0.7:  # Menos de 70% do recomendado
                recomendacoes.append("Aumentar o consumo de proteínas (carnes, ovos, leguminosas).")
        
        if "Cálcio (mg)" in df_consumo.columns:
            calcio_diario = df_consumo["Cálcio (mg)"].sum() / dias_periodo
            if calcio_diario < calcio_rec * 0.7:
                recomendacoes.append("Aumentar o consumo de alimentos ricos em cálcio (vegetais verde-escuros, tofu).")
        
        if "Ferro (mg)" in df_consumo.columns:
            ferro_diario = df_consumo["Ferro (mg)"].sum() / dias_periodo
            if ferro_diario < ferro_rec * 0.7:
                recomendacoes.append("Aumentar o consumo de alimentos ricos em ferro (carnes, feijões, folhas verde-escuras).")
        
        if "Vitamina C (mg)" in df_consumo.columns:
            vit_c_diaria = df_consumo["Vitamina C (mg)"].sum() / dias_periodo
            if vit_c_diaria < vit_c_rec * 0.7:
                recomendacoes.append("Aumentar o consumo de frutas cítricas e vegetais ricos em vitamina C.")
        
        if recomendacoes:
            for rec in recomendacoes:
                st.info(rec)
        else:
            st.success("Os níveis nutricionais estão adequados às necessidades de Thomás! Continue com a alimentação atual.")
            
    except Exception as e:
        st.error(f"Erro na análise nutricional: {str(e)}")
        st.error("Por favor, verifique se os dados de consumo estão sendo registrados corretamente.")
        st.code(traceback.format_exc())
