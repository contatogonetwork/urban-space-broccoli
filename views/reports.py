import streamlit as st
import pandas as pd
from utils.formatters import *
from utils.constants import *

def mostrar_relatorios(db):
    st.title("📊 Relatórios")
    
    # Selecionar tipo de relatório
    relatorio = st.selectbox(
        "Selecione o tipo de relatório", 
        ["Análise de Preços", "Consumo e Perfil Alimentar", "Nutrição e Saúde"]
    )
    
    if relatorio == "Análise de Preços":
        mostrar_relatorio_precos(db)
    elif relatorio == "Consumo e Perfil Alimentar":
        mostrar_relatorio_consumo(db)
    else:
        mostrar_relatorio_nutricional(db)

def mostrar_relatorio_precos(db):
    st.subheader("💰 Análise de Preços")
    
    # Obter dados de preços
    df_precos = db.obter_tendencia_precos()
    
    if df_precos.empty:
        st.info("Ainda não há histórico de preços registrado.")
        return
        
    # Relatório por local de compra
    st.write("#### Comparação por Local de Compra")
    
    # Agrupar por nome e local, obtendo média de preço unitário
    comparativo = df_precos.groupby(["Nome", "Local Compra"])["Valor Unitário"].mean().reset_index()
    
    # Pivot para comparar melhor
    pivot = comparativo.pivot(index="Nome", columns="Local Compra", values="Valor Unitário")
    
    # Exibir tabela comparativa
    st.dataframe(pivot, use_container_width=True)
    
    # Gráfico de evolução de preços
    st.write("#### Evolução de Preços ao Longo do Tempo")
    
    # Selecionar produto para análise
    produtos = sorted(df_precos["Nome"].unique())
    produto = st.selectbox("Selecione um produto", produtos)
    
    # Filtrar dados do produto selecionado
    produto_data = df_precos[df_precos["Nome"] == produto].sort_values("Data")
    
    if len(produto_data) > 1:
        # Usar gráfico de linha do Streamlit em vez de matplotlib
        st.line_chart(
            produto_data.pivot(index="Data", columns="Local Compra", values="Valor Unitário")
        )
        
        # Calcular tendência
        if len(produto_data) >= 3:
            primeiro_preco = produto_data.iloc[0]["Valor Unitário"]
            ultimo_preco = produto_data.iloc[-1]["Valor Unitário"]
            variacao = (ultimo_preco - primeiro_preco) / primeiro_preco * 100
            
            if variacao > 5:
                st.warning(f"⚠️ **Tendência de alta:** Aumento de {variacao:.1f}% desde o primeiro registro")
            elif variacao < -5:
                st.success(f"✅ **Tendência de queda:** Redução de {abs(variacao):.1f}% desde o primeiro registro")
            else:
                st.info(f"📊 **Preço estável:** Variação de apenas {variacao:.1f}% desde o primeiro registro")
    else:
        st.info("Histórico insuficiente para gerar gráfico de tendência.")

def mostrar_relatorio_consumo(db):
    st.subheader("🍽️ Análise de Consumo")
    
    # Opções de relatório
    opcao = st.radio(
        "Tipo de análise",
        ["Consumo Geral", "Consumo de Thomás", "Comparativo"]
    )
    
    # Selecionar período
    periodo = st.selectbox(
        "Período de análise", 
        options=[7, 14, 30, 60, 90],
        index=2,  # padrão 30 dias
        format_func=lambda d: f"Últimos {d} dias"
    )
    
    if opcao == "Consumo Geral":
        df_consumo = db.obter_estatisticas_consumo(apenas_thomas=False, periodo_dias=periodo)
        titulo = "Perfil de Consumo Geral"
    elif opcao == "Consumo de Thomás":
        df_consumo = db.obter_estatisticas_consumo(apenas_thomas=True, periodo_dias=periodo)
        titulo = "Perfil de Consumo de Thomás"
    else:
        # Para o comparativo, obtemos os dois e fazemos o merge
        df_geral = db.obter_estatisticas_consumo(apenas_thomas=False, periodo_dias=periodo)
        df_thomas = db.obter_estatisticas_consumo(apenas_thomas=True, periodo_dias=periodo)
        
        if not df_geral.empty and not df_thomas.empty:
            df_geral = df_geral.rename(columns={"Quantidade Consumida": "Consumo Geral"})
            df_thomas = df_thomas.rename(columns={"Quantidade Consumida": "Consumo Thomás"})
            
            # Merge dos dataframes
            df_consumo = pd.merge(df_geral, df_thomas, on=["Nome", "Categoria", "Unidade"], how="outer")
            df_consumo = df_consumo.fillna(0)
        else:
            df_consumo = pd.DataFrame()
            
        titulo = "Comparativo de Consumo"
    
    st.write(f"#### {titulo}")
    
    if df_consumo.empty:
        st.info("Ainda não há registros de consumo suficientes para análise.")
        return
    
    # Exibir dados de consumo
    if opcao == "Consumo de Thomás":
        # Selecionar apenas colunas relevantes para exibição
        colunas_exibir = ["Nome", "Categoria", "Quantidade Consumida", "Unidade"]
        
        # Adicionar colunas nutricionais se disponíveis
        for col in ["Proteínas (g) Consumido", "Cálcio (mg) Consumido", 
                    "Vitamina D (mcg) Consumido", "Ferro (mg) Consumido"]:
            if col in df_consumo.columns:
                colunas_exibir.append(col)
                
        st.dataframe(
            df_consumo[colunas_exibir],
            use_container_width=True
        )
    else:
        st.dataframe(df_consumo, use_container_width=True)
    
    # Gráfico de consumo por categoria
    if opcao != "Comparativo" and not df_consumo.empty:
        st.write("#### Consumo por Categoria")
        
        # Agrupar por categoria e somar quantidades
        if "Categoria" in df_consumo.columns:
            por_categoria = df_consumo.groupby("Categoria")["Quantidade Consumida"].sum().reset_index()
            por_categoria = por_categoria.sort_values("Quantidade Consumida", ascending=False)
            
            # Usar gráfico de barras do Streamlit
            st.bar_chart(por_categoria.set_index("Categoria"))
            
            # Recomendações de consumo
            st.write("#### 💡 Recomendações")
            
            # Identificar categoria mais consumida
            mais_consumida = por_categoria.iloc[0]["Categoria"]
            
            if opcao == "Consumo de Thomás":
                # Recomendações personalizadas para Thomas
                if mais_consumida in ["Doces/Sobremesas", "Snacks"]:
                    st.warning(f"""
                        ⚠️ **Alto consumo de {mais_consumida.lower()} por Thomás**
                        
                        Sugestão: Substituir gradualmente por alternativas mais saudáveis como frutas frescas sem açúcar adicionado.
                        
                        Para snacks, considere opções ricas em nutrientes como:
                        - Palitos de legumes
                        - Biscoitos sem leite e baixo açúcar
                    """)
                elif mais_consumida in ["Carnes", "Laticínios"]:
                    # Para Thomas, laticínios precisam de atenção especial
                    if mais_consumida == "Laticínios":
                        st.warning(f"""
                            ⚠️ **Atenção ao consumo de laticínios por Thomás**
                            
                            Certifique-se de que os produtos são adequados para suas restrições alimentares.
                            Use alternativas vegetais fortificadas sempre que possível.
                        """)
                    else:
                        st.info(f"""
                            ℹ️ **Consumo equilibrado de {mais_consumida.lower()}**
                            
                            Certifique-se de incluir boas fontes de ferro e proteínas adequadas para Thomás.
                        """)
                elif mais_consumida in ["Frutas", "Verduras", "Legumes"]:
                    st.success(f"""
                        ✅ **Excelente consumo de {mais_consumida.lower()} por Thomás!**
                        
                        Continue incentivando o consumo variado de vegetais e frutas para garantir
                        vitaminas e minerais essenciais para seu desenvolvimento.
                    """)
                else:
                    st.info(f"""
                        ℹ️ **Consumo de {mais_consumida.lower()}**
                        
                        Monitore a variedade na alimentação de Thomás para garantir nutrientes adequados.
                    """)
            else:
                # Recomendações gerais para consumo familiar
                if mais_consumida in ["Doces/Sobremesas", "Snacks"]:
                    st.warning(f"""
                        ⚠️ **Alto consumo de {mais_consumida.lower()}**
                        
                        Sugestão: Reduzir o consumo e substituir por alternativas mais saudáveis como frutas frescas.
                    """)
                elif mais_consumida in ["Carnes", "Laticínios"]:
                    st.info(f"""
                        ℹ️ **Consumo elevado de {mais_consumida.lower()}**
                        
                        Sugestão: Balancear com mais vegetais e considerar alternativas como legumes e proteínas vegetais.
                    """)
                else:
                    st.success(f"""
                        ✅ **Bom perfil de consumo**
                        
                        Continue com o consumo balanceado e variado.
                    """)

def mostrar_relatorio_nutricional(db):
    st.subheader("🥗 Análise Nutricional")
    
    # Carregar dados
    df = db.carregar_inventario()
    
    if df.empty:
        st.info("Ainda não há itens cadastrados com informações nutricionais.")
        return
    
    # Verificar se há colunas nutricionais
    if "Calorias/100g" not in df.columns:
        st.info("Não há informações nutricionais cadastradas no banco de dados.")
        return
    
    # Filtrar apenas itens com informações nutricionais
    df_nutri = df.dropna(subset=["Calorias/100g"])
    
    if df_nutri.empty:
        st.info("Nenhum item possui informações nutricionais cadastradas.")
        return
    
    # Visão geral nutricional
    st.write("#### Visão Geral por Nível de Saúde")
    
    # Contagem por nível de saúde
    if "Nível Saúde" in df.columns:
        contagem_saude = df.groupby("Nível Saúde").size().reset_index(name="Quantidade")
        contagem_saude["Nível"] = contagem_saude["Nível Saúde"].map({
            1: "Saudável", 
            2: "Intermediário", 
            3: "Alto impacto"
        })
        
        # Gráfico de barras usando Streamlit
        saude_data = contagem_saude.set_index("Nível")["Quantidade"]
        st.write("Distribuição de Alimentos por Nível de Saúde:")
        st.bar_chart(saude_data)
    
    # Ranking nutricional
    st.write("#### Ranking Nutricional")
    
    # Mais opções de visualização
    tab1, tab2 = st.tabs(["Ranking por Componente", "Alimentos Ricos em Nutrientes"])
    
    with tab1:
        # Selecionar característica para ranking
        caracteristica = st.selectbox(
            "Escolha a característica para classificação",
            ["Calorias/100g", "Açúcar/100g", "Sódio/100g"]
        )
        
        # Colunas para exibir
        colunas_ranking = ["Nome", "Categoria" if "Categoria" in df.columns else "Localização", caracteristica]
        if "Nível Saúde" in df.columns:
            colunas_ranking.append("Nível Saúde")
        
        # Ordenar por característica selecionada
        df_ordenado = df_nutri.dropna(subset=[caracteristica]).sort_values(caracteristica, ascending=False).head(10)
        
        # Exibir ranking
        config_dict = {}
        if caracteristica in df_ordenado.columns:
            config_dict[caracteristica] = st.column_config.NumberColumn(caracteristica, format="%.1f")
        if "Nível Saúde" in df_ordenado.columns:
            config_dict["Nível Saúde"] = st.column_config.NumberColumn(
                "Nível Saúde",
                help="1=Saudável, 2=Intermediário, 3=Alto impacto",
                format="%d"
            )
        
        st.dataframe(
            df_ordenado[colunas_ranking],
            use_container_width=True,
            column_config=config_dict
        )
    
    with tab2:
        # Selecionar nutriente para ver alimentos ricos
        nutriente = st.selectbox(
            "Alimentos ricos em:",
            ["Proteínas (g)", "Cálcio (mg)", "Ferro (mg)", "Vitamina D (mcg)", "Vitamina C (mg)"],
            index=1  # Padrão: Cálcio (importante para Thomas)
        )
        
        # Verificar se o nutriente está disponível
        if nutriente in df.columns:
            # Filtrar itens que têm este nutriente cadastrado
            df_com_nutriente = df.dropna(subset=[nutriente])
            
            if not df_com_nutriente.empty:
                # Ordenar por maior quantidade do nutriente
                df_nutriente_ranking = df_com_nutriente.sort_values(nutriente, ascending=False).head(10)
                
                # Exibir ranking
                st.write(f"#### Top 10 alimentos ricos em {nutriente}")
                
                # Configuração das colunas
                nutrient_config = {}
                nutrient_config["Nome"] = st.column_config.TextColumn("Nome")
                nutrient_config[nutriente] = st.column_config.NumberColumn(nutriente, format="%.1f")
                if "Compatibilidade Thomas" in df_nutriente_ranking.columns:
                    df_nutriente_ranking["Status Thomas"] = df_nutriente_ranking["Compatibilidade Thomas"].apply(format_compatibilidade)
                    nutrient_config["Status Thomas"] = st.column_config.TextColumn("Para Thomás")
                
                # Mostrar tabela
                st.dataframe(
                    df_nutriente_ranking[["Nome", nutriente] + (["Status Thomas"] if "Status Thomas" in df_nutriente_ranking.columns else [])],
                    use_container_width=True,
                    column_config=nutrient_config
                )
                
                # Gráfico de barras
                st.bar_chart(df_nutriente_ranking.set_index("Nome")[nutriente])
            else:
                st.info(f"Não há informações sobre {nutriente} cadastradas para nenhum item.")
        else:
            st.info(f"Informações sobre {nutriente} não disponíveis no banco de dados.")
    
    # Legenda de cores
    st.write("#### Legenda de Cores")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div style="{estilo_saude_cor(1)}; padding: 10px; border-radius: 5px;">Saudável</div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div style="{estilo_saude_cor(2)}; padding: 10px; border-radius: 5px;">Intermediário</div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div style="{estilo_saude_cor(3)}; padding: 10px; border-radius: 5px;">Alto impacto</div>', unsafe_allow_html=True)