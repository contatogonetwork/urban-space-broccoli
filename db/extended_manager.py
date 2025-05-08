import pandas as pd
import sqlite3
from .manager import DatabaseManager
import streamlit as st
import datetime

class ExtendedDatabaseManager(DatabaseManager):
    """Versão estendida do DatabaseManager com funcionalidades avançadas de análise"""
    
    @st.cache_data(ttl=300)  # Cache por 5 minutos
    def obter_historico_preco_detalhado(_self, item_id=None):
        """Obtém o histórico detalhado de preços com análise estatística"""
        try:
            query_base = """
                SELECT 
                    i.id, 
                    i.nome,
                    h.data_compra,
                    h.valor_unitario,
                    h.local_compra,
                    i.unidade
                FROM historico_precos h
                JOIN itens i ON h.item_id = i.id
            """
            
            params = []
            if item_id:
                query_base += " WHERE h.item_id = ?"
                params = [item_id]
                
            query_base += " ORDER BY i.nome, h.data_compra DESC"
            
            _self.cursor.execute(query_base, params)
            rows = _self.cursor.fetchall()
            
            if not rows:
                return pd.DataFrame()
                
            # Criar DataFrame
            df = pd.DataFrame(rows, columns=[
                "ID", "Nome", "Data Compra", "Valor Unitário", "Local Compra", "Unidade"
            ])
            
            # Converter data
            df["Data Compra"] = pd.to_datetime(df["Data Compra"])
            
            return df
        
        except sqlite3.Error as e:
            print(f"Erro ao obter histórico de preços: {e}")
            return pd.DataFrame()

    @st.cache_data(ttl=300)  # Cache por 5 minutos
    def calcular_estatisticas_preco(_self):
        """Calcula estatísticas avançadas de preços dos produtos"""
        df = _self.obter_historico_preco_detalhado()
        
        if df.empty:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
        # Estatísticas por produto
        try:
            estatisticas_produtos = df.groupby(["ID", "Nome", "Unidade"]).agg(
                media=("Valor Unitário", "mean"),
                mediana=("Valor Unitário", "median"),
                minimo=("Valor Unitário", "min"),
                maximo=("Valor Unitário", "max"),
                desvio_padrao=("Valor Unitário", "std"),
                contagem=("Valor Unitário", "count"),
                ultima_compra=("Data Compra", "max")
            ).reset_index()
        except Exception as e:
            print(f"Erro ao calcular estatísticas: {e}")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
        # Para cada item, calcular a variação percentual em relação à média histórica
        resultado = []
        for item_id in estatisticas_produtos["ID"].unique():
            item_stats = estatisticas_produtos[estatisticas_produtos["ID"] == item_id].iloc[0]
            
            # Obter preços ordenados por data para este item
            precos_item = df[df["ID"] == item_id].sort_values("Data Compra")
            
            if len(precos_item) >= 2:
                ultimo_preco = precos_item.iloc[-1]["Valor Unitário"]
                primeiro_preco = precos_item.iloc[0]["Valor Unitário"]
                penultimo_preco = precos_item.iloc[-2]["Valor Unitário"] if len(precos_item) > 1 else primeiro_preco
                
                # Calcular tendências com proteção contra divisão por zero
                variacao_total = ((ultimo_preco - primeiro_preco) / primeiro_preco) * 100 if primeiro_preco != 0 else 0
                variacao_recente = ((ultimo_preco - penultimo_preco) / penultimo_preco) * 100 if penultimo_preco != 0 else 0
                
                # Calcular posição em relação à média
                posicao_media = ((ultimo_preco - item_stats["media"]) / item_stats["media"]) * 100 if item_stats["media"] != 0 else 0
                
                # Definir tendência: 
                # 1 = acima da média (alta)
                # 0 = na média
                # -1 = abaixo da média (baixa)
                if posicao_media > 5:
                    tendencia = 1  # Alta
                elif posicao_media < -5:
                    tendencia = -1  # Baixa
                else:
                    tendencia = 0  # Na média
                    
                # Calcular volatilidade (coeficiente de variação)
                volatilidade = (item_stats["desvio_padrao"] / item_stats["media"]) * 100 if item_stats["media"] != 0 else 0
                
                resultado.append({
                    "ID": item_id,
                    "Nome": item_stats["Nome"],
                    "Unidade": item_stats["Unidade"],
                    "Preço Médio": item_stats["media"],
                    "Preço Último": ultimo_preco,
                    "Variação Total (%)": variacao_total,
                    "Variação Recente (%)": variacao_recente,
                    "Posição vs Média (%)": posicao_media,
                    "Tendência": tendencia,
                    "Volatilidade (%)": volatilidade,
                    "Última Compra": item_stats["ultima_compra"],
                    "Histórico": len(precos_item)
                })
        
        # Estatísticas por local
        if "Local Compra" in df.columns and not df["Local Compra"].isna().all():
            try:
                estatisticas_locais = df.groupby(["Nome", "Local Compra"]).agg(
                    preco_medio=("Valor Unitário", "mean"),
                    ultima_data=("Data Compra", "max")
                ).reset_index()
                
                # Pivotar para comparar entre locais
                pivot_locais = estatisticas_locais.pivot(
                    index="Nome", 
                    columns="Local Compra", 
                    values="preco_medio"
                )
                
                # Adicionar melhor local para cada produto
                nomes_produtos = estatisticas_locais["Nome"].unique()
                melhor_local = {}
                
                for nome in nomes_produtos:
                    item_por_local = estatisticas_locais[estatisticas_locais["Nome"] == nome]
                    if len(item_por_local) > 1:  # Mais de um local para comparar
                        melhor = item_por_local.loc[item_por_local["preco_medio"].idxmin()]
                        preco_max = item_por_local["preco_medio"].max()
                        # Proteção contra divisão por zero
                        economia = ((preco_max - melhor["preco_medio"]) / preco_max) * 100 if preco_max != 0 else 0
                        melhor_local[nome] = {
                            "melhor_local": melhor["Local Compra"],
                            "preco_medio": melhor["preco_medio"],
                            "economia_percentual": economia
                        }
                
                # Criar DataFrame para melhor local
                if melhor_local:
                    melhores_locais_df = pd.DataFrame.from_dict(melhor_local, orient='index')
                    melhores_locais_df.index.name = "Nome"
                    melhores_locais_df.reset_index(inplace=True)
                else:
                    melhores_locais_df = pd.DataFrame()
            except Exception as e:
                print(f"Erro ao calcular estatísticas por local: {e}")
                pivot_locais = pd.DataFrame()
                melhores_locais_df = pd.DataFrame()
        else:
            pivot_locais = pd.DataFrame()
            melhores_locais_df = pd.DataFrame()
        
        return pd.DataFrame(resultado), pivot_locais, melhores_locais_df

    def simular_feira(self, produtos_quantidades, locais_preferencia=None):
        """
        Simula uma feira com base nos preços históricos e recomenda onde comprar cada item
        
        Args:
            produtos_quantidades: dict com {id_produto: quantidade}
            locais_preferencia: list de locais preferidos em ordem (opcional)
            
        Returns:
            DataFrame com simulação, custo total, economia
        """
        try:
            if not produtos_quantidades or len(produtos_quantidades) == 0:
                return pd.DataFrame(), 0, 0, {}
            
            # Obter histórico de preços
            produto_ids = list(produtos_quantidades.keys())
            
            # Verificar suporte a funções de window no SQLite
            try:
                self.cursor.execute("SELECT 1 WHERE 1=2")
                # Se chegou aqui é porque o SQLite suporta o SQL básico
                
                # Usar versão segura da consulta
                placeholders = ','.join(['?'] * len(produto_ids))
                
                # Tentar usar ROW_NUMBER()
                try:
                    query = f"""
                        WITH RankedPrices AS (
                            SELECT 
                                h.item_id, 
                                i.nome,
                                i.unidade,
                                h.local_compra,
                                h.valor_unitario,
                                h.data_compra,
                                ROW_NUMBER() OVER (PARTITION BY h.item_id, h.local_compra ORDER BY h.data_compra DESC) as rn
                            FROM historico_precos h
                            JOIN itens i ON h.item_id = i.id
                            WHERE h.item_id IN ({placeholders})
                        )
                        SELECT item_id, nome, unidade, local_compra, valor_unitario, data_compra
                        FROM RankedPrices
                        WHERE rn = 1
                        ORDER BY nome, local_compra
                    """
                    
                    self.cursor.execute(query, produto_ids)
                except sqlite3.OperationalError:
                    # Versão antiga do SQLite, usar abordagem alternativa
                    # Buscar todos os preços e depois filtrar em Python
                    query = f"""
                        SELECT 
                            h.item_id, 
                            i.nome,
                            i.unidade,
                            h.local_compra,
                            h.valor_unitario,
                            h.data_compra
                        FROM historico_precos h
                        JOIN itens i ON h.item_id = i.id
                        WHERE h.item_id IN ({placeholders})
                        ORDER BY h.item_id, h.local_compra, h.data_compra DESC
                    """
                    
                    self.cursor.execute(query, produto_ids)
                    
                    # Processar os resultados para obter o mais recente por item/local
                    rows_all = self.cursor.fetchall()
                    rows = []
                    
                    seen = set()
                    for row in rows_all:
                        item_local = (row[0], row[3])  # item_id, local_compra
                        if item_local not in seen:
                            rows.append(row)
                            seen.add(item_local)
            except sqlite3.Error as e:
                print(f"Erro na consulta SQL: {e}")
                return pd.DataFrame(), 0, 0, {}
                
            rows = self.cursor.fetchall()
            
            if not rows:
                return pd.DataFrame(), 0, 0, {}
                
            # Transformar em DataFrame
            precos_df = pd.DataFrame(rows, columns=[
                "ID", "Nome", "Unidade", "Local Compra", "Valor Unitário", "Data Compra"
            ])
            
            # Calcular média global e por local para cada produto
            precos_medios = precos_df.groupby(["ID", "Nome", "Local Compra"])["Valor Unitário"].mean().reset_index()
            precos_medios_globais = precos_df.groupby(["ID", "Nome"])["Valor Unitário"].mean().reset_index()
            precos_medios_globais = precos_medios_globais.rename(columns={"Valor Unitário": "Preço Médio Global"})
            
            # Para cada produto, encontrar o local mais barato
            melhor_local = {}
            for id_produto in produto_ids:
                produto_precos = precos_medios[precos_medios["ID"] == id_produto]
                
                if not produto_precos.empty:
                    # Se há locais preferidos, filtrar ou ordenar por eles
                    if locais_preferencia:
                        # Filtrar apenas os locais preferidos (caso o produto esteja disponível neles)
                        produto_precos_pref = produto_precos[produto_precos["Local Compra"].isin(locais_preferencia)]
                        
                        # Se não há dados nos locais preferidos, usar todos os locais
                        if not produto_precos_pref.empty:
                            produto_precos = produto_precos_pref
                    
                    try:
                        # Encontrar o local mais barato disponível
                        mais_barato = produto_precos.loc[produto_precos["Valor Unitário"].idxmin()]
                        melhor_local[id_produto] = {
                            "local": mais_barato["Local Compra"],
                            "preco": mais_barato["Valor Unitário"],
                        }
                    except Exception as e:
                        print(f"Erro ao encontrar local mais barato: {e}")
                        continue
            
            # Criar DataFrame de resultado
            resultados = []
            locais_compra = set()
            
            for id_produto, quantidade in produtos_quantidades.items():
                try:
                    nome_produto_df = precos_df[precos_df["ID"] == id_produto]["Nome"]
                    if nome_produto_df.empty:
                        # Buscar diretamente do banco se não estiver no DataFrame
                        self.cursor.execute("SELECT nome, unidade FROM itens WHERE id = ?", (id_produto,))
                        item_base = self.cursor.fetchone()
                        nome_produto = item_base[0] if item_base else f"Item ID {id_produto}"
                        unidade = item_base[1] if item_base else "unidade"
                    else:
                        nome_produto = nome_produto_df.iloc[0]
                        unidade = precos_df[precos_df["ID"] == id_produto]["Unidade"].iloc[0]
                    
                    if id_produto in melhor_local:
                        local_recomendado = melhor_local[id_produto]["local"]
                        preco_unitario = melhor_local[id_produto]["preco"]
                        locais_compra.add(local_recomendado)
                    else:
                        # Se não há histórico, usar dados diretamente do item
                        self.cursor.execute("SELECT nome, valor_compra, unidade FROM itens WHERE id = ?", (id_produto,))
                        item = self.cursor.fetchone()
                        if item and item[1]:  # Se tem valor de compra
                            preco_unitario = item[1]
                            local_recomendado = "Desconhecido"
                        else:
                            preco_unitario = None
                            local_recomendado = "Sem histórico"
                    
                    # Calcular preço total para este item
                    preco_total = preco_unitario * quantidade if preco_unitario else None
                    
                    # Calcular economia potencial
                    economia_percentual = None
                    valor_economia = None
                    
                    # Obter preço mais alto deste produto em outro local
                    produto_precos = precos_medios[precos_medios["ID"] == id_produto]
                    if not produto_precos.empty and len(produto_precos) > 1:
                        preco_max = produto_precos["Valor Unitário"].max()
                        # Proteção contra divisão por zero
                        if preco_max != 0 and preco_unitario is not None:
                            economia_percentual = ((preco_max - preco_unitario) / preco_max) * 100
                            valor_economia = (preco_max - preco_unitario) * quantidade
                    
                    # Calcular posição em relação à média global
                    posicao_vs_media = None
                    preco_medio_global_df = precos_medios_globais[precos_medios_globais["ID"] == id_produto]["Preço Médio Global"]
                    
                    if not preco_medio_global_df.empty and preco_unitario is not None:
                        preco_medio_global = preco_medio_global_df.iloc[0]
                        if preco_medio_global != 0:
                            posicao_vs_media = ((preco_unitario - preco_medio_global) / preco_medio_global) * 100
                    
                    resultados.append({
                        "ID": id_produto,
                        "Nome": nome_produto,
                        "Quantidade": quantidade,
                        "Unidade": unidade,
                        "Local Recomendado": local_recomendado,
                        "Preço Unitário": preco_unitario,
                        "Preço Total": preco_total,
                        "Economia (%)": economia_percentual,
                        "Valor Economizado": valor_economia,
                        "Posição vs Média (%)": posicao_vs_media
                    })
                except Exception as e:
                    print(f"Erro ao processar item {id_produto}: {e}")
                    # Continuar com o próximo item
            
            # Criar DataFrame final
            resultado_df = pd.DataFrame(resultados)
            
            # Calcular totais
            custo_total = resultado_df["Preço Total"].sum() if "Preço Total" in resultado_df.columns and not resultado_df["Preço Total"].empty else 0
            economia_total = resultado_df["Valor Economizado"].sum() if "Valor Economizado" in resultado_df.columns and not resultado_df["Valor Economizado"].empty else 0
            
            # Calcular total por local
            total_por_local = {}
            for local in locais_compra:
                itens_local = resultado_df[resultado_df["Local Recomendado"] == local]
                if "Preço Total" in itens_local.columns and not itens_local.empty:
                    total_por_local[local] = itens_local["Preço Total"].sum()
                else:
                    total_por_local[local] = 0
            
            return resultado_df, custo_total, economia_total, total_por_local
            
        except Exception as e:
            print(f"Erro ao simular feira: {e}")
            return pd.DataFrame(), 0, 0, {}

    def adicionar_produto_lista_compra(self, nome_produto, quantidade, unidade):
        """Adiciona um produto na lista de compras (onde não há histórico)"""
        try:
            with self.lock:
                # Verificar se o produto já existe na tabela de itens
                self.cursor.execute("SELECT id FROM itens WHERE LOWER(nome) = LOWER(?)", (nome_produto,))
                item = self.cursor.fetchone()
                
                if item:
                    # Produto existente, retorna ID
                    return True, "Produto adicionado à lista de compras", item[0]
                else:
                    # Novo produto, inserir na tabela itens com mínimo de informações
                    self.cursor.execute(
                        """INSERT INTO itens (nome, quantidade, unidade, localizacao, perecivel)
                        VALUES (?, ?, ?, ?, ?)""",
                        (nome_produto, quantidade, unidade, "A definir", 0)
                    )
                    
                    novo_id = self.cursor.lastrowid
                    self.conn.commit()
                    return True, "Novo produto adicionado à lista de compras", novo_id
        
        except sqlite3.Error as e:
            return False, f"Erro ao adicionar produto à lista: {e}", None

    def obter_locais_compra(self):
        """Obtém a lista de locais de compra registrados no sistema"""
        try:
            self.cursor.execute("SELECT DISTINCT local_compra FROM historico_precos WHERE local_compra IS NOT NULL AND local_compra != ''")
            locais = [row[0] for row in self.cursor.fetchall()]
            return sorted(locais) if locais else ["Local padrão"]
        except sqlite3.Error as e:
            print(f"Erro ao obter locais de compra: {e}")
            return ["Local padrão"]