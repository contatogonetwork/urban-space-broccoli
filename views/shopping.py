import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
from utils.formatters import *
from utils.constants import *

def mostrar_planejamento_feira(db):
    st.title("🛒 Fazer Feira")
    
    # Descrição da funcionalidade
    st.markdown("""
    Planeje sua feira com base nos melhores preços históricos e economize!
    
    Esta ferramenta analisa o histórico de preços dos produtos em diferentes locais de compra
    e sugere onde você deve comprar cada item para maximizar sua economia.
    """)
    
    # Abas para diferentes funcionalidades
    tab1, tab2, tab3 = st.tabs(["🛍️ Planejar Compras", "📊 Comparativo de Mercados", "📈 Análise de Preços"])
    
    with tab1:
        planejar_compras(db)
        
    with tab2:
        comparativo_mercados(db)
        
    with tab3:
        analise_precos(db)
    
def planejar_compras(db):
    """Interface para planejar compras"""
    st.subheader("🛍️ Planejar Compras")
    
    # Carregar inventário para seleção
    df_inventario = db.carregar_inventario()
    
    if df_inventario.empty:
        st.info("Nenhum item cadastrado para adicionar à lista de compras.")
        return
    
    # Obter locais de compra disponíveis
    locais_compra = db.obter_locais_compra()
    
    # Inicializar lista de compras na sessão se não existir
    if "lista_compras" not in st.session_state:
        st.session_state.lista_compras = {}
    
    # Formulário para adicionar item à lista
    with st.form("form_add_compra"):
        st.write("Adicionar item à lista de compras:")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Opção para selecionar do inventário ou criar novo
            opcao_origem = st.radio(
                "Origem do produto",
                ["Selecionar do inventário", "Adicionar novo produto"]
            )
            
            if opcao_origem == "Selecionar do inventário":
                # Filtro de pesquisa
                filtro_nome = st.text_input("Filtrar por nome:")
                
                # Filtrar itens
                items_filtrados = df_inventario
                if filtro_nome:
                    items_filtrados = df_inventario[df_inventario["Nome"].str.contains(filtro_nome, case=False)]
                
                # Evitar erro se não houver itens após filtro
                if items_filtrados.empty:
                    st.warning("Nenhum item encontrado com este filtro")
                    item_id = None
                    nome_produto = ""
                    unidade_padrao = "unidade"
                else:
                    # Selecionar item
                    opcoes_itens = items_filtrados["ID"].tolist()
                    format_opcoes = lambda x: f"{items_filtrados[items_filtrados['ID'] == x]['Nome'].values[0]} ({items_filtrados[items_filtrados['ID'] == x]['Unidade'].values[0]})"
                    
                    item_id = st.selectbox(
                        "Selecione um item:",
                        options=opcoes_itens,
                        format_func=format_opcoes
                    ) if not items_filtrados.empty else None
                    
                    # Mostrar tendência de preço
                    if item_id:
                        nome_produto = items_filtrados[items_filtrados["ID"] == item_id]["Nome"].values[0] 
                        unidade_padrao = items_filtrados[items_filtrados["ID"] == item_id]["Unidade"].values[0]
                        
                        # Verificar tendência só se existir a coluna
                        if 'Tendência' in items_filtrados.columns:
                            tendencia_row = items_filtrados[items_filtrados["ID"] == item_id]["Tendência"]
                            if not tendencia_row.empty and pd.notna(tendencia_row.values[0]):
                                tendencia = tendencia_row.values[0]
                                if tendencia == 1:
                                    st.warning("⚠️ Preço acima da média histórica")
                                elif tendencia == -1:
                                    st.success("✅ Preço abaixo da média histórica")
                            
            else:
                # Campos para novo produto
                nome_produto = st.text_input("Nome do novo produto:")
                unidade_padrao = st.selectbox("Unidade:", options=UNIDADES_MEDIDA)
                item_id = None
        
        with col2:
            quantidade = st.number_input("Quantidade:", min_value=0.1, value=1.0, step=0.1)
            
            # Preferências de locais
            st.write("Preferências de locais (opcional)")
            local_preferido = st.multiselect(
                "Prefiro comprar em:",
                options=locais_compra,
                help="Selecione locais de sua preferência para este item"
            )
        
        with col3:
            # Detalhes adicionais (opcional)
            st.write("Detalhes adicionais (opcional)")
            observacoes = st.text_area("Observações:", max_chars=100)
            urgencia = st.checkbox("Item urgente")
        
        # Botão de adicionar
        if st.form_submit_button("➕ Adicionar à Lista"):
            if not nome_produto:
                st.error("Por favor, informe o nome do produto.")
            else:
                # Se for novo produto, criar no banco
                if opcao_origem == "Adicionar novo produto":
                    success, msg, item_id = db.adicionar_produto_lista_compra(nome_produto, quantidade, unidade_padrao)
                    if not success:
                        st.error(msg)
                        return
                
                # Adicionar à lista de compras da sessão
                st.session_state.lista_compras[item_id] = {
                    "quantidade": quantidade,
                    "nome": nome_produto,
                    "unidade": unidade_padrao,
                    "local_preferido": local_preferido,
                    "observacoes": observacoes,
                    "urgencia": urgencia
                }
                st.success(f"'{nome_produto}' adicionado à lista!")
                st.rerun()
    
    # Exibir lista de compras atual
    st.subheader("Lista de Compras Atual")
    
    if not st.session_state.lista_compras:
        st.info("Sua lista de compras está vazia. Adicione itens acima.")
    else:
        # Converter lista para DataFrame para visualização
        lista_items = []
        for item_id, dados in st.session_state.lista_compras.items():
            lista_items.append({
                "ID": item_id,
                "Nome": dados["nome"],
                "Quantidade": dados["quantidade"],
                "Unidade": dados["unidade"],
                "Preferência": ", ".join(dados["local_preferido"]) if dados["local_preferido"] else "",
                "Observações": dados["observacoes"],
                "Urgente": "⚡" if dados["urgencia"] else ""
            })
        
        lista_df = pd.DataFrame(lista_items)
        
        # Configurar colunas
        config_dict = {
            "ID": st.column_config.NumberColumn("ID", width="small"),
            "Nome": st.column_config.TextColumn("Nome", width="medium"),
            "Quantidade": st.column_config.NumberColumn("Quantidade", format="%.2f"),
            "Unidade": st.column_config.TextColumn("Unidade", width="small"),
            "Preferência": st.column_config.TextColumn("Preferência"),
            "Observações": st.column_config.TextColumn("Observações"),
            "Urgente": st.column_config.TextColumn("Urgente", width="small")
        }
        
        # Exibir tabela editável
        edited_df = st.data_editor(
            lista_df,
            use_container_width=True,
            column_config=config_dict,
            num_rows="dynamic",
            hide_index=True,
            key="lista_compras_editor"
        )
        
        # Remover itens excluídos
        if len(edited_df) < len(lista_df):
            # Encontrar IDs que foram removidos
            ids_atuais = set(edited_df["ID"].tolist())
            ids_originais = set(lista_df["ID"].tolist())
            ids_removidos = ids_originais - ids_atuais
            
            # Remover da sessão
            for id_remover in ids_removidos:
                st.session_state.lista_compras.pop(id_remover, None)
            
            st.success(f"Removido(s) {len(ids_removidos)} item(ns) da lista.")
            st.rerun()
        
        # Atualizar quantidades
        for _, row in edited_df.iterrows():
            item_id = row["ID"]
            if item_id in st.session_state.lista_compras:
                st.session_state.lista_compras[item_id]["quantidade"] = row["Quantidade"]
    
    # Botões de ação
    if st.session_state.lista_compras:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🧹 Limpar Lista", use_container_width=True):
                st.session_state.lista_compras = {}
                st.rerun()
                
        with col2:
            if st.button("💰 Otimizar Compras", use_container_width=True):
                # Validar entradas
                produtos_ids = list(st.session_state.lista_compras.keys())
                if not produtos_ids:
                    st.error("❌ Adicione pelo menos um item à lista antes de otimizar!")
                    return
                    
                # Checar se há histórico de preços
                df_historico = db.obter_historico_preco_detalhado()
                if df_historico.empty:
                    st.warning("""
                    ⚠️ Não há histórico de preços disponível para análise!
                    
                    Para usar esta funcionalidade, você precisa ter um histórico de preços 
                    para os produtos. Adicione itens ao inventário com informações de preço
                    e local de compra.
                    """)
                    return
                
                # Preparar dados para simulação
                produtos_quantidades = {
                    int(id_item): dados["quantidade"] 
                    for id_item, dados in st.session_state.lista_compras.items()
                }
                
                # Obter locais preferidos gerais (união de todos os locais preferidos)
                locais_preferidos = set()
                for dados in st.session_state.lista_compras.values():
                    if dados["local_preferido"]:
                        locais_preferidos.update(dados["local_preferido"])
                
                locais_preferidos = list(locais_preferidos) if locais_preferidos else None
                
                # Simular feira
                try:
                    resultado_df, custo_total, economia_total, total_por_local = db.simular_feira(
                        produtos_quantidades, locais_preferencia=locais_preferidos
                    )
                    
                    if resultado_df.empty:
                        st.warning("Não foi possível simular a feira. Verifique se há histórico de preços para os produtos.")
                    else:
                        st.session_state.simulacao_feira = {
                            "resultado": resultado_df,
                            "custo_total": custo_total,
                            "economia_total": economia_total,
                            "total_por_local": total_por_local
                        }
                        # Mostrar resultados em nova aba
                        st.rerun()
                except Exception as e:
                    st.error(f"Erro ao simular feira: {e}")
    
    # Mostrar resultados da simulação
    if "simulacao_feira" in st.session_state:
        st.divider()
        st.subheader("📊 Resultados da Simulação")
        
        sim = st.session_state.simulacao_feira
        
        # Resumo financeiro
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Custo Total Estimado", f"R$ {sim['custo_total']:.2f}")
        with col2:
            st.metric("Economia Total Estimada", f"R$ {sim['economia_total']:.2f}")
        with col3:
            if sim['economia_total'] > 0 and sim['custo_total'] + sim['economia_total'] > 0:
                economia_percentual = (sim['economia_total'] / (sim['custo_total'] + sim['economia_total'])) * 100
                st.metric("Economia Percentual", f"{economia_percentual:.1f}%")
        
        # Distribuição por local
        st.subheader("Distribuição por Local de Compra")
        
        # Criar gráfico de distribuição
        if sim['total_por_local']:
            try:
                dist_data = [{"Local": local, "Valor": valor} for local, valor in sim['total_por_local'].items()]
                dist_df = pd.DataFrame(dist_data)
                
                # Proteção contra DataFrame vazio
                if not dist_df.empty:
                    fig = px.pie(
                        dist_df, 
                        values='Valor', 
                        names='Local', 
                        title='Distribuição de Gastos por Local',
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )
                    fig.update_traces(textposition='inside', textinfo='percent+label')
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Não foi possível gerar o gráfico de distribuição.")
            except Exception as e:
                st.error(f"Erro ao criar gráfico: {e}")
                st.info("Distribuição por local não disponível.")
        
        # Lista detalhada de compras por local
        st.subheader("Lista de Compras por Local")
        
        if not sim['resultado'].empty:
            # Agrupar por local
            for local in sorted(sim['resultado']['Local Recomendado'].unique()):
                with st.expander(f"🏪 {local}"):
                    try:
                        # Filtrar itens deste local
                        items_local = sim['resultado'][sim['resultado']['Local Recomendado'] == local]
                        
                        # Configurar colunas para exibição
                        local_config = {
                            "Nome": st.column_config.TextColumn("Nome", width="medium"),
                            "Quantidade": st.column_config.NumberColumn("Quantidade", format="%.2f"),
                            "Unidade": st.column_config.TextColumn("Unidade", width="small"),
                            "Preço Unitário": st.column_config.NumberColumn("Preço Unitário", format="R$ %.2f"),
                            "Preço Total": st.column_config.NumberColumn("Preço Total", format="R$ %.2f")
                        }
                        
                        # Verificar se "Economia (%)" está presente e não é nulo
                        if "Economia (%)" in items_local.columns and not items_local["Economia (%)"].isna().all():
                            local_config["Economia (%)"] = st.column_config.NumberColumn("Economia (%)", format="%.1f%%")
                            cols_to_show = ["Nome", "Quantidade", "Unidade", "Preço Unitário", "Preço Total", "Economia (%)"]
                        else:
                            cols_to_show = ["Nome", "Quantidade", "Unidade", "Preço Unitário", "Preço Total"]
                        
                        # Filtrar colunas válidas
                        cols_to_show = [col for col in cols_to_show if col in items_local.columns]
                        
                        # Exibir tabela deste local
                        st.dataframe(
                            items_local[cols_to_show],
                            use_container_width=True,
                            column_config=local_config,
                            hide_index=True
                        )
                        
                        # Total deste local
                        local_total = sim['total_por_local'].get(local, 0)
                        st.metric("Total neste local", f"R$ {local_total:.2f}")
                    except Exception as e:
                        st.error(f"Erro ao exibir itens do local {local}: {e}")
        
        # Opção para gerar lista de compras por local
        if st.button("📝 Gerar Lista para Impressão", use_container_width=True):
            try:
                lista_texto = "LISTA DE COMPRAS\n\n"
                
                # Ordenar locais alfabeticamente
                locais = sorted(sim['resultado']['Local Recomendado'].unique())
                
                for local in locais:
                    lista_texto += f"=== {local} ===\n"
                    items_local = sim['resultado'][sim['resultado']['Local Recomendado'] == local]
                    
                    # Ordenar itens por nome
                    items_local = items_local.sort_values("Nome")
                    
                    for _, item in items_local.iterrows():
                        # Verificar valores nulos
                        nome = item['Nome'] if pd.notna(item['Nome']) else "Item sem nome"
                        quantidade = item['Quantidade'] if pd.notna(item['Quantidade']) else 0
                        unidade = item['Unidade'] if pd.notna(item['Unidade']) else "un"
                        preco_total = item['Preço Total'] if pd.notna(item['Preço Total']) else 0
                        
                        lista_texto += f"[ ] {nome} - {quantidade} {unidade} - R$ {preco_total:.2f}\n"
                    
                    lista_texto += f"\nSubtotal: R$ {sim['total_por_local'].get(local, 0):.2f}\n\n"
                    
                lista_texto += f"\nTOTAL ESTIMADO: R$ {sim['custo_total']:.2f}"
                lista_texto += f"\nECONOMIA ESTIMADA: R$ {sim['economia_total']:.2f}"
                
                # Mostrar em texto
                st.text_area("Lista para Copiar", lista_texto, height=300)
            except Exception as e:
                st.error(f"Erro ao gerar lista para impressão: {e}")
                st.info("Tente novamente ou copie os dados manualmente da tabela acima.")

def comparativo_mercados(db):
    """Mostra comparativo de preços entre diferentes mercados"""
    st.subheader("📊 Comparativo de Mercados")
    
    # Obter dados estatísticos
    try:
        _, pivot_locais, melhores_locais = db.calcular_estatisticas_preco()
        
        if pivot_locais.empty:
            st.info("Ainda não há dados suficientes para comparar mercados. Registre preços em diferentes locais.")
            
            # Adicionar ajuda sobre como registrar preços
            st.markdown("""
            ### Como registrar preços para comparação:
            
            1. Adicione produtos ao inventário com valores de compra
            2. Cadastre o mesmo produto com preços em diferentes locais
            3. Volte a esta página quando tiver dados suficientes para comparação
            
            Você precisa ter pelo menos 2 locais de compra diferentes para o mesmo produto.
            """)
            return
        
        # Mostrar tabela de comparação
        st.write("#### Comparativo de Preços por Local")
        
        # Formatar valores para exibir como moeda
        formatted_pivot = pivot_locais.copy()
        for col in formatted_pivot.columns:
            formatted_pivot[col] = formatted_pivot[col].apply(lambda x: f"R$ {x:.2f}" if pd.notna(x) else "-")
        
        st.dataframe(formatted_pivot, use_container_width=True)
        
        # Mostrar melhores locais por produto
        if not melhores_locais.empty:
            st.write("#### Melhores Locais por Produto")
            
            # Configurar colunas
            config_dict = {
                "Nome": st.column_config.TextColumn("Nome", width="medium"),
                "melhor_local": st.column_config.TextColumn("Melhor Local"),
                "preco_medio": st.column_config.NumberColumn("Preço Médio", format="R$ %.2f"),
                "economia_percentual": st.column_config.ProgressColumn(
                    "Economia vs. Pior Preço",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100
                )
            }
            
            # Exibir tabela
            st.dataframe(
                melhores_locais,
                use_container_width=True,
                column_config=config_dict,
                hide_index=True
            )
        
        # Análise de economia potencial
        st.write("#### Economia Potencial")
        st.markdown("""
        Se você comprar cada produto no local mais barato disponível, sua economia potencial total 
        em comparação a comprar tudo no local mais caro pode chegar a valores significativos.
        
        **Importante:** Esta análise é baseada em dados históricos e os preços podem variar.
        Sempre verifique os preços atuais durante suas compras.
        """)
    except Exception as e:
        st.error(f"Erro ao processar comparativo de mercados: {e}")
        st.info("Tente novamente mais tarde ou verifique os dados no banco de dados.")

def analise_precos(db):
    """Mostra análise detalhada de preços por produto"""
    st.subheader("📈 Análise de Preços")
    
    # Obter tendências de preços
    try:
        tendencias_df, _, _ = db.calcular_estatisticas_preco()
        
        if tendencias_df.empty:
            st.warning("⚠️ Ainda não há dados históricos suficientes para análise de preços.")
            st.info("""
            Para gerar análises de preço, você precisa:
            1. Registrar preços de produtos em diferentes datas
            2. Registrar preços em diferentes locais de compra
            3. Ter pelo menos 2 registros por produto para calcular tendências
            
            Comece adicionando itens ao inventário com valores de compra.
            """)
            return
        
        # Selecionar produto para análise detalhada
        try:
            produto_id = st.selectbox(
                "Selecione um produto para análise detalhada",
                options=tendencias_df["ID"].tolist(),
                format_func=lambda x: tendencias_df[tendencias_df["ID"] == x]["Nome"].values[0]
            )
            
            # Filtrar dados do produto selecionado
            produto_dados = tendencias_df[tendencias_df["ID"] == produto_id].iloc[0]
            
            # Obter histórico de preços do produto
            historico = db.obter_historico_preco_detalhado(produto_id)
            
            # Exibir métricas do produto
            st.write(f"#### Análise de: {produto_dados['Nome']}")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Preço Médio", f"R$ {produto_dados['Preço Médio']:.2f}/{produto_dados['Unidade']}")
            with col2:
                st.metric("Preço Atual", f"R$ {produto_dados['Preço Último']:.2f}/{produto_dados['Unidade']}")
            with col3:
                delta = produto_dados["Variação Recente (%)"]
                delta_color = "inverse" if delta > 0 else "normal"
                st.metric(
                    "Variação Recente", 
                    f"{abs(delta):.1f}%", 
                    delta=f"{'subiu' if delta > 0 else 'caiu'}", 
                    delta_color=delta_color
                )
            
            # Exibir histórico em gráfico
            if not historico.empty:
                st.write("#### Histórico de Preços")
                
                # Preparar dados para gráfico
                historico['Data Compra'] = pd.to_datetime(historico['Data Compra'])
                
                try:
                    # Criar gráfico de linha
                    fig = px.line(
                        historico, 
                        x="Data Compra", 
                        y="Valor Unitário",
                        color="Local Compra",
                        title=f"Evolução de Preço: {produto_dados['Nome']}",
                        labels={"Valor Unitário": f"Preço por {produto_dados['Unidade']}", "Data Compra": "Data", "Local Compra": "Local"}
                    )
                    
                    # Adicionar linha de média
                    fig.add_hline(
                        y=produto_dados["Preço Médio"],
                        line_dash="dash",
                        line_color="gray",
                        annotation_text="Média histórica"
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Erro ao gerar gráfico: {e}")
                    st.info("Não foi possível criar o gráfico de evolução de preços.")
                
                # Tabela de histórico
                with st.expander("Ver histórico detalhado"):
                    # Formatar histórico para exibição
                    historico_exib = historico.copy()
                    historico_exib["Valor Unitário"] = historico_exib["Valor Unitário"].apply(lambda x: f"R$ {x:.2f}")
                    
                    # Config tabela
                    hist_config = {
                        "Data Compra": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                        "Local Compra": st.column_config.TextColumn("Local"),
                        "Valor Unitário": st.column_config.TextColumn(f"Valor por {produto_dados['Unidade']}")
                    }
                    
                    st.dataframe(
                        historico_exib[["Data Compra", "Local Compra", "Valor Unitário"]],
                        use_container_width=True,
                        column_config=hist_config,
                        hide_index=True
                    )
            
            # Análise de volatilidade
            st.write("#### Análise de Variação")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Variação Total", f"{produto_dados['Variação Total (%)']:.1f}%")
            with col2:
                st.metric("Volatilidade", f"{produto_dados['Volatilidade (%)']:.1f}%", 
                        help="Quanto maior, mais oscila o preço deste produto")
            
            # Recomendações baseadas na análise
            st.write("#### 💡 Recomendações")
            
            tendencia = produto_dados["Tendência"]
            volatilidade = produto_dados["Volatilidade (%)"]
            
            if tendencia == 1:  # Alta
                if volatilidade > 15:
                    st.warning("""
                    **Produto com tendência de alta e alta volatilidade.**
                    
                    Recomendação: Considere adiar a compra ou buscar alternativas, pois os preços estão 
                    elevados e instáveis. Se precisar comprar, pesquise bem em diferentes locais.
                    """)
                else:
                    st.warning("""
                    **Produto com tendência de alta, mas estável.**
                    
                    Recomendação: Os preços estão mais altos que o habitual, mas estáveis. 
                    Considere comprar apenas o necessário e buscar promoções.
                    """)
            elif tendencia == -1:  # Baixa
                if volatilidade > 15:
                    st.success("""
                    **Produto com tendência de baixa, mas com alta volatilidade.**
                    
                    Recomendação: Bom momento para comprar, mas os preços podem subir rapidamente.
                    Considere estocar se for não-perecível e tiver espaço.
                    """)
                else:
                    st.success("""
                    **Produto com tendência de baixa e estável.**
                    
                    Recomendação: Excelente momento para comprar. Os preços estão estáveis
                    e abaixo da média histórica. Considere estocar se for não-perecível.
                    """)
            else:  # Na média
                if volatilidade > 15:
                    st.info("""
                    **Produto com preços na média, mas com alta volatilidade.**
                    
                    Recomendação: O preço atual está na média histórica, mas tende a oscilar bastante.
                    Monitore os preços e compre quando houver reduções.
                    """)
                else:
                    st.info("""
                    **Produto com preços na média e estáveis.**
                    
                    Recomendação: Preço estável e dentro da média histórica.
                    Compre conforme sua necessidade sem pressa.
                    """)
                    
        except Exception as e:
            st.error(f"Erro na análise de preços: {e}")
            st.info("Não foi possível completar a análise de preços.")
            
    except Exception as e:
        st.error(f"Erro ao carregar dados de tendências: {e}")
        st.info("Verifique a conexão com o banco de dados e tente novamente.")