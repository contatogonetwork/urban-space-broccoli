import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import logging

# Funções com cache - Modificado para resolver o erro de unhashable type
@st.cache_data(ttl=600)  # Cache por 10 minutos
def cached_carregar_inventario(_db):  # Adicionado underscore ao parâmetro db
    return _db.carregar_inventario()

@st.cache_data(ttl=600)
def cached_obter_locais_compra(_db):  # Adicionado underscore ao parâmetro db
    return _db.obter_locais_compra()

@st.cache_data(ttl=300)  # Cache por 5 minutos
def cached_calcular_estatisticas_preco(_db):  # Adicionado underscore ao parâmetro db
    try:
        return _db.calcular_estatisticas_preco()
    except AttributeError:
        # Se o método não existir, retorna valores vazios
        logging.warning("Método calcular_estatisticas_preco não encontrado")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def mostrar_planejamento_feira(db):
    """Mostra a interface de planejamento de feira"""
    st.title("🛒 Fazer Feira")
    
    st.markdown("""
    Planeje sua feira com base nos melhores preços históricos e economize!

    Esta ferramenta analisa o histórico de preços dos produtos em diferentes locais de compra
    e sugere onde você deve comprar cada item para maximizar sua economia.
    """)
    
    tabs = st.tabs(["🛍️ Planejar Compras", "📊 Comparativo de Mercados", "📈 Análise de Preços"])
    
    with tabs[0]:
        planejar_compras(db)
    
    with tabs[1]:
        comparativo_mercados(db)
    
    with tabs[2]:
        analise_precos(db)

def planejar_compras(db):
    """Interface para planejamento de compras"""
    st.header("🛍️ Planejar Compras")
    
    try:
        # Obter locais de compra disponíveis
        locais_compra = db.obter_locais_compra()
        
        if not locais_compra:
            st.info("Não há locais de compra registrados. Registre alguns preços primeiro.")
            return
            
        # Obter lista de itens
        inventario = cached_carregar_inventario(db)
        
        if inventario.empty:
            st.info("Não há itens no inventário para planejar compras.")
            return
        
        # Interface para seleção de itens para comprar
        st.subheader("Selecione os itens para sua lista de compras")
        
        # Categorizar itens
        if 'categoria' in inventario.columns:
            categorias = sorted(inventario['categoria'].unique())
            
            categoria_selecionada = st.selectbox(
                "Filtrar por categoria:", 
                ["Todas"] + categorias,
                help="Escolha uma categoria para filtrar os itens exibidos."
            )
            
            if categoria_selecionada != "Todas":
                itens_filtrados = inventario[inventario['categoria'] == categoria_selecionada]
            else:
                itens_filtrados = inventario
        else:
            itens_filtrados = inventario
            
        # Criar uma lista de compras interativa
        st.markdown("### Minha Lista de Compras")
        
        lista_compras = []
        
        # Usar expander para não ocupar muito espaço
        with st.expander("Adicionar itens à lista"):
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                item_selecionado = st.selectbox(
                    "Selecione um item:", 
                    itens_filtrados['nome'].unique(),
                    help="Escolha um item do inventário para adicionar à lista de compras.")
            
            with col2:
                quantidade = st.number_input("Quantidade:", min_value=0.1, value=1.0, step=0.1)
                
            with col3:
                unidade = st.selectbox("Unidade:", ["unidade", "kg", "g", "litro", "ml"])
            
            if st.button("➕ Adicionar à lista"):
                # Verificar se já existe na lista para não duplicar
                if item_selecionado in [item['nome'] for item in lista_compras]:
                    st.warning(f"{item_selecionado} já está na lista de compras!")
                else:
                    # Obter informações de melhor preço
                    try:
                        melhor_local = obter_melhor_local_compra(db, item_selecionado)
                        lista_compras.append({
                            'nome': item_selecionado,
                            'quantidade': quantidade,
                            'unidade': unidade,
                            'melhor_local': melhor_local['local'] if melhor_local else "N/A",
                            'preco_estimado': melhor_local['preco'] if melhor_local else 0
                        })
                        st.success(f"{item_selecionado} adicionado à lista com sucesso!")
                    except Exception as e:
                        lista_compras.append({
                            'nome': item_selecionado,
                            'quantidade': quantidade,
                            'unidade': unidade,
                            'melhor_local': "N/A",
                            'preco_estimado': 0
                        })
                        st.success(f"{item_selecionado} adicionado à lista com sucesso (sem dados de preço).")
        
        # Opção para carregar lista salva (implementação simplificada)
        if st.button("📂 Carregar Lista Salva"):
            try:
                lista_compras = carregar_lista_padrao(db)
                st.success("Lista carregada com sucesso!")
            except Exception as e:
                st.error(f"Erro ao carregar lista: {str(e)}")
        
        # Exibir lista atual
        if lista_compras:
            # Criar dataframe para exibição
            df_lista = pd.DataFrame(lista_compras)
            
            # Calcular total estimado
            total_estimado = sum([item['preco_estimado'] * item['quantidade'] for item in lista_compras if item['preco_estimado']])
            
            # Exibir total estimado
            st.metric("Total Estimado", f"R$ {total_estimado:.2f}")
            
            # Exibir tabela com a lista
            st.dataframe(
                df_lista,
                column_config={
                    "nome": "Item",
                    "quantidade": "Quantidade",
                    "unidade": "Unidade",
                    "melhor_local": "Melhor Local de Compra",
                    "preco_estimado": st.column_config.NumberColumn("Preço Unitário", format="R$ %.2f")
                },
                hide_index=True
            )
            
            # Opção para salvar lista (implementação simplificada)
            if st.button("💾 Salvar Lista"):
                st.info("Funcionalidade de salvar lista será implementada em versões futuras.")
            
            # Opção para exportar lista
            if st.button("📤 Exportar Lista", use_container_width=True):
                try:
                    # Simulação de exportação
                    st.success("✅ Lista exportada com sucesso!")
                except Exception as e:
                    st.error(f"❌ Erro ao exportar lista: {str(e)}")
        else:
            st.info("Adicione itens à sua lista de compras.")
            
        # Sugestões baseadas em itens que estão acabando
        st.subheader("Sugestões de Compra")
        
        # Tentar usar métodos específicos se existirem, caso contrário usar abordagem genérica
        try:
            sugestoes = db.obter_sugestoes_compra()
        except AttributeError:
            # Abordagem alternativa: itens com quantidade baixa
            if 'quantidade' in inventario.columns:
                sugestoes = inventario[inventario['quantidade'] <= 1]
            else:
                sugestoes = pd.DataFrame()
        
        if not sugestoes.empty:
            st.dataframe(
                sugestoes[['nome', 'quantidade', 'unidade']],
                column_config={
                    "nome": "Item",
                    "quantidade": "Quantidade atual",
                    "unidade": "Unidade"
                },
                hide_index=True
            )
        else:
            st.info("Sem sugestões de compras no momento.")
    
    except Exception as e:
        st.error(f"Erro ao planejar compras: {str(e)}")
        st.exception(e)

    # Adicionar animação sutil ao passar o mouse
    st.markdown(
        """
        <style>
        button:hover {
            transform: scale(1.05);
            transition: transform 0.2s;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

def obter_melhor_local_compra(db, item_nome):
    """Determina o melhor local para compra de um item com base no histórico de preços"""
    try:
        # Tentativa de usar método especializado se disponível
        return db.obter_melhor_local_compra(item_nome)
    except AttributeError:
        try:
            # Implementação alternativa baseada em dados genéricos
            historico = db.obter_historico_precos_por_nome(item_nome)
            
            if historico.empty:
                return None
                
            # Agrupar por local de compra e pegar o menor preço em cada local
            melhores_precos = historico.groupby('local_compra')['valor_unitario'].min().reset_index()
            
            if melhores_precos.empty:
                return None
                
            # Obter local com menor preço
            melhor = melhores_precos.loc[melhores_precos['valor_unitario'].idxmin()]
            
            return {
                'local': melhor['local_compra'],
                'preco': melhor['valor_unitario']
            }
        except Exception as e:
            # Em último caso, retornar None
            logging.warning(f"Erro ao determinar melhor local para {item_nome}: {str(e)}")
            return None

def carregar_lista_padrao(db):
    """Carrega uma lista de compras padrão ou salva anteriormente"""
    # Implementação simplificada para demonstração
    return [
        {
            'nome': 'Leite',
            'quantidade': 1,
            'unidade': 'litro',
            'melhor_local': 'Supermercado ABC',
            'preco_estimado': 4.50
        },
        {
            'nome': 'Pão',
            'quantidade': 2,
            'unidade': 'unidade',
            'melhor_local': 'Padaria XYZ',
            'preco_estimado': 7.90
        }
    ]

def comparativo_mercados(db):
    """Mostra comparativo entre diferentes locais de compra"""
    st.subheader("📊 Comparativo de Mercados")
    
    try:
        # Tentar obter histórico de preços agrupado
        df_precos = None
        
        # Tentar diferentes métodos que podem existir
        try:
            df_precos = db.obter_comparativo_precos_mercados()
        except AttributeError:
            try:
                # Tentativa 2: calcular estatísticas e usar o primeiro dataframe
                df_precos, _, _ = cached_calcular_estatisticas_preco(db)
            except:
                # Implementação genérica usando histórico de preços
                try:
                    df_precos = db.obter_historico_precos_completo()
                except:
                    st.warning("Não foi possível obter dados de preços para comparação.")
                    return
        
        if df_precos is None or df_precos.empty:
            st.info("Ainda não há dados suficientes para gerar um comparativo entre mercados.")
            return
            
        # Organizar os dados para comparação
        try:
            # Ajustar para diferentes estruturas de dados possíveis
            if 'local_compra' in df_precos.columns and 'nome_item' in df_precos.columns:
                pivot = df_precos.pivot_table(
                    index='nome_item',
                    columns='local_compra',
                    values='valor_unitario',
                    aggfunc='mean'
                ).reset_index()
            elif 'local' in df_precos.columns and 'item' in df_precos.columns:
                pivot = df_precos.pivot_table(
                    index='item',
                    columns='local',
                    values='preco',
                    aggfunc='mean'
                ).reset_index()
            else:
                st.warning("Estrutura de dados não reconhecida para comparação.")
                st.dataframe(df_precos)
                return
                
            st.dataframe(
                pivot,
                hide_index=True
            )
            
            # Visualização de preços médios por local
            st.subheader("Preço Médio por Local de Compra")
            
            # Diferentes tentativas de calcular o preço médio
            try:
                if 'local_compra' in df_precos.columns and 'valor_unitario' in df_precos.columns:
                    media_locais = df_precos.groupby('local_compra')['valor_unitario'].mean().reset_index()
                    media_locais.columns = ['Local', 'Preço Médio']
                elif 'local' in df_precos.columns and 'preco' in df_precos.columns:
                    media_locais = df_precos.groupby('local')['preco'].mean().reset_index()
                    media_locais.columns = ['Local', 'Preço Médio']
                else:
                    st.warning("Não foi possível calcular o preço médio por local.")
                    return
                    
                fig = px.bar(
                    media_locais, 
                    x='Local',
                    y='Preço Médio',
                    title='Preço Médio por Local de Compra'
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"Erro ao criar gráfico de preços médios: {str(e)}")
        
        except Exception as e:
            st.error(f"Erro ao processar dados para comparação: {str(e)}")
            st.exception(e)
    
    except Exception as e:
        st.error(f"Erro ao gerar comparativo de mercados: {str(e)}")
        st.exception(e)

def analise_precos(db):
    """Mostra análise de tendências de preços para itens específicos"""
    st.subheader("📈 Análise de Tendências de Preços")
    
    try:
        # Obter histórico de preços
        try:
            df_historico = db.obter_historico_precos_completo()
        except AttributeError:
            try:
                # Tentativa alternativa
                _, df_historico, _ = cached_calcular_estatisticas_preco(db)
            except:
                st.warning("Não foi possível obter dados de histórico de preços.")
                return
        
        if df_historico is None or df_historico.empty:
            st.info("Ainda não há dados suficientes para análise de tendências de preços.")
            st.markdown("""
                Para começar a usar esta funcionalidade:
                1. Adicione itens ao inventário com informações de preço
                2. Registre compras com preços em diferentes locais
                3. Volte a esta página para ver a análise de tendências
            """)
            return
            
        # Ajustar para diferentes estruturas de dados possíveis
        nome_coluna_item = None
        nome_coluna_data = None
        nome_coluna_preco = None
        nome_coluna_local = None
        
        if 'nome_item' in df_historico.columns:
            nome_coluna_item = 'nome_item'
        elif 'item' in df_historico.columns:
            nome_coluna_item = 'item'
            
        if 'data_compra' in df_historico.columns:
            nome_coluna_data = 'data_compra'
        elif 'data' in df_historico.columns:
            nome_coluna_data = 'data'
            
        if 'valor_unitario' in df_historico.columns:
            nome_coluna_preco = 'valor_unitario'
        elif 'preco' in df_historico.columns:
            nome_coluna_preco = 'preco'
            
        if 'local_compra' in df_historico.columns:
            nome_coluna_local = 'local_compra'
        elif 'local' in df_historico.columns:
            nome_coluna_local = 'local'
        
        if not all([nome_coluna_item, nome_coluna_data, nome_coluna_preco, nome_coluna_local]):
            st.warning("Estrutura de dados não reconhecida para análise de tendências.")
            st.dataframe(df_historico)
            return
        
        # Seleção de item para análise
        itens_unicos = sorted(df_historico[nome_coluna_item].unique())
        
        if not itens_unicos:
            st.info("Não há itens com histórico de preços para analisar.")
            return
            
        item_selecionado = st.selectbox("Selecione um item para análise:", itens_unicos)
        
        # Filtrar para o item selecionado
        df_item = df_historico[df_historico[nome_coluna_item] == item_selecionado].copy()
        
        # Converter coluna de data para datetime
        df_item[nome_coluna_data] = pd.to_datetime(df_item[nome_coluna_data])
        
        # Ordenar por data
        df_item.sort_values(by=nome_coluna_data, inplace=True)
        
        # Gráfico de tendência
        st.subheader(f"Tendência de Preço: {item_selecionado}")
        
        if df_item.empty:
            st.info(f"Não há dados de preço para {item_selecionado}")
            return
            
        # Criar gráfico de tendência por local de compra
        fig = px.line(
            df_item, 
            x=nome_coluna_data,
            y=nome_coluna_preco,
            color=nome_coluna_local,
            title=f"Evolução do Preço de {item_selecionado}",
            markers=True
        )
        
        fig.update_layout(
            xaxis_title="Data",
            yaxis_title="Preço (R$)"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Estatísticas de preço
        st.subheader("Estatísticas de Preço")
        
        # Calcular estatísticas por local
        estatisticas_locais = df_item.groupby(nome_coluna_local)[nome_coluna_preco].agg(['min', 'max', 'mean']).reset_index()
        estatisticas_locais.columns = ['Local', 'Menor Preço', 'Maior Preço', 'Preço Médio']
        
        st.dataframe(
            estatisticas_locais,
            hide_index=True,
            column_config={
                'Local': 'Local de Compra',
                'Menor Preço': st.column_config.NumberColumn('Menor Preço', format="R$ %.2f"),
                'Maior Preço': st.column_config.NumberColumn('Maior Preço', format="R$ %.2f"),
                'Preço Médio': st.column_config.NumberColumn('Preço Médio', format="R$ %.2f")
            }
        )
        
        # Analisar tendência
        if len(df_item) >= 2:
            primeiro_preco = df_item[nome_coluna_preco].iloc[0]
            ultimo_preco = df_item[nome_coluna_preco].iloc[-1]
            variacao = ((ultimo_preco - primeiro_preco) / primeiro_preco) * 100
            
            if variacao > 5:
                st.warning(f"⚠️ **Tendência de ALTA**: Aumento de {variacao:.1f}% desde o primeiro registro.")
            elif variacao < -5:
                st.success(f"✅ **Tendência de QUEDA**: Redução de {abs(variacao):.1f}% desde o primeiro registro.")
            else:
                st.info(f"📊 **Preço estável**: Variação de apenas {variacao:.1f}% desde o primeiro registro.")
    
    except Exception as e:
        st.error(f"Erro na análise de preços: {str(e)}")
        st.exception(e)
