import sqlite3
import logging
import pandas as pd
import os
import datetime
import shutil
from contextlib import contextmanager
from typing import Tuple, List, Dict, Any, Optional, Generator
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)

class ExtendedDatabaseManager:
    """
    Gerenciador estendido do banco de dados para o Sistema GELADEIRA.
    
    Esta classe implementa todas as operações necessárias para acesso e manipulação
    dos dados do inventário, consumos, e configurações do sistema.
    """
    def __init__(self, db_path):
        """
        Inicializa o gerenciador de banco de dados.
        
        Args:
            db_path (str): Caminho para o arquivo de banco de dados SQLite.
        """
        self.db_path = db_path
        self.lock = Lock()
        self.conn = None
        self.cursor = None
        try:
            # Garante que o diretório do banco de dados existe
            if db_path != ":memory:":
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            self.conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30.0)
            # Habilitar suporte a chaves estrangeiras
            self.conn.execute("PRAGMA foreign_keys = ON")
            # Habilitar o uso de dicionários nos resultados
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            
            # Inicializar banco se não existir
            self.inicializar_banco()
            
        except sqlite3.Error as e:
            logger.error(f"Erro ao conectar ao banco de dados: {str(e)}")
            if self.conn:
                self.conn.close()
            self.conn = None
            self.cursor = None

    def __enter__(self):
        """Suporte para uso de context manager (with statement)."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Fecha a conexão ao sair do bloco with."""
        self.fechar()
        return False  # Permite que exceções sejam propagadas

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Cursor, None, None]:
        """
        Context manager para gerenciar transações no banco de dados.
        
        Yields:
            sqlite3.Cursor: O cursor para executar operações dentro da transação.
        """
        if not self.conn:
            raise sqlite3.Error("Conexão com o banco de dados não está ativa.")
            
        try:
            with self.lock:
                yield self.cursor
                self.conn.commit()
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            logger.error(f"Erro durante a transação: {str(e)}")
            raise
            
    def verificar_integridade(self) -> Tuple[bool, str]:
        """
        Verifica a integridade do banco de dados.

        Returns:
            tuple: (sucesso, mensagem)
        """
        if not self.conn:
            return False, "Conexão com o banco de dados não está ativa."

        try:
            # Verificação de integridade usando PRAGMA
            self.cursor.execute("PRAGMA integrity_check;")
            resultado = self.cursor.fetchone()
            
            if resultado and resultado[0].lower() == "ok":
                return True, "Banco de dados íntegro"
            return False, f"Problemas de integridade detectados: {resultado[0] if resultado else 'desconhecido'}"
        except sqlite3.DatabaseError as db_err:
            return False, f"Erro de banco de dados ao verificar integridade: {str(db_err)}"
        except Exception as e:
            logger.exception("Erro ao verificar integridade do banco")
            return False, f"Erro inesperado ao verificar integridade: {str(e)}"
            
    def inicializar_banco(self) -> Tuple[bool, str]:
        """
        Inicializa a estrutura básica do banco de dados.
        
        Returns:
            tuple: (sucesso, mensagem)
        """
        try:
            # Criar tabelas básicas
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS itens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                quantidade REAL NOT NULL,
                unidade TEXT NOT NULL DEFAULT 'unidade',
                localizacao TEXT NOT NULL,
                categoria TEXT NOT NULL DEFAULT 'Outros',
                perecivel INTEGER NOT NULL DEFAULT 0,
                validade DATE,
                data_cadastro DATE DEFAULT CURRENT_DATE,
                para_thomas INTEGER NOT NULL DEFAULT 0,
                compatibilidade_thomas INTEGER DEFAULT 2,
                contem_leite INTEGER DEFAULT 0,
                custo_unitario REAL,
                local_compra TEXT,
                nivel_saude INTEGER DEFAULT 2
            )
            """)
            
            # Tabela para informações nutricionais
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS nutricional (
                item_id INTEGER PRIMARY KEY,
                calorias_100g REAL,
                proteinas_g REAL,
                carboidratos_g REAL,
                gorduras_g REAL,
                fibras_g REAL,
                calcio_mg REAL,
                ferro_mg REAL,
                vitamina_a_mcg REAL,
                vitamina_c_mg REAL,
                vitamina_d_mcg REAL,
                acucar_100g REAL,
                sodio_100g REAL,
                peso_por_unidade REAL DEFAULT NULL,  -- Nova coluna para resolver problema nutricional
                FOREIGN KEY (item_id) REFERENCES itens(id)
            )
            """)
            
            # Tabela para registro de consumo
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS consumo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                quantidade REAL NOT NULL,
                data_consumo DATE DEFAULT CURRENT_DATE,
                para_thomas INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (item_id) REFERENCES itens(id)
            )
            """)
            
            # Tabela para configurações
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS configuracoes (
                chave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            )
            """)
            
            # Tabela para configurações de alertas
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS config_alertas (
                chave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            )
            """)
            
            # Tabela para restrições alimentares
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS restricoes_thomas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                substancia TEXT NOT NULL,
                nivel_gravidade INTEGER DEFAULT 1,
                sintomas TEXT,
                substituicoes TEXT,
                ativo INTEGER DEFAULT 1
            )
            """)
            
            # Tabela para necessidades nutricionais
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS necessidades_thomas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nutriente TEXT NOT NULL,
                quantidade_diaria REAL NOT NULL,
                unidade TEXT NOT NULL,
                idade_meses INTEGER,
                peso_kg REAL
            )
            """)
            
            # Tabela para registro de consumo de nutrientes
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS consumo_nutrientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                nome_item TEXT NOT NULL,
                data_consumo DATE DEFAULT CURRENT_DATE,
                para_thomas INTEGER NOT NULL DEFAULT 0,
                nutriente TEXT NOT NULL,
                valor REAL NOT NULL,
                FOREIGN KEY (item_id) REFERENCES itens(id)
            )
            """)
            
            # Tabela para histórico de preços
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS historico_precos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                valor_unitario REAL NOT NULL,
                data_compra DATE DEFAULT CURRENT_DATE,
                local_compra TEXT,
                quantidade_comprada REAL,
                FOREIGN KEY (item_id) REFERENCES itens(id)
            )
            """)
            
            # Criar alias para compatibilidade com testes
            self.cursor.execute("""
            CREATE VIEW IF NOT EXISTS inventario AS
            SELECT * FROM itens
            """)
            
            # Criar alias para categorias (para compatibilidade)
            self.cursor.execute("""
            CREATE VIEW IF NOT EXISTS categorias AS
            SELECT DISTINCT categoria FROM itens
            """)
            
            # Criação de índices para performance
            self._criar_indices()
            
            self.conn.commit()
            return True, "Banco de dados inicializado com sucesso"
        except sqlite3.Error as e:
            logger.error(f"Erro ao inicializar banco de dados: {str(e)}")
            return False, f"Erro ao inicializar banco de dados: {str(e)}"

    def _criar_indices(self):
        """Cria os índices necessários para melhorar a performance do banco de dados."""
        try:
            # Índices para tabela itens
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_itens_nome ON itens (nome)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_itens_validade ON itens (validade)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_itens_categoria ON itens (categoria)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_itens_localizacao ON itens (localizacao)")
            
            # Índices para tabela consumo
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_consumo_item_id ON consumo (item_id)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_consumo_data ON consumo (data_consumo)")
            
            # Índices para tabela nutricional
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_nutricional_item_id ON nutricional (item_id)")
            
            # Índices para tabela historico_precos
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_historico_precos_item_id ON historico_precos (item_id)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_historico_precos_data ON historico_precos (data_compra)")
            
            logger.info("Índices criados com sucesso.")
        except sqlite3.Error as e:
            logger.error(f"Erro ao criar índices: {str(e)}")

    def adicionar_item(self, nome: str, categoria: str, quantidade: float, unidade: str, validade: Optional[datetime.date], localizacao: str, custo_unitario: float = 0.0, para_thomas: bool = False, contem_leite: bool = False) -> int:
        """
        Adiciona um item ao inventário.

        Args:
            nome (str): Nome do item.
            categoria (str): Categoria do item.
            quantidade (float): Quantidade do item.
            unidade (str): Unidade de medida.
            validade (Optional[datetime.date]): Data de validade.
            localizacao (str): Localização do item.
            custo_unitario (float): Custo unitário do item.
            para_thomas (bool): Indica se o item é seguro para Thomás.
            contem_leite (bool): Indica se o item contém leite.

        Returns:
            int: ID do item adicionado.
        """
        # Validação de dados
        if not nome or not nome.strip():
            raise ValueError("O nome do item não pode estar vazio")
        
        if quantidade < 0:
            raise ValueError("A quantidade não pode ser negativa")
            
        try:
            with self.transaction() as cursor:
                cursor.execute(
                    """
                    INSERT INTO itens (nome, categoria, quantidade, unidade, validade, localizacao, custo_unitario, para_thomas, contem_leite)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (nome, categoria, quantidade, unidade, validade, localizacao, custo_unitario, para_thomas, contem_leite)
                )
                return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Erro ao adicionar item '{nome}': {str(e)}")
            raise

    def carregar_inventario(self) -> pd.DataFrame:
        """
        Carrega todos os itens do inventário.

        Returns:
            pd.DataFrame: DataFrame contendo os itens do inventário.
        """
        if not self.conn:
            logger.error("Conexão com o banco de dados não está ativa.")
            return pd.DataFrame()
            
        query = "SELECT * FROM itens"
        return pd.read_sql_query(query, self.conn)

    def buscar_itens(self, termo_busca: str) -> List[Dict[str, Any]]:
        """
        Busca itens no inventário por nome.

        Args:
            termo_busca (str): O termo para buscar no nome dos itens.

        Returns:
            List[Dict[str, Any]]: Uma lista de dicionários, onde cada dicionário representa um item.
        """
        if not termo_busca or not termo_busca.strip():
            return []
            
        try:
            query = "SELECT id, nome, quantidade, unidade FROM itens WHERE nome LIKE ?"
            self.cursor.execute(query, (f"%{termo_busca}%",))
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Erro ao buscar itens: {str(e)}")
            return []

    def obter_itens_proximos_vencimento(self, dias: int) -> List[Dict[str, Any]]:
        """
        Obtém itens que estão próximos da data de vencimento.

        Args:
            dias (int): Número de dias para considerar como "próximo do vencimento".

        Returns:
            List[Dict[str, Any]]: Lista de itens próximos do vencimento, incluindo 'dias_ate_vencer'.
        """
        if dias < 0:
            logger.warning(f"Valor negativo para dias ({dias}) foi fornecido. Usando valor absoluto.")
            dias = abs(dias)
            
        try:
            query = """
            SELECT 
                id, nome, quantidade, unidade, validade, localizacao,
                CAST(julianday(validade) - julianday('now') AS INTEGER) as dias_ate_vencer
            FROM itens
            WHERE validade IS NOT NULL 
              AND validade >= DATE('now')
              AND validade <= DATE('now', '+' || ? || ' days')
              AND quantidade > 0
            ORDER BY validade ASC
            """
            self.cursor.execute(query, (dias,))
            itens = [dict(row) for row in self.cursor.fetchall()]
            
            # Adicionar itens já vencidos (dias_ate_vencer <= 0)
            query_vencidos = """
            SELECT
                id, nome, quantidade, unidade, validade, localizacao,
                CAST(julianday(validade) - julianday('now') AS INTEGER) as dias_ate_vencer
            FROM itens
            WHERE validade IS NOT NULL
              AND validade < DATE('now')
              AND quantidade > 0
            ORDER BY validade ASC
            """
            self.cursor.execute(query_vencidos)
            itens_vencidos = [dict(row) for row in self.cursor.fetchall()]
            
            # Combinar e remover duplicatas se houver
            todos_os_itens = {item['id']: item for item in itens_vencidos + itens}
            
            return list(todos_os_itens.values())

        except sqlite3.Error as e:
            logger.error(f"Erro ao obter itens próximos do vencimento: {str(e)}")
            return []

    def registrar_consumo(self, item_id: int, quantidade: float, para_thomas: bool = False, data: Optional[datetime.date] = None) -> Tuple[bool, str]:
        """
        Registra o consumo de um item no banco de dados, atualizando o inventário
        e inserindo um registro na tabela de consumo.

        Args:
            item_id (int): ID do item consumido.
            quantidade (float): Quantidade consumida.
            para_thomas (bool): Indica se o consumo é para Thomás.
            data (Optional[datetime.date]): Data do consumo. Se None, usa a data atual.

        Returns:
            Tuple[bool, str]: Sucesso e mensagem de status.
        """
        if quantidade <= 0:
            return False, "A quantidade consumida deve ser maior que zero."
            
        logger.debug(f"Tentando registrar consumo: item_id={item_id}, quantidade={quantidade}, para_thomas={para_thomas}, data={data}")
        try:
            with self.transaction() as cursor:
                # Verificar se o item existe
                cursor.execute("SELECT quantidade FROM itens WHERE id = ?", (item_id,))
                result = cursor.fetchone()
                if not result:
                    logger.warning(f"Falha ao registrar consumo: Item ID {item_id} não encontrado.")
                    return False, "Item não encontrado no inventário."

                quantidade_atual = result["quantidade"]
                # Ajusta quantidade consumida se exceder o disponível
                quantidade_consumir = min(quantidade, quantidade_atual)
                
                # Atualizar quantidade na tabela itens
                nova_quantidade = max(0, quantidade_atual - quantidade_consumir)
                cursor.execute("UPDATE itens SET quantidade = ? WHERE id = ?", (nova_quantidade, item_id))
                
                # Inserir registro na tabela consumo
                data_consumo_str = data.strftime('%Y-%m-%d') if data else None
                
                if data_consumo_str:
                    cursor.execute(
                        "INSERT INTO consumo (item_id, quantidade, data_consumo, para_thomas) VALUES (?, ?, ?, ?)",
                        (item_id, quantidade_consumir, data_consumo_str, 1 if para_thomas else 0)
                    )
                else:
                    cursor.execute(
                        "INSERT INTO consumo (item_id, quantidade, para_thomas) VALUES (?, ?, ?)",
                        (item_id, quantidade_consumir, 1 if para_thomas else 0)
                    )
                
                # Registrar aviso se quantidade foi ajustada
                if quantidade_consumir < quantidade:
                    logger.warning(f"Quantidade ajustada de {quantidade} para {quantidade_consumir} ao registrar consumo do item ID {item_id}")
                    return True, f"Consumo registrado parcialmente ({quantidade_consumir} de {quantidade} solicitadas)"
                
                return True, "Consumo registrado com sucesso e inventário atualizado."
            
        except sqlite3.Error as e:
            logger.error(f"Erro de SQLite ao registrar consumo para item_id {item_id}: {str(e)}")
            return False, f"Erro de banco de dados ao registrar consumo: {str(e)}"
        except Exception as e:
            logger.error(f"Erro inesperado ao registrar consumo para item_id {item_id}: {str(e)}", exc_info=True)
            return False, f"Erro inesperado ao registrar consumo: {str(e)}"

    def obter_registros_consumo(self, data_inicio: datetime.date) -> List[Dict[str, Any]]:
        """
        Obtém os registros de consumo a partir de uma data específica.

        Args:
            data_inicio (datetime.date): Data de início para buscar os registros.

        Returns:
            List[Dict[str, Any]]: Lista de dicionários com 'item_id' e 'data_consumo'.
        """
        try:
            query = "SELECT item_id, data_consumo FROM consumo WHERE data_consumo >= ?"
            self.cursor.execute(query, (data_inicio,))
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Erro ao obter registros de consumo: {str(e)}")
            return []

    def buscar_item_por_id(self, item_id: int) -> Optional[Dict[str, Any]]:
        """
        Busca um item específico pelo seu ID.

        Args:
            item_id (int): ID do item a ser buscado.

        Returns:
            Optional[Dict[str, Any]]: Dicionário com os detalhes do item ou None se não encontrado.
        """
        try:
            query = "SELECT * FROM itens WHERE id = ?"
            self.cursor.execute(query, (item_id,))
            row = self.cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Erro ao buscar item por ID {item_id}: {str(e)}")
            return None

    def obter_itens_vencidos_no_inventario(self) -> List[Dict[str, Any]]:
        """
        Obtém todos os itens do inventário que estão vencidos e com quantidade > 0.

        Returns:
            List[Dict[str, Any]]: Lista de dicionários, onde cada dicionário representa um item vencido.
        """
        try:
            query = """
            SELECT id, nome, quantidade, unidade, validade, localizacao
            FROM itens
            WHERE validade IS NOT NULL
              AND validade < DATE('now')
              AND quantidade > 0
            ORDER BY validade ASC
            """
            self.cursor.execute(query)
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Erro ao obter itens vencidos no inventário: {str(e)}")
            return []

    def obter_nutrientes_consumidos_dict(self, dias: int = 7) -> Dict[str, float]:
        """
        Calcula e retorna a soma dos nutrientes consumidos nos últimos X dias (formato dicionário).
        
        Esta função mantida por compatibilidade. Para novos usos, prefira obter_nutrientes_consumidos()
        que retorna um DataFrame mais completo.

        Args:
            dias (int): Número de dias anteriores a considerar para o cálculo. Default é 7.

        Returns:
            Dict[str, float]: Dicionário com a soma de cada nutriente.
        """
        logger.info(f"Iniciando cálculo de nutrientes consumidos nos últimos {dias} dias (formato dicionário).")
        # Manter a implementação atual do método obter_nutrientes_consumidos
        # ... existing code ...
        
    def obter_nutrientes_consumidos(self, apenas_thomas: bool = False, periodo_dias: int = 7) -> pd.DataFrame:
        """
        Obtém os nutrientes consumidos em um período específico.
        
        Versão principal que retorna um DataFrame pandas para maior flexibilidade.
        Para compatibilidade com código antigo, use obter_nutrientes_consumidos_dict().

        Args:
            apenas_thomas (bool): Se True, considera apenas consumos de Thomas.
            periodo_dias (int): Número de dias para considerar.

        Returns:
            pd.DataFrame: DataFrame contendo os nutrientes consumidos.
        """
        if not self.conn:
            logger.error("Conexão com o banco de dados não está ativa.")
            return pd.DataFrame()
            
        try:
            # Calcular data de início
            data_inicio = datetime.date.today() - datetime.timedelta(days=periodo_dias)
            data_inicio_str = data_inicio.strftime('%Y-%m-%d')
            
            # Query para buscar consumos com dados nutricionais
            query = """
            SELECT 
                c.item_id,
                i.nome,
                c.quantidade AS quantidade_consumida,
                c.data_consumo,
                i.unidade,
                n.calorias_100g,
                n.proteinas_g,
                n.carboidratos_g,
                n.gorduras_g,
                n.fibras_g,
                n.calcio_mg,
                n.ferro_mg,
                n.vitamina_a_mcg,
                n.vitamina_c_mg,
                n.vitamina_d_mcg,
                n.acucar_100g,
                n.sodio_100g,
                n.peso_por_unidade
            FROM consumo c
            JOIN itens i ON c.item_id = i.id
            LEFT JOIN nutricional n ON c.item_id = n.item_id
            WHERE c.data_consumo >= ?
            """
            
            # Adicionar filtro para Thomas se necessário
            if apenas_thomas:
                query += " AND c.para_thomas = 1"
                
            # Executar query
            df = pd.read_sql_query(query, self.conn, params=(data_inicio_str,))
            
            if df.empty:
                return pd.DataFrame()
                
            # Preparar DataFrame para cálculos nutricionais
            df_resultado = pd.DataFrame()
            df_resultado['Nome'] = df['nome']
            df_resultado['Data'] = pd.to_datetime(df['data_consumo'])
            df_resultado['Quantidade'] = df['quantidade_consumida']
            
            # Calcular nutrientes com base nas regras de unidade
            for row_idx, row in df.iterrows():
                quantidade = row['quantidade_consumida']
                unidade = str(row['unidade']).lower() if row['unidade'] is not None else ''
                peso_por_unidade = row['peso_por_unidade']
                
                # Determinar o fator multiplicador
                fator = 0.0
                
                # Caso 1: Se há peso_por_unidade definido e unidade é 'unidade'
                if unidade in ['unidade', 'unidades', 'unid', 'und', 'un', ''] and peso_por_unidade:
                    fator = (quantidade * peso_por_unidade) / 100.0
                # Caso 2: Se a unidade já é peso/volume
                elif unidade in ['g', 'gramas', 'gr', 'grama', 'ml', 'mililitros', 'mililitro']:
                    fator = quantidade / 100.0
                # Caso 3: Se é unidade mas não temos peso_por_unidade
                elif unidade in ['unidade', 'unidades', 'unid', 'und', 'un', '']:
                    fator = quantidade
                
                # Calcular valores nutricionais
                colunas = {
                    'calorias_100g': 'Calorias (kcal)',
                    'proteinas_g': 'Proteínas (g)',
                    'carboidratos_g': 'Carboidratos (g)',
                    'gorduras_g': 'Gorduras (g)',
                    'fibras_g': 'Fibras (g)',
                    'calcio_mg': 'Cálcio (mg)',
                    'ferro_mg': 'Ferro (mg)',
                    'vitamina_a_mcg': 'Vitamina A (mcg)',
                    'vitamina_c_mg': 'Vitamina C (mg)',
                    'vitamina_d_mcg': 'Vitamina D (mcg)',
                    'acucar_100g': 'Açúcar (g)',
                    'sodio_100g': 'Sódio (g)'
                }
                
                for col_db, col_res in colunas.items():
                    if col_db in row and pd.notna(row[col_db]):
                        if col_res not in df_resultado.columns:
                            df_resultado[col_res] = 0.0
                        df_resultado.loc[row_idx, col_res] = float(row[col_db]) * fator
            
            return df_resultado
            
        except sqlite3.Error as e:
            logger.error(f"Erro de SQLite ao obter nutrientes consumidos: {str(e)}")
            return pd.DataFrame()
        except Exception as e:
            logger.exception("Erro inesperado ao obter nutrientes consumidos:")
            return pd.DataFrame()

    def obter_locais_compra(self) -> List[str]:
        """
        Obtém uma lista de locais de compra distintos da tabela de itens.

        Returns:
            List[str]: Lista de nomes de locais de compra.
        """
        if not self.conn or not self.cursor:
            logger.error("Conexão com o banco de dados não está ativa.")
            return []
        try:
            query = "SELECT DISTINCT local_compra FROM itens WHERE local_compra IS NOT NULL AND local_compra != ''"
            self.cursor.execute(query)
            locais = [row['local_compra'] for row in self.cursor.fetchall()]
            
            # Adicionar locais da tabela historico_precos também
            query_historico = "SELECT DISTINCT local_compra FROM historico_precos WHERE local_compra IS NOT NULL AND local_compra != ''"
            self.cursor.execute(query_historico)
            locais_historico = [row['local_compra'] for row in self.cursor.fetchall()]
            
            # Combinar e remover duplicatas
            todos_locais = sorted(list(set(locais + locais_historico)))
            
            logger.info(f"Locais de compra obtidos: {todos_locais}")
            return todos_locais
        except sqlite3.Error as e:
            logger.error(f"Erro de SQLite ao obter locais de compra: {str(e)}")
            return []
        except Exception as e:
            logger.exception("Erro inesperado ao obter locais de compra:")
            return []

    def criar_backup(self, caminho_backup: str = None) -> Tuple[bool, str]:
        """
        Cria um backup do banco de dados.
        
        Args:
            caminho_backup (str, optional): Caminho onde salvar o backup.
                                           Se None, usa o nome do arquivo original + data/hora.
                                           
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        if not self.conn:
            return False, "Conexão com o banco de dados não está ativa."
            
        if self.db_path == ":memory:":
            return False, "Não é possível fazer backup de banco em memória."
            
        try:
            # Fecha todas as transações e limpa cache
            self.conn.commit()
            
            # Gera nome do arquivo de backup se não fornecido
            if not caminho_backup:
                now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                db_nome = os.path.basename(self.db_path)
                db_dir = os.path.dirname(self.db_path)
                caminho_backup = os.path.join(db_dir, f"{db_nome}.backup_{now}")
                
            # Cria diretórios para o backup se necessário
            os.makedirs(os.path.dirname(os.path.abspath(caminho_backup)), exist_ok=True)
            
            # Copia o arquivo do banco
            shutil.copy2(self.db_path, caminho_backup)
            
            logger.info(f"Backup do banco criado em: {caminho_backup}")
            return True, f"Backup criado com sucesso em: {caminho_backup}"
            
        except Exception as e:
            logger.exception(f"Erro ao criar backup:")
            return False, f"Erro ao criar backup: {str(e)}"

    def obter_historico_precos_por_nome(self, nome_item: str) -> pd.DataFrame:
        """
        Obtém o histórico de preços para um item específico pelo nome.

        Args:
            nome_item (str): Nome do item a ser consultado.

        Returns:
            pd.DataFrame: DataFrame contendo o histórico de preços do item.
        """
        if not self.conn or not self.cursor:
            logger.error("Conexão com o banco de dados não está ativa.")
            return pd.DataFrame()

        try:
            query = """
            SELECT hp.id, hp.item_id, i.nome AS nome_item, hp.valor_unitario, hp.data_compra, 
                   hp.local_compra, hp.quantidade_comprada
            FROM historico_precos hp
            JOIN itens i ON hp.item_id = i.id
            WHERE i.nome LIKE ?
            ORDER BY hp.data_compra DESC, hp.id DESC
            """
            return pd.read_sql_query(query, self.conn, params=(f"%{nome_item}%",))
        except sqlite3.Error as e:
            logger.error(f"Erro ao obter histórico de preços para o item '{nome_item}': {str(e)}")
            return pd.DataFrame()
        except Exception as e:
            logger.exception(f"Erro inesperado ao obter histórico de preços para o item '{nome_item}':")
            return pd.DataFrame()

    def obter_historico_precos_completo(self) -> pd.DataFrame:
        """
        Obtém o histórico de preços completo para todos os itens.

        Returns:
            pd.DataFrame: DataFrame contendo o histórico de preços de todos os itens.
        """
        if not self.conn or not self.cursor:
            logger.error("Conexão com o banco de dados não está ativa.")
            return pd.DataFrame()

        try:
            query = """
            SELECT hp.id, hp.item_id, i.nome AS nome_item, hp.valor_unitario, hp.data_compra, 
                   hp.local_compra, hp.quantidade_comprada
            FROM historico_precos hp
            JOIN itens i ON hp.item_id = i.id
            ORDER BY hp.data_compra DESC, hp.id DESC
            """
            return pd.read_sql_query(query, self.conn)
        except sqlite3.Error as e:
            logger.error(f"Erro ao obter histórico de preços completo: {str(e)}")
            return pd.DataFrame()
        except Exception as e:
            logger.exception("Erro inesperado ao obter histórico de preços completo:")
            return pd.DataFrame()
            
    def calcular_estatisticas_preco(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Calcula estatísticas de preços para todos os itens.

        Returns:
            Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]: 
                - DataFrame com tendências de preço por item
                - DataFrame com histórico de preços detalhado
                - DataFrame com estatísticas por local de compra
        """
        if not self.conn or not self.cursor:
            logger.error("Conexão com o banco de dados não está ativa.")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        try:
            # Obter histórico de preços completo
            historico_df = self.obter_historico_precos_completo()
            
            if historico_df.empty:
                logger.warning("Sem dados de histórico de preços para calcular estatísticas.")
                return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
                
            # Calcular tendências de preço por item
            tendencias = []
            
            # Agrupar por item
            for nome_item, grupo in historico_df.groupby('nome_item'):
                # Ordenar por data
                grupo = grupo.sort_values('data_compra')
                
                # Se houver pelo menos dois registros, calcular tendência
                if len(grupo) >= 2:
                    primeiro_registro = grupo.iloc[0]
                    ultimo_registro = grupo.iloc[-1]
                    
                    preco_inicial = primeiro_registro['valor_unitario']
                    preco_atual = ultimo_registro['valor_unitario']
                    
                    # Evitar divisão por zero
                    if preco_inicial > 0:
                        variacao_percentual = ((preco_atual - preco_inicial) / preco_inicial) * 100
                    else:
                        variacao_percentual = 0
                        
                    # Média de preços de todos os registros
                    preco_medio = grupo['valor_unitario'].mean()
                    
                    # Calcular posição do último preço em relação à média
                    posicao_vs_media = ((preco_atual - preco_medio) / preco_medio) * 100 if preco_medio > 0 else 0
                    
                    # Determinar tendência com base na variação
                    if variacao_percentual > 5:
                        tendencia = "Alta"
                    elif variacao_percentual < -5:
                        tendencia = "Queda"
                    else:
                        tendencia = "Estável"
                        
                    tendencias.append({
                        'ID': ultimo_registro['item_id'],
                        'Nome': nome_item,
                        'Preço Inicial': preco_inicial,
                        'Preço Atual': preco_atual,
                        'Preço Médio': preco_medio,
                        'Variação (%)': variacao_percentual,
                        'Posição vs Média (%)': posicao_vs_media,
                        'Tendência': tendencia
                    })
            
            # Criar DataFrame de tendências
            tendencias_df = pd.DataFrame(tendencias)
            
            # Estatísticas por local de compra
            if not historico_df.empty and 'local_compra' in historico_df.columns:
                estatisticas_local = historico_df.groupby(['nome_item', 'local_compra'])['valor_unitario'].agg(['min', 'max', 'mean']).reset_index()
                estatisticas_local.columns = ['Item', 'Local', 'Menor Preço', 'Maior Preço', 'Preço Médio']
            else:
                estatisticas_local = pd.DataFrame()
            
            return tendencias_df, historico_df, estatisticas_local
            
        except Exception as e:
            logger.exception("Erro ao calcular estatísticas de preço:")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    def obter_sugestoes_compra(self, limite_quantidade: float = 1.0) -> pd.DataFrame:
        """
        Obtém sugestões de itens para compra com base em estoque baixo.

        Args:
            limite_quantidade (float): Quantidade limite para considerar estoque baixo.

        Returns:
            pd.DataFrame: DataFrame com itens sugeridos para compra.
        """
        if not self.conn or not self.cursor:
            logger.error("Conexão com o banco de dados não está ativa.")
            return pd.DataFrame()

        try:
            query = """
            SELECT id, nome, quantidade, unidade, categoria, localizacao
            FROM itens
            WHERE quantidade <= ?
            ORDER BY quantidade ASC
            """
            return pd.read_sql_query(query, self.conn, params=(limite_quantidade,))
        except sqlite3.Error as e:
            logger.error(f"Erro ao obter sugestões de compra: {str(e)}")
            return pd.DataFrame()
        except Exception as e:
            logger.exception("Erro inesperado ao obter sugestões de compra:")
            return pd.DataFrame()

    def obter_melhor_local_compra(self, nome_item: str) -> Optional[Dict[str, Any]]:
        """
        Determina o melhor local para compra de um item específico.

        Args:
            nome_item (str): Nome do item a consultar.

        Returns:
            Optional[Dict[str, Any]]: Dicionário com informações do melhor local, ou None se não houver dados.
        """
        if not self.conn or not self.cursor:
            logger.error("Conexão com o banco de dados não está ativa.")
            return None

        try:
            historico_df = self.obter_historico_precos_por_nome(nome_item)
            
            if historico_df.empty:
                return None
                
            # Agrupar por local de compra e obter o menor preço em cada local
            melhores_precos = historico_df.groupby('local_compra')['valor_unitario'].min().reset_index()
            
            if melhores_precos.empty:
                return None
                
            # Pegar o local com menor preço
            melhor = melhores_precos.loc[melhores_precos['valor_unitario'].idxmin()]
            
            return {
                'local': melhor['local_compra'],
                'preco': melhor['valor_unitario']
            }
            
        except Exception as e:
            logger.exception(f"Erro ao determinar melhor local para '{nome_item}':")
            return None

    def obter_comparativo_precos_mercados(self) -> pd.DataFrame:
        """
        Gera um comparativo de preços entre diferentes mercados.

        Returns:
            pd.DataFrame: DataFrame com comparativo de preços por mercado.
        """
        if not self.conn or not self.cursor:
            logger.error("Conexão com o banco de dados não está ativa.")
            return pd.DataFrame()

        try:
            query = """
            SELECT i.nome AS nome_item, hp.local_compra, AVG(hp.valor_unitario) AS valor_unitario
            FROM historico_precos hp
            JOIN itens i ON hp.item_id = i.id
            WHERE hp.local_compra IS NOT NULL AND hp.local_compra != ''
            GROUP BY i.nome, hp.local_compra
            ORDER BY i.nome, hp.local_compra
            """
            return pd.read_sql_query(query, self.conn)
        except sqlite3.Error as e:
            logger.error(f"Erro ao gerar comparativo de preços: {str(e)}")
            return pd.DataFrame()
        except Exception as e:
            logger.exception("Erro inesperado ao gerar comparativo de preços:")
            return pd.DataFrame()

    def obter_categorias(self) -> List[str]:
        """
        Obtém uma lista de categorias distintas de itens.

        Returns:
            List[str]: Lista de nomes de categorias.
        """
        if not self.conn or not self.cursor:
            logger.error("Conexão com o banco de dados não está ativa.")
            return []
        try:
            self.cursor.execute("SELECT DISTINCT categoria FROM itens WHERE categoria IS NOT NULL AND categoria != '' ORDER BY categoria")
            return [row['categoria'] for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Erro ao obter categorias: {str(e)}")
            return []
        except Exception as e:
            logger.exception("Erro inesperado ao obter categorias:")
            return []

    def carregar_por_categoria(self, categoria: str) -> pd.DataFrame:
        """
        Carrega itens do inventário filtrados por categoria.

        Args:
            categoria (str): Nome da categoria para filtrar.

        Returns:
            pd.DataFrame: DataFrame contendo os itens filtrados.
        """
        if not self.conn or not self.cursor:
            logger.error("Conexão com o banco de dados não está ativa.")
            return pd.DataFrame()

        try:
            query = "SELECT * FROM itens WHERE categoria = ?"
            return pd.read_sql_query(query, self.conn, params=(categoria,))
        except sqlite3.Error as e:
            logger.error(f"Erro ao carregar itens da categoria '{categoria}': {str(e)}")
            return pd.DataFrame()
        except Exception as e:
            logger.exception(f"Erro inesperado ao carregar itens da categoria '{categoria}':")
            return pd.DataFrame()

    def carregar_configuracoes(self) -> Dict[str, Any]:
        """
        Carrega configurações do sistema do banco de dados.

        Returns:
            Dict[str, Any]: Dicionário com as configurações.
        """
        if not self.conn or not self.cursor:
            logger.error("Conexão com o banco de dados não está ativa.")
            return {}

        try:
            self.cursor.execute("SELECT chave, valor FROM configuracoes")
            rows = self.cursor.fetchall()
            
            # Converter para um dicionário
            config = {}
            for row in rows:
                chave = row['chave']
                valor = row['valor']
                
                # Tentar converter tipos comuns
                if valor.lower() == 'true':
                    config[chave] = True
                elif valor.lower() == 'false':
                    config[chave] = False
                elif valor.isdigit():
                    config[chave] = int(valor)
                elif valor.replace('.', '', 1).isdigit() and valor.count('.') < 2:
                    config[chave] = float(valor)
                else:
                    config[chave] = valor
            
            return config
        except sqlite3.Error as e:
            logger.error(f"Erro ao carregar configurações: {str(e)}")
            return {}
        except Exception as e:
            logger.exception("Erro inesperado ao carregar configurações:")
            return {}

    def salvar_configuracoes(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Salva configurações do sistema no banco de dados.

        Args:
            config (Dict[str, Any]): Dicionário com configurações para salvar.

        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        if not self.conn or not self.cursor:
            return False, "Conexão com o banco de dados não está ativa."

        try:
            with self.lock:
                # Converter valores para string para armazenamento
                for chave, valor in config.items():
                    valor_str = str(valor)
                    
                    # Usar INSERT OR REPLACE para adicionar ou atualizar
                    self.cursor.execute(
                        "INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES (?, ?)",
                        (chave, valor_str)
                    )
                
                self.conn.commit()
                return True, "Configurações salvas com sucesso"
        except sqlite3.Error as e:
            logger.error(f"Erro ao salvar configurações: {str(e)}")
            if self.conn:
                try:
                    self.conn.rollback()
                except sqlite3.Error as rb_err:
                    logger.error(f"Erro durante o rollback: {rb_err}")
            return False, f"Erro de banco de dados: {str(e)}"
        except Exception as e:
            logger.exception("Erro inesperado ao salvar configurações:")
            if self.conn:
                try:
                    self.conn.rollback()
                except sqlite3.Error as rb_err:
                    logger.error(f"Erro durante o rollback: {rb_err}")
            return False, f"Erro inesperado: {str(e)}"

    def carregar_configuracoes_alertas(self) -> Dict[str, Any]:
        """
        Carrega configurações de alertas do banco de dados.

        Returns:
            Dict[str, Any]: Dicionário com as configurações de alertas.
        """
        if not self.conn or not self.cursor:
            logger.error("Conexão com o banco de dados não está ativa.")
            return {}

        try:
            self.cursor.execute("SELECT chave, valor FROM config_alertas")
            rows = self.cursor.fetchall()
            
            # Converter para um dicionário
            config = {}
            for row in rows:
                chave = row['chave']
                valor = row['valor']
                
                # Tentar converter tipos comuns
                if valor.lower() == 'true':
                    config[chave] = True
                elif valor.lower() == 'false':
                    config[chave] = False
                elif valor.isdigit():
                    config[chave] = int(valor)
                elif valor.replace('.', '', 1).isdigit() and valor.count('.') < 2:
                    config[chave] = float(valor)
                else:
                    config[chave] = valor
            
            return config
        except sqlite3.Error as e:
            logger.error(f"Erro ao carregar configurações de alertas: {str(e)}")
            return {}
        except Exception as e:
            logger.exception("Erro inesperado ao carregar configurações de alertas:")
            return {}

    def salvar_configuracoes_alertas(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Salva configurações de alertas no banco de dados.

        Args:
            config (Dict[str, Any]): Dicionário com configurações de alertas para salvar.

        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        if not self.conn or not self.cursor:
            return False, "Conexão com o banco de dados não está ativa."

        try:
            with self.lock:
                # Converter valores para string para armazenamento
                for chave, valor in config.items():
                    valor_str = str(valor)
                    
                    # Usar INSERT OR REPLACE para adicionar ou atualizar
                    self.cursor.execute(
                        "INSERT OR REPLACE INTO config_alertas (chave, valor) VALUES (?, ?)",
                        (chave, valor_str)
                    )
                
                self.conn.commit()
                return True, "Configurações de alertas salvas com sucesso"
        except sqlite3.Error as e:
            logger.error(f"Erro ao salvar configurações de alertas: {str(e)}")
            if self.conn:
                try:
                    self.conn.rollback()
                except sqlite3.Error as rb_err:
                    logger.error(f"Erro durante o rollback: {rb_err}")
            return False, f"Erro de banco de dados: {str(e)}"
        except Exception as e:
            logger.exception("Erro inesperado ao salvar configurações de alertas:")
            if self.conn:
                try:
                    self.conn.rollback()
                except sqlite3.Error as rb_err:
                    logger.error(f"Erro durante o rollback: {rb_err}")
            return False, f"Erro inesperado: {str(e)}"

    def criar_alerta_nutricional(self, nutriente: str, percentual: float, para_thomas: bool = False) -> bool:
        """
        Cria um alerta nutricional no sistema.
        
        Args:
            nutriente (str): Nome do nutriente deficiente.
            percentual (float): Percentual da necessidade que está sendo consumido.
            para_thomas (bool): Se o alerta é para Thomas.
            
        Returns:
            bool: True se o alerta foi criado com sucesso.
        """
        try:
            dados_alerta = {
                'tipo': 'nutricional',
                'nutriente': nutriente,
                'percentual': percentual,
                'para_thomas': para_thomas,
                'data': datetime.date.today().isoformat(),
                'lido': False
            }
            
            # Converter para string JSON para armazenar
            import json
            alerta_json = json.dumps(dados_alerta)
            
            with self.lock:
                self.cursor.execute(
                    "INSERT OR REPLACE INTO config_alertas (chave, valor) VALUES (?, ?)",
                    (f"alerta_nutricional_{nutriente}_{datetime.date.today().isoformat()}", alerta_json)
                )
                self.conn.commit()
                
            return True
        except Exception as e:
            logger.exception(f"Erro ao criar alerta nutricional para {nutriente}:")
            return False

    def fechar(self):
        """Fecha a conexão com o banco de dados."""
        if self.conn:
            try:
                self.conn.close()
            except sqlite3.Error as e:
                logger.error(f"Erro ao fechar conexão com o banco: {str(e)}")
            finally:
                self.conn = None
                self.cursor = None