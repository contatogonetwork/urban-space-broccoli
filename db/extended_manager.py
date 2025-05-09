import pandas as pd
import sqlite3
from .manager import DatabaseManager
import datetime

# Importação condicional do streamlit
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    # Fallback para o decorador de cache quando o streamlit não está disponível
    class StMock:
        @staticmethod
        def cache_data(ttl=None):
            def decorator(func):
                # ttl seria usado para expiração de cache
                def wrapper(*args, **kwargs):
                    # Se tivesse cache, usaria ttl aqui
                    return func(*args, **kwargs)
                return wrapper
            return decorator
    st = StMock()

class ExtendedDatabaseManager(DatabaseManager):
    """Versão estendida do DatabaseManager com funcionalidades avançadas de análise"""
    
    # Constantes
    TERMOS_LACTEOS = ["leite", "queijo", "iogurte", "manteiga", "requeijão", "creme", "whey", 
                     "lactose", "caseína", "nata", "leitelho", "dairy", "lacteo", "lácteo"]
    
    # Use um decorador que funciona com ou sem streamlit
    @st.cache_data(ttl=300) if STREAMLIT_AVAILABLE else st.cache_data(ttl=300)
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

    # Use um decorador que funciona com ou sem streamlit
    @st.cache_data(ttl=300) if STREAMLIT_AVAILABLE else st.cache_data(ttl=300)
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
            return False, f"Erro ao adicionar produto: {str(e)}", None

    def obter_locais_compra(self):
        """Obtém a lista de locais de compra registrados no sistema"""
        try:
            self.cursor.execute("SELECT DISTINCT local_compra FROM historico_precos WHERE local_compra IS NOT NULL AND local_compra != ''")
            locais = [row[0] for row in self.cursor.fetchall()]
            return sorted(locais) if locais else ["Local padrão"]
        except sqlite3.Error as e:
            print(f"Erro ao obter locais de compra: {e}")
            return ["Local padrão"]
            
    def verificar_integridade(self):
        """Verifica a integridade do banco de dados e retorna status"""
        try:
            # Verificar se as tabelas essenciais existem
            self.cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tabelas_existentes = {row[0] for row in self.cursor.fetchall()}
            
            # Verificar tabela itens (essencial)
            if 'itens' not in tabelas_existentes:
                return False, "Tabela 'itens' não encontrada. Banco de dados pode estar corrompido."
                
            # Verificar se há itens na tabela principal
            self.cursor.execute("SELECT COUNT(*) FROM itens")
            count = self.cursor.fetchone()[0]
            
            # Verificar inconsistências em itens (por exemplo, quantidade negativa)
            self.cursor.execute("SELECT COUNT(*) FROM itens WHERE quantidade < 0")
            itens_negativos = self.cursor.fetchone()[0]
            
            if itens_negativos > 0:
                return False, f"Existem {itens_negativos} itens com quantidade negativa"
                
            # Verificar itens sem categoria válida
            self.cursor.execute("""
                SELECT COUNT(*) FROM itens i 
                LEFT JOIN categorias c ON i.categoria_id = c.id
                WHERE i.categoria_id IS NOT NULL AND c.id IS NULL
            """)
            itens_sem_categoria = self.cursor.fetchone()[0]
            
            if itens_sem_categoria > 0:
                return False, f"Existem {itens_sem_categoria} itens com categoria inválida"
            
            # Verificar históricos de preços sem item válido
            self.cursor.execute("""
                SELECT COUNT(*) FROM historico_precos hp
                LEFT JOIN itens i ON hp.item_id = i.id
                WHERE i.id IS NULL
            """)
            preco_sem_item = self.cursor.fetchone()[0]
            
            if preco_sem_item > 0:
                return False, f"Existem {preco_sem_item} registros de preços sem item válido"
                
            return True, f"Banco de dados íntegro. Total de {count} itens cadastrados."
            
        except sqlite3.Error as e:
            return False, f"Erro ao verificar integridade: {str(e)}"
        except sqlite3.Error as e:
            return False, f"Erro ao verificar integridade: {str(e)}"
            
    def obter_itens_proximos_vencimento(self, dias=7):
        """
        Obtém itens próximos do vencimento dentro do período especificado
        
        Args:
            dias: Número de dias para considerar como "próximo do vencimento"
            
        Returns:
            Lista de dicionários com informações dos itens
        """
        try:
            # Obter data atual e data limite
            hoje = datetime.date.today()
            data_limite = hoje + datetime.timedelta(days=dias)
            
            # Converter para formato de string (YYYY-MM-DD)
            hoje_str = hoje.strftime("%Y-%m-%d")
            limite_str = data_limite.strftime("%Y-%m-%d")
            
            # Consulta para obter itens próximos do vencimento
            query = """
                SELECT 
                    id, 
                    nome, 
                    quantidade, 
                    unidade,
                    validade,
                    (julianday(validade) - julianday(?)) as dias_ate_vencer
                FROM itens 
                WHERE 
                    perecivel = 1 
                    AND validade IS NOT NULL 
                    AND validade != '' 
                    AND validade BETWEEN ? AND ? 
                ORDER BY validade
            """
            
            self.cursor.execute(query, (hoje_str, hoje_str, limite_str))
            rows = self.cursor.fetchall()
            
            # Criar lista de dicionários
            itens_proximos = []
            for row in rows:
                itens_proximos.append({
                    'id': row[0],
                    'nome': row[1],
                    'quantidade': row[2],
                    'unidade': row[3],
                    'data_validade': row[4],
                    'dias_ate_vencer': int(row[5])
                })
                
            return itens_proximos
            
        except sqlite3.Error as e:
            print(f"Erro ao buscar itens próximos do vencimento: {e}")
            return []
            
    def carregar_inventario(self, apenas_thomas=False):
        """
        Carrega todos os itens do inventário
        
        Args:
            apenas_thomas: Se True, filtra apenas itens adequados para Thomas
            
        Returns:
            DataFrame com os itens do inventário
        """
        try:
            # Base da consulta SQL
            query_base = """
                SELECT 
                    i.id,
                    i.nome,
                    i.quantidade,
                    i.unidade,
                    i.localizacao as "Localização",
                    i.categoria as "Categoria",
                    i.validade,
                    i.perecivel as "Perecível",
                    i.para_thomas as "Para Thomas",
                    i.contem_leite as "Contém Leite",
                    i.compatibilidade_thomas as "Compatibilidade Thomas",
                    i.valor_compra,
                    i.data_cadastro,
                    i.nivel_saude as "Nível Saúde",
                    
                    -- Informações nutricionais básicas
                    i.proteinas_g as "Proteínas (g)",
                    i.carboidratos_g as "Carboidratos (g)", 
                    i.gorduras_g as "Gorduras (g)",
                    i.calorias_100g as "Calorias/100g",
                    
                    -- Nutrientes específicos para Thomas
                    i.calcio_mg as "Cálcio (mg)",
                    i.ferro_mg as "Ferro (mg)",
                    i.vitamina_d_mcg as "Vitamina D (mcg)",
                    i.vitamina_c_mg as "Vitamina C (mg)",
                    
                    -- Informações adicionais
                    i.acucar_100g as "Açúcar/100g",
                    i.sodio_100g as "Sódio/100g"
                FROM itens i
            """
            
            # Adicionar filtro para Thomas se necessário
            if apenas_thomas:
                query_base += " WHERE i.para_thomas = 1"
                
            # Ordenação padrão
            query_base += " ORDER BY i.nome"
            
            # Executar consulta
            self.cursor.execute(query_base)
            rows = self.cursor.fetchall()
            
            # Obter nomes de colunas
            column_names = [description[0] for description in self.cursor.description]
            
            # Criar DataFrame
            df = pd.DataFrame(rows, columns=column_names)
            
            if not df.empty:
                # Converter datas para datetime
                if "validade" in df.columns:
                    df["validade"] = pd.to_datetime(df["validade"], errors='coerce')
                    df.rename(columns={"validade": "Validade"}, inplace=True)
                    
                    # Calcular dias até vencer
                    df["Dias Até Vencer"] = (df["Validade"].dt.date - datetime.date.today()).dt.days
                
                # Remover colunas com valores None ou vazios em todas as linhas
                df = df.loc[:, ~df.isna().all()]
                
            return df
            
        except sqlite3.Error as e:
            print(f"Erro ao carregar inventário: {e}")
            return pd.DataFrame()
            
    def buscar_itens(self, termo_busca):
        """
        Busca itens no inventário pelo termo especificado
        
        Args:
            termo_busca: Termo para buscar nos nomes dos itens
            
        Returns:
            Lista de dicionários com itens encontrados
        """
        try:
            # Garantir que o termo de busca é string
            termo_busca = str(termo_busca)
            
            # Busca com LIKE para encontrar correspondências parciais
            query = """
                SELECT 
                    id,
                    nome,
                    quantidade,
                    unidade,
                    localizacao,
                    validade,
                    perecivel
                FROM itens
                WHERE nome LIKE ?
                ORDER BY nome
                LIMIT 20
            """
            
            # Adicionar % para busca parcial
            termo_busca_pattern = f"%{termo_busca}%"
            
            self.cursor.execute(query, (termo_busca_pattern,))
            rows = self.cursor.fetchall()
            
            # Criar lista de resultados
            resultados = []
            for row in rows:
                dias_ate_vencer = None
                if row[5]:  # Se tem data de validade
                    try:
                        data_validade = datetime.datetime.strptime(row[5], "%Y-%m-%d").date()
                        dias_ate_vencer = (data_validade - datetime.date.today()).days
                    except (ValueError, TypeError):
                        pass
                        
                resultados.append({
                    'id': row[0],
                    'nome': row[1],
                    'quantidade': row[2],
                    'unidade': row[3],
                    'localizacao': row[4],
                    'validade': row[5],
                    'perecivel': row[6],
                    'dias_ate_vencer': dias_ate_vencer
                })
                
            return resultados
            
        except sqlite3.Error as e:
            print(f"Erro ao buscar itens: {e}")
            return []
    
    def carregar_configuracoes(self):
        """Carrega configurações do banco de dados"""
        try:
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='configuracoes'")
            table_exists = self.cursor.fetchone()
            
            if not table_exists:
                # Criar tabela se não existir
                self.cursor.execute("""
                    CREATE TABLE configuracoes (
                        chave TEXT PRIMARY KEY,
                        valor TEXT
                    )
                """)
                self.conn.commit()
                return {}
                
            # Buscar configurações
            self.cursor.execute("SELECT chave, valor FROM configuracoes")
            config_rows = self.cursor.fetchall()
            
            config = {}
            for chave, valor in config_rows:
                # Converter tipos
                try:
                    if valor.lower() == 'true':
                        config[chave] = True
                    elif valor.lower() == 'false':
                        config[chave] = False
                    elif valor.isdigit():
                        config[chave] = int(valor)
                    elif '.' in valor and all(p.isdigit() for p in valor.split('.', 1)):
                        config[chave] = float(valor)
                    else:
                        config[chave] = valor
                except:
                    config[chave] = valor
                    
            # Carregar configurações padrão do config.py se estiverem faltando
            from config import load_config
            defaults = load_config()
            
            for key, value in defaults.items():
                if key not in config:
                    config[key] = value
                    
            return config
            
        except sqlite3.Error as e:
            print(f"Erro ao carregar configurações: {e}")
            # Retornar configurações padrão em caso de erro
            from config import load_config
            return load_config()
    
    def salvar_configuracoes(self, config_dict):
        """Salva as configurações no banco de dados"""
        try:
            with self.lock:
                # Verificar se a tabela existe
                self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='configuracoes'")
                if not self.cursor.fetchone():
                    self.cursor.execute("""
                        CREATE TABLE configuracoes (
                            chave TEXT PRIMARY KEY,
                            valor TEXT
                        )
                    """)
                
                # Salvar cada configuração
                for chave, valor in config_dict.items():
                    # Converter para string para salvar no banco
                    valor_str = str(valor)
                    
                    # Atualizar se existe, inserir se não existe
                    self.cursor.execute("""
                        INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES (?, ?)
                    """, (chave, valor_str))
                
                self.conn.commit()
                return True, "Configurações salvas com sucesso."
                
        except sqlite3.Error as e:
            return False, f"Erro ao salvar configurações: {str(e)}"
    
    def carregar_configuracoes_alertas(self):
        """Carrega configurações específicas de alertas"""
        try:
            config = self.carregar_configuracoes()
            
            # Filtrar apenas configurações relacionadas a alertas
            alerta_keys = [
                "habilitar_alertas_vencimento", "dias_antecedencia", 
                "sempre_mostrar_vencidos", "habilitar_alertas_estoque",
                "percentual_estoque", "habilitar_alertas_thomas",
                "prioridade_thomas", "monitorar_nutricao_thomas",
                "limite_alerta_nutricional"
            ]
            
            alertas_config = {k: config.get(k, False) for k in alerta_keys}
            
            # Valores padrão
            if "habilitar_alertas_vencimento" not in alertas_config:
                alertas_config["habilitar_alertas_vencimento"] = True
            if "dias_antecedencia" not in alertas_config:
                alertas_config["dias_antecedencia"] = 7
            if "sempre_mostrar_vencidos" not in alertas_config:
                alertas_config["sempre_mostrar_vencidos"] = True
            if "habilitar_alertas_estoque" not in alertas_config:
                alertas_config["habilitar_alertas_estoque"] = True
            if "percentual_estoque" not in alertas_config:
                alertas_config["percentual_estoque"] = 20
            if "habilitar_alertas_thomas" not in alertas_config:
                alertas_config["habilitar_alertas_thomas"] = True
            if "prioridade_thomas" not in alertas_config:
                alertas_config["prioridade_thomas"] = 3
            if "monitorar_nutricao_thomas" not in alertas_config:
                alertas_config["monitorar_nutricao_thomas"] = True
            if "limite_alerta_nutricional" not in alertas_config:
                alertas_config["limite_alerta_nutricional"] = 70
                
            return alertas_config
            
        except Exception as e:
            print(f"Erro ao carregar configurações de alertas: {e}")
            # Retornar valores padrão
            return {
                "habilitar_alertas_vencimento": True,
                "dias_antecedencia": 7,
                "sempre_mostrar_vencidos": True,
                "habilitar_alertas_estoque": True,
                "percentual_estoque": 20,
                "habilitar_alertas_thomas": True,
                "prioridade_thomas": 3,
                "monitorar_nutricao_thomas": True,
                "limite_alerta_nutricional": 70
            }
    
    def salvar_configuracoes_alertas(self, config_alertas):
        """Salva configurações específicas de alertas"""
        try:
            # Carregar todas as configurações atuais
            config_completo = self.carregar_configuracoes()
            
            # Atualizar com as configurações de alerta
            config_completo.update(config_alertas)
            
            # Salvar configurações atualizadas
            return self.salvar_configuracoes(config_completo)
            
        except Exception as e:
            return False, f"Erro ao salvar configurações de alertas: {str(e)}"
    
    def obter_estatisticas_consumo(self, apenas_thomas=False, periodo_dias=30):
        """
        Obtém estatísticas de consumo para o período especificado
        
        Args:
            apenas_thomas: Se True, filtra apenas consumo de Thomas
            periodo_dias: Período em dias para análise
            
        Returns:
            DataFrame com dados de consumo
        """
        try:
            # Escolher tabela baseado no filtro
            tabela = "consumo_thomas" if apenas_thomas else "consumo_geral"
            
            # Construir consulta
            query = f"""
                SELECT 
                    i.id,
                    i.nome,
                    c.categoria,
                    SUM(cg.quantidade_consumida) as quantidade_consumida,
                    i.unidade,
                    MAX(cg.data_consumo) as ultima_data
                FROM {tabela} cg
                JOIN itens i ON cg.item_id = i.id
                LEFT JOIN categorias c ON i.categoria_id = c.id
                WHERE cg.data_consumo >= date('now', ?)
                GROUP BY i.id, i.nome, c.categoria, i.unidade
                ORDER BY quantidade_consumida DESC
            """
            
            # Executar consulta
            self.cursor.execute(query, (f'-{periodo_dias} days',))
            rows = self.cursor.fetchall()
            
            if not rows:
                return pd.DataFrame()
                
            # Criar DataFrame
            df = pd.DataFrame(rows, columns=[
                "ID", "Nome", "Categoria", "Quantidade Consumida", "Unidade", "Última Data"
            ])
            
            # Adicionar informações nutricionais se forem para Thomas
            if apenas_thomas:
                try:
                    # Obter dados nutricionais
                    nutrientes = self.obter_nutrientes_consumidos(apenas_thomas=True, periodo_dias=periodo_dias)
                    
                    if not nutrientes.empty:
                        # Agrupar por nutriente e calcular totais
                        nutrientes_totais = nutrientes.groupby("Nutriente")["Total"].sum().reset_index()
                        
                        # Converter para dicionário para facilitar o acesso
                        nutrientes_dict = {r["Nutriente"]: r["Total"] for _, r in nutrientes_totais.iterrows()}
                        
                        # Adicionar colunas
                        for nutriente, valor in nutrientes_dict.items():
                            df[f"{nutriente} Consumido"] = valor
                except Exception as e:
                    print(f"Erro ao adicionar informações nutricionais: {e}")
            
            return df
            
        except sqlite3.Error as e:
            print(f"Erro ao obter estatísticas de consumo: {e}")
            return pd.DataFrame()
    
    def carregar_por_categoria(self, categoria):
        """Carrega itens de uma categoria específica"""
        try:
            # Construir consulta SQL
            query = """
                SELECT 
                    i.id,
                    i.nome,
                    i.quantidade,
                    i.unidade,
                    i.localizacao as "Localização",
                    c.nome as "Categoria",
                    i.validade,
                    i.perecivel as "Perecível",
                    i.para_thomas as "Para Thomas",
                    i.contem_leite as "Contém Leite",
                    i.compatibilidade_thomas as "Compatibilidade Thomas",
                    i.valor_compra,
                    i.data_cadastro,
                    i.nivel_saude as "Nível Saúde"
                FROM itens i
                LEFT JOIN categorias c ON i.categoria_id = c.id
                WHERE c.nome = ?
                ORDER BY i.nome
            """
            
            # Executar consulta
            self.cursor.execute(query, (categoria,))
            rows = self.cursor.fetchall()
            
            if not rows:
                return pd.DataFrame()
                
            # Obter nomes de colunas
            column_names = [description[0] for description in self.cursor.description]
            
            # Criar DataFrame
            df = pd.DataFrame(rows, columns=column_names)
            
            if not df.empty:
                # Converter datas para datetime
                if "validade" in df.columns:
                    df["validade"] = pd.to_datetime(df["validade"], errors='coerce')
                    df.rename(columns={"validade": "Validade"}, inplace=True)
                    
                    # Calcular dias até vencer
                    df["Dias Até Vencer"] = (df["Validade"].dt.date - datetime.date.today()).dt.days
                
                # Remover colunas com valores None ou vazios em todas as linhas
                df = df.loc[:, ~df.isna().all()]
                
            return df
            
        except sqlite3.Error as e:
            print(f"Erro ao carregar itens por categoria: {e}")
            return pd.DataFrame()
    
    def obter_categorias(self):
        """Obtém a lista de categorias cadastradas"""
        try:
            self.cursor.execute("""
                SELECT DISTINCT categoria FROM itens
                WHERE categoria IS NOT NULL AND categoria != ''
                ORDER BY categoria
            """)
            categorias = [row[0] for row in self.cursor.fetchall()]
            return categorias
            
        except sqlite3.Error as e:
            print(f"Erro ao obter categorias: {e}")
            return []
    
    def obter_restricoes_thomas(self):
        """Obtém as restrições alimentares de Thomas"""
        try:
            self.cursor.execute("""
                SELECT id, tipo, substancia, nivel_gravidade, sintomas, substituicoes
                FROM restricoes_thomas
                WHERE ativo = 1
                ORDER BY nivel_gravidade DESC
            """)
            rows = self.cursor.fetchall()
            
            return [
                {
                    "id": row[0],
                    "tipo": row[1],
                    "substancia": row[2],
                    "nivel": row[3],
                    "sintomas": row[4],
                    "substituicoes": row[5]
                }
                for row in rows
            ]
            
        except sqlite3.Error as e:
            print(f"Erro ao obter restrições de Thomas: {e}")
            return []
    
    def obter_tendencia_precos(self):
        """Obtém a tendência de preços para análise"""
        return self.obter_historico_preco_detalhado()
    
    def carregar_item_por_id(self, item_id):
        """Carrega informações de um item específico pelo ID"""
        try:
            if not isinstance(item_id, int):
                return None
                
            # Construir consulta SQL
            query = """
                SELECT *
                FROM itens
                WHERE id = ?
            """
            
            # Executar consulta
            self.cursor.execute(query, (item_id,))
            row = self.cursor.fetchone()
            
            if not row:
                return None
                
            # Obter nomes de colunas
            column_names = [description[0] for description in self.cursor.description]
            
            # Criar DataFrame
            df = pd.DataFrame([row], columns=column_names)
            return df
            
        except sqlite3.Error as e:
            print(f"Erro ao carregar item {item_id}: {e}")
            return None
    
    def registrar_consumo(self, item_id, quantidade, para_thomas=False, data=None):
        """
        Registra o consumo de um item
        
        Args:
            item_id: ID do item consumido
            quantidade: Quantidade consumida
            para_thomas: Se o consumo foi para Thomas
            data: Data do consumo (opcional, padrão é data atual)
            
        Returns:
            Tuple (bool, str): Status e mensagem
        """
        try:
            # Validar parâmetros
            if not isinstance(item_id, int) or item_id <= 0:
                return False, "ID do item inválido"
                
            if not isinstance(quantidade, (int, float)) or quantidade <= 0:
                return False, "Quantidade deve ser maior que zero"
            
            # Verificar se o item existe
            self.cursor.execute("SELECT id, nome, quantidade FROM itens WHERE id = ?", (item_id,))
            item = self.cursor.fetchone()
            
            if not item:
                return False, f"Item ID {item_id} não encontrado"
                
            item_nome = item[1]
            item_qtd_atual = item[2]
            
            # Verificar se há quantidade suficiente
            if quantidade > item_qtd_atual:
                return False, f"Quantidade insuficiente. Disponível: {item_qtd_atual}"
            
            # Definir data
            if not data:
                data = datetime.date.today()
                
            # Atualizar estoque
            nova_qtd = item_qtd_atual - quantidade
            
            # Determinar tabela para registro
            tabela = "consumo_thomas" if para_thomas else "consumo_geral"
            
            with self.lock:
                # Atualizar quantidade no estoque
                self.cursor.execute(
                    "UPDATE itens SET quantidade = ? WHERE id = ?",
                    (nova_qtd, item_id)
                )
                
                # Registrar consumo
                self.cursor.execute(
                    f"INSERT INTO {tabela} (item_id, quantidade_consumida, data_consumo) VALUES (?, ?, ?)",
                    (item_id, quantidade, data)
                )
                
                self.conn.commit()
                
            # Registrar nutrientes consumidos se tiver o método
            try:
                from utils.nutrition import registrar_nutrientes_consumidos
                registrar_nutrientes_consumidos(self, item_id, quantidade, para_thomas, data)
            except ImportError:
                # Se o módulo não estiver disponível, apenas ignorar
                pass
                
            return True, f"Consumo de {quantidade} {item_nome} registrado com sucesso"
            
        except sqlite3.Error as e:
            return False, f"Erro ao registrar consumo: {str(e)}"
    
    def restaurar_inventario(self, inventario_data):
        """
        Restaura inventário a partir de dados de backup
        
        Args:
            inventario_data: Dicionário com dados do inventário
            
        Returns:
            Tuple (bool, str): Status e mensagem
        """
        try:
            if not inventario_data:
                return False, "Dados de inventário vazios ou inválidos"
                
            # Converter back para DataFrame
            df = pd.DataFrame(inventario_data)
            
            if df.empty:
                return False, "Dados de inventário vazios"
                
            # Limpar tabela atual
            with self.lock:
                self.cursor.execute("DELETE FROM itens")
                
                # Inserir novos dados
                for _, row in df.iterrows():
                    # Preparar valores para inserção
                    valores = {}
                    for col in df.columns:
                        if pd.notna(row[col]):
                            valores[col] = row[col]
                    
                    # Gerar query dinâmica
                    colunas = ", ".join(valores.keys())
                    placeholders = ", ".join("?" for _ in valores)
                    
                    query = f"INSERT INTO itens ({colunas}) VALUES ({placeholders})"
                    
                    # Executar
                    self.cursor.execute(query, list(valores.values()))
                
                self.conn.commit()
                
            return True, f"Inventário restaurado com sucesso. Total de {len(df)} itens."
            
        except Exception as e:
            return False, f"Erro ao restaurar inventário: {str(e)}"
    
    def restaurar_consumo(self, consumo_data):
        """Stub para compatibilidade com funções de backup/restauração"""
        return True, "Função de restauração de consumo ainda não implementada"
    
    def restaurar_restricoes_thomas(self, restricoes):
        """Stub para compatibilidade com funções de backup/restauração"""
        return True, "Função de restauração de restrições ainda não implementada"
    
    def restaurar_necessidades_thomas(self, necessidades):
        """Stub para compatibilidade com funções de backup/restauração"""
        return True, "Função de restauração de necessidades nutricionais ainda não implementada"
    
    def adicionar_item(self, nome, qtd, unidade, local, categoria, perecivel, 
                      validade=None, valor_compra=None, local_compra=None, 
                      calorias=None, proteinas=None, carboidratos=None, 
                      gorduras=None, fibras=None, calcio=None, ferro=None, 
                      vitamina_a=None, vitamina_c=None, vitamina_d=None, 
                      acucar=None, sodio=None, ingredientes=None, 
                      para_thomas=False, contem_leite=False):
        """
        Adiciona um novo item ao inventário
        
        Returns:
            Tuple (bool, str): Status e mensagem
        """
        try:
            # Validar dados obrigatórios
            if not nome:
                return False, "Nome do item é obrigatório"
            if qtd <= 0:
                return False, "Quantidade deve ser maior que zero"
            
            # Verificar compatibilidade para Thomas
            compatibilidade_thomas = 2  # Padrão: Verificar
            
            if para_thomas:
                if contem_leite:
                    # Thomas tem restrição a leite, baixa compatibilidade
                    compatibilidade_thomas = 1
                else:
                    # Analisar ingredientes para Thomas
                    if ingredientes:
                        # Se contém termos lácteos nos ingredientes
                        if any(termo in ingredientes.lower() for termo in self.TERMOS_LACTEOS):
                            compatibilidade_thomas = 1
                        else:
                            compatibilidade_thomas = 3  # Compatível
                    else:
                        compatibilidade_thomas = 3  # Sem ingredientes informados, assumir compatível
            
            # Nível de saúde com base nos nutrientes (1=Saudável, 2=Intermediário, 3=Alto impacto)
            nivel_saude = 2  # Padrão: Intermediário
            
            if acucar is not None or sodio is not None:
                # Critérios simplificados
                acucar_alto = acucar > 10 if acucar is not None else False
                sodio_alto = sodio > 400 if sodio is not None else False
                
                if acucar_alto or sodio_alto:
                    nivel_saude = 3  # Alto impacto
                    
            if fibras is not None or vitamina_c is not None or calcio is not None:
                # Critérios simplificados para alimentos saudáveis
                fibra_boa = fibras > 3 if fibras is not None else False
                vitamina_c_boa = vitamina_c > 15 if vitamina_c is not None else False
                calcio_bom = calcio > 100 if calcio is not None else False
                
                if fibra_boa or vitamina_c_boa or calcio_bom:
                    nivel_saude = 1  # Saudável
            
            # Inserir no banco
            with self.lock:
                self.cursor.execute("""
                    INSERT INTO itens (
                        nome, quantidade, unidade, localizacao, categoria, perecivel,
                        validade, valor_compra, local_compra, 
                        calorias_100g, proteinas_g, carboidratos_g, gorduras_g, fibras_g,
                        calcio_mg, ferro_mg, vitamina_a_mcg, vitamina_c_mg, vitamina_d_mcg,
                        acucar_100g, sodio_100g, ingredientes,
                        saudavel, nivel_saude, para_thomas, contem_leite, compatibilidade_thomas
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    nome, qtd, unidade, local, categoria, perecivel,
                    validade, valor_compra, local_compra,
                    calorias, proteinas, carboidratos, gorduras, fibras,
                    calcio, ferro, vitamina_a, vitamina_c, vitamina_d,
                    acucar, sodio, ingredientes,
                    1, nivel_saude, para_thomas, contem_leite, compatibilidade_thomas
                ))
                
                novo_id = self.cursor.lastrowid
                
                # Se tiver valor de compra, registrar no histórico
                if valor_compra and valor_compra > 0 and local_compra:
                    data_compra = datetime.date.today()
                    self.cursor.execute("""
                        INSERT INTO historico_precos (item_id, data_compra, valor_unitario, local_compra)
                        VALUES (?, ?, ?, ?)
                    """, (novo_id, data_compra, valor_compra, local_compra))
                
                self.conn.commit()
                
            return True, f"Item '{nome}' adicionado com sucesso"
            
        except sqlite3.Error as e:
            return False, f"Erro ao adicionar item: {str(e)}"
    
    def atualizar_item(self, item_id, nome, qtd, unidade, local, categoria, perecivel, 
                      validade=None, valor_compra=None, local_compra=None, 
                      calorias=None, proteinas=None, carboidratos=None, 
                      gorduras=None, fibras=None, calcio=None, ferro=None, 
                      vitamina_a=None, vitamina_c=None, vitamina_d=None, 
                      acucar=None, sodio=None, ingredientes=None, 
                      para_thomas=False, contem_leite=False):
        """
        Atualiza um item existente no inventário
        
        Returns:
            Tuple (bool, str): Status e mensagem
        """
        try:
            # Validar dados obrigatórios
            if not isinstance(item_id, int) or item_id <= 0:
                return False, "ID do item inválido"
            if not nome:
                return False, "Nome do item é obrigatório"
            if qtd < 0:
                return False, "Quantidade não pode ser negativa"
                
            # Verificar se o item existe
            self.cursor.execute("SELECT id FROM itens WHERE id = ?", (item_id,))
            if not self.cursor.fetchone():
                return False, f"Item ID {item_id} não encontrado"
                
            # Verificar compatibilidade para Thomas
            compatibilidade_thomas = 2  # Padrão: Verificar
            
            if para_thomas:
                if contem_leite:
                    # Thomas tem restrição a leite, baixa compatibilidade
                    compatibilidade_thomas = 1
                else:
                    # Analisar ingredientes para Thomas
                    if ingredientes:
                        # Se contém termos lácteos nos ingredientes
                        if any(termo in ingredientes.lower() for termo in self.TERMOS_LACTEOS):
                            compatibilidade_thomas = 1
                        else:
                            compatibilidade_thomas = 3  # Compatível
                    else:
                        compatibilidade_thomas = 3  # Sem ingredientes informados, assumir compatível
            
            # Nível de saúde com base nos nutrientes (1=Saudável, 2=Intermediário, 3=Alto impacto)
            nivel_saude = 2  # Padrão: Intermediário
            
            if acucar is not None or sodio is not None:
                # Critérios simplificados
                acucar_alto = acucar > 10 if acucar is not None else False
                sodio_alto = sodio > 400 if sodio is not None else False
                
                if acucar_alto or sodio_alto:
                    nivel_saude = 3  # Alto impacto
                    
            if fibras is not None or vitamina_c is not None or calcio is not None:
                # Critérios simplificados para alimentos saudáveis
                fibra_boa = fibras > 3 if fibras is not None else False
                vitamina_c_boa = vitamina_c > 15 if vitamina_c is not None else False
                calcio_bom = calcio > 100 if calcio is not None else False
                
                if fibra_boa or vitamina_c_boa or calcio_bom:
                    nivel_saude = 1  # Saudável
            
            # Atualizar no banco
            with self.lock:
                self.cursor.execute("""
                    UPDATE itens SET
                        nome = ?, quantidade = ?, unidade = ?, localizacao = ?, categoria = ?,
                        perecivel = ?, validade = ?, valor_compra = ?, local_compra = ?,
                        calorias_100g = ?, proteinas_g = ?, carboidratos_g = ?, gorduras_g = ?,
                        fibras_g = ?, calcio_mg = ?, ferro_mg = ?, vitamina_a_mcg = ?,
                        vitamina_c_mg = ?, vitamina_d_mcg = ?, acucar_100g = ?, sodio_100g = ?,
                        ingredientes = ?, saudavel = ?, nivel_saude = ?,
                        para_thomas = ?, contem_leite = ?, compatibilidade_thomas = ?
                    WHERE id = ?
                """, (
                    nome, qtd, unidade, local, categoria,
                    perecivel, validade, valor_compra, local_compra,
                    calorias, proteinas, carboidratos, gorduras,
                    fibras, calcio, ferro, vitamina_a,
                    vitamina_c, vitamina_d, acucar, sodio,
                    ingredientes, 1, nivel_saude,
                    para_thomas, contem_leite, compatibilidade_thomas,
                    item_id
                ))
                
                # Se tiver valor de compra, registrar no histórico
                if valor_compra is not None and valor_compra > 0 and local_compra:
                    data_compra = datetime.date.today()
                    self.cursor.execute("""
                        INSERT INTO historico_precos (item_id, data_compra, valor_unitario, local_compra)
                        VALUES (?, ?, ?, ?)
                    """, (item_id, data_compra, valor_compra, local_compra))
                
                self.conn.commit()
                
            return True, f"Item '{nome}' atualizado com sucesso"
            
        except sqlite3.Error as e:
            return False, f"Erro ao atualizar item: {str(e)}"
            
    def excluir_item(self, item_id):
        """
        Exclui um item do inventário
        
        Returns:
            Tuple (bool, str): Status e mensagem
        """
        try:
            # Validar ID
            if not isinstance(item_id, int) or item_id <= 0:
                return False, "ID do item inválido"
                
            # Verificar se o item existe
            self.cursor.execute("SELECT id, nome FROM itens WHERE id = ?", (item_id,))
            item = self.cursor.fetchone()
            
            if not item:
                return False, f"Item ID {item_id} não encontrado"
                
            nome_item = item[1]
            
            # Excluir o item
            with self.lock:
                # Poderia ser configurado para fazer soft-delete em vez de hard-delete
                self.cursor.execute("DELETE FROM itens WHERE id = ?", (item_id,))
                
                # Limpar histórico relacionados
                self.cursor.execute("DELETE FROM historico_precos WHERE item_id = ?", (item_id,))
                self.cursor.execute("DELETE FROM consumo_thomas WHERE item_id = ?", (item_id,))
                self.cursor.execute("DELETE FROM consumo_geral WHERE item_id = ?", (item_id,))
                
                self.conn.commit()
            
            return True, f"Item '{nome_item}' excluído com sucesso"
                
        except sqlite3.Error as e:
            return False, f"Erro ao excluir item: {str(e)}"