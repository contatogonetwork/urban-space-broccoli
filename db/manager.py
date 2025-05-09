import sqlite3
import pandas as pd
import datetime
import os
import threading
import re
from utils.constants import TERMOS_LACTEOS

class DatabaseManager:
    """Gerencia todas as operações do banco de dados"""
    
    def __init__(self, db_path: str = "geladeira.db"):
        """Inicializa conexão com o banco de dados"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.lock = threading.Lock()  # Para operações thread-safe
        self._setup_database()
    
    def _setup_database(self):
        """Configura as tabelas necessárias e migra dados se necessário"""
        # Verifica se a tabela já existe
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='itens'")
        table_exists = self.cursor.fetchone()
        
        if not table_exists:
            # Criar tabela com nova estrutura
            success, msg = self._create_new_tables()
            return success, msg
        else:
            # Verificar e adicionar colunas faltantes
            return self._migrate_database()
    
    def _create_new_tables(self):
        """Cria as tabelas do zero com estrutura completa"""
        try:
            # Tabela principal de itens
            self.cursor.execute("""
            CREATE TABLE itens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                quantidade REAL NOT NULL,
                unidade TEXT NOT NULL DEFAULT 'unidade',
                localizacao TEXT NOT NULL,
                categoria TEXT NOT NULL DEFAULT 'Outros',
                perecivel INTEGER NOT NULL,
                validade DATE,
                data_cadastro DATE DEFAULT CURRENT_DATE,
                valor_compra REAL,
                local_compra TEXT,
                calorias_100g REAL,  -- Alterado para padronizar
                proteinas_g REAL,  -- Alterado para padronizar
                carboidratos_g REAL,  -- Alterado para padronizar
                gorduras_g REAL,  -- Alterado para padronizar
                fibras_g REAL,
                calcio_mg REAL,
                ferro_mg REAL,
                vitamina_a_mcg REAL,
                vitamina_c_mg REAL,
                vitamina_d_mcg REAL,
                acucar_100g REAL,
                sodio_100g REAL,
                ingredientes TEXT,
                saudavel INTEGER DEFAULT 1,
                para_thomas INTEGER DEFAULT 0,
                contem_leite INTEGER DEFAULT 0,
                compatibilidade_thomas INTEGER DEFAULT 0,
                nivel_saude INTEGER DEFAULT 2  -- Adicionado
            )
            """)
            
            # Tabela para histórico de preços
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS historico_precos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                data_compra DATE NOT NULL,
                valor_unitario REAL NOT NULL,
                local_compra TEXT,
                FOREIGN KEY (item_id) REFERENCES itens(id)
            )
            """)
            
            # Tabela para consumo de Thomas
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS consumo_thomas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                data_consumo DATE DEFAULT CURRENT_DATE,
                quantidade_consumida REAL NOT NULL,
                FOREIGN KEY (item_id) REFERENCES itens(id)
            )
            """)
            
            # Tabela para consumo geral
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS consumo_geral (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                data_consumo DATE DEFAULT CURRENT_DATE,
                quantidade_consumida REAL NOT NULL,
                FOREIGN KEY (item_id) REFERENCES itens(id)
            )
            """)
            
            # Tabela para restrições alimentares de Thomas
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS restricoes_thomas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,  -- 'Alergia' ou 'Intolerância'
                substancia TEXT NOT NULL,
                nivel_gravidade INTEGER NOT NULL DEFAULT 1,  -- 1 a 5
                sintomas TEXT,
                substituicoes TEXT,
                ativo INTEGER DEFAULT 1
            )
            """)
            
            # Tabela para necessidades nutricionais de Thomas
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS necessidades_thomas (
                nutriente TEXT PRIMARY KEY,
                quantidade_diaria REAL NOT NULL
            )
            """)
            
            # Tabela de consumo de nutrientes
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS consumo_nutrientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                nome_item TEXT,
                data_consumo DATE NOT NULL,
                para_thomas INTEGER NOT NULL,
                nutriente TEXT NOT NULL,
                valor REAL NOT NULL
            )
            """)
            
            # Tabela de alertas nutricionais
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS alertas_nutricionais (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nutriente TEXT NOT NULL,
                percentual REAL,
                para_thomas INTEGER NOT NULL,
                data_alerta DATE DEFAULT CURRENT_DATE
            )
            """)
            
            self.conn.commit()
            
            # Inicializar restrições padrão
            self._inicializar_restricoes_thomas()
            
            # Inicializar necessidades nutricionais padrão
            self._inicializar_necessidades_thomas()
            
            return True, "Banco de dados criado com sucesso!"
        except sqlite3.Error as e:
            return False, f"Erro ao criar banco de dados: {e}"
    
    def _inicializar_restricoes_thomas(self):
        """Inicializa restrições alimentares padrão para Thomas"""
        restricoes_default = [
            ('Intolerância', 'Lactose', 4, 'Dor abdominal, Gases, Diarreia', 'Leite vegetal, Queijos veganos'),
            ('Alergia', 'Corante Amarelo', 3, 'Urticária, Coceira', 'Alimentos sem corantes artificiais')
        ]
        
        try:
            for restricao in restricoes_default:
                self.cursor.execute("""
                INSERT INTO restricoes_thomas (tipo, substancia, nivel_gravidade, sintomas, substituicoes)
                VALUES (?, ?, ?, ?, ?)
                """, restricao)
            
            self.conn.commit()
            return True, "Restrições padrão inicializadas com sucesso"
        except sqlite3.Error as e:
            return False, f"Erro ao inicializar restrições padrão: {e}"
    
    def _inicializar_necessidades_thomas(self):
        """Inicializa necessidades nutricionais padrão para Thomas"""
        necessidades_default = [
            ('Cálcio', 1000),
            ('Proteínas', 30),
            ('Vitamina D', 15),
            ('Ferro', 10),
            ('Vitamina C', 45)
        ]
        
        try:
            for necessidade in necessidades_default:
                self.cursor.execute("""
                INSERT INTO necessidades_thomas (nutriente, quantidade_diaria)
                VALUES (?, ?)
                """, necessidade)
            
            self.conn.commit()
            return True, "Necessidades nutricionais padrão inicializadas com sucesso"
        except sqlite3.Error as e:
            return False, f"Erro ao inicializar necessidades nutricionais padrão: {e}"
    
    def _migrate_database(self):
        """Migra o banco de dados, adicionando colunas faltantes"""
        try:
            # Obter lista de colunas atuais
            self.cursor.execute("PRAGMA table_info(itens)")
            columns = {col[1]: col[2] for col in self.cursor.fetchall()}
            
            # Lista de colunas necessárias com seus tipos e valores padrão
            needed_columns = {
                "nome": ("TEXT", None),
                "quantidade": ("REAL", None),
                "unidade": ("TEXT", "'unidade'"),
                "localizacao": ("TEXT", None),
                "categoria": ("TEXT", "'Outros'"),
                "perecivel": ("INTEGER", None),
                "validade": ("DATE", None),
                "data_cadastro": ("DATE", "CURRENT_DATE"),
                "valor_compra": ("REAL", None),
                "local_compra": ("TEXT", None),
                "calorias_100g": ("REAL", None),
                "proteinas_g": ("REAL", "0"),
                "carboidratos_g": ("REAL", "0"),
                "gorduras_g": ("REAL", "0"),
                "fibras_g": ("REAL", "0"),
                "calcio_mg": ("REAL", "0"),
                "ferro_mg": ("REAL", "0"),
                "vitamina_a_mcg": ("REAL", "0"),
                "vitamina_c_mg": ("REAL", "0"),
                "vitamina_d_mcg": ("REAL", "0"),
                "acucar_100g": ("REAL", None),
                "sodio_100g": ("REAL", None),
                "ingredientes": ("TEXT", "NULL"),
                "saudavel": ("INTEGER", "1"),
                "para_thomas": ("INTEGER", "0"),
                "contem_leite": ("INTEGER", "0"),
                "compatibilidade_thomas": ("INTEGER", "0")
            }
            
            # Verificar quantas colunas estão faltando
            missing_cols = [col for col in needed_columns if col not in columns]
            
            # Se muitas colunas faltantes, usar shadow table (mais eficiente)
            if len(missing_cols) > 5:
                with self.lock:
                    # Criar tabela temporária com estrutura completa
                    col_defs = []
                    for col_name, (col_type, default) in needed_columns.items():
                        default_clause = f" DEFAULT {default}" if default else ""
                        col_defs.append(f"{col_name} {col_type}{default_clause}")
                    
                    # Criar a tabela com estrutura completa
                    self.cursor.execute(f"""
                    CREATE TABLE itens_new (
                        id INTEGER PRIMARY KEY,
                        {', '.join(col_defs)}
                    )
                    """)
                    
                    # Colunas existentes para a inserção
                    existing_cols = [col for col in columns]
                    
                    # Colunas para inserção na nova tabela (existentes + NULL para as novas)
                    new_cols = existing_cols + [f"NULL AS {col}" for col in missing_cols]
                    
                    # Copiar dados
                    self.cursor.execute(f"""
                    INSERT INTO itens_new (id, {', '.join(existing_cols)})
                    SELECT id, {', '.join(existing_cols)} FROM itens
                    """)
                    
                    # Substituir tabelas
                    self.cursor.execute("DROP TABLE itens")
                    self.cursor.execute("ALTER TABLE itens_new RENAME TO itens")
                    
                    # Atualizar valores padrão para campos específicos
                    self.cursor.execute("UPDATE itens SET unidade = 'unidade' WHERE unidade IS NULL")
                    self.cursor.execute("UPDATE itens SET categoria = 'Outros' WHERE categoria IS NULL")
                    
                    self.conn.commit()
                    
                    messages = ["Migração de tabela realizada com sucesso usando shadow table"]
            else:
                # Adicionar colunas individualmente (para poucas colunas)
                messages = []
                with self.lock:
                    for col_name, (col_type, default) in needed_columns.items():
                        if col_name not in columns:
                            default_clause = f" DEFAULT {default}" if default else ""
                            try:
                                self.cursor.execute(f"ALTER TABLE itens ADD COLUMN {col_name} {col_type}{default_clause}")
                                messages.append(f"Coluna {col_name} adicionada à tabela 'itens'")
                            except sqlite3.Error as e:
                                return False, f"Erro ao adicionar coluna {col_name}: {e}"
                    
                    # Atualizar valores padrão para campos específicos
                    self.cursor.execute("UPDATE itens SET unidade = 'unidade' WHERE unidade IS NULL")
                    self.cursor.execute("UPDATE itens SET categoria = 'Outros' WHERE categoria IS NULL")
                    
                    self.conn.commit()
            
            # Verificar e criar outras tabelas necessárias
            tables_to_check = [
                ("historico_precos", """
                CREATE TABLE historico_precos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL,
                    data_compra DATE NOT NULL,
                    valor_unitario REAL NOT NULL,
                    local_compra TEXT,
                    FOREIGN KEY (item_id) REFERENCES itens(id)
                )
                """),
                ("consumo_thomas", """
                CREATE TABLE consumo_thomas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL,
                    data_consumo DATE DEFAULT CURRENT_DATE,
                    quantidade_consumida REAL NOT NULL,
                    FOREIGN KEY (item_id) REFERENCES itens(id)
                )
                """),
                ("consumo_geral", """
                CREATE TABLE consumo_geral (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL,
                    data_consumo DATE DEFAULT CURRENT_DATE,
                    quantidade_consumida REAL NOT NULL,
                    FOREIGN KEY (item_id) REFERENCES itens(id)
                )
                """),
                ("restricoes_thomas", """
                CREATE TABLE restricoes_thomas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo TEXT NOT NULL,
                    substancia TEXT NOT NULL,
                    nivel_gravidade INTEGER NOT NULL DEFAULT 1,
                    sintomas TEXT,
                    substituicoes TEXT,
                    ativo INTEGER DEFAULT 1
                )
                """),
                ("necessidades_thomas", """
                CREATE TABLE necessidades_thomas (
                    nutriente TEXT PRIMARY KEY,
                    quantidade_diaria REAL NOT NULL
                )
                """),
                ("consumo_nutrientes", """
                CREATE TABLE consumo_nutrientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL,
                    nome_item TEXT,
                    data_consumo DATE NOT NULL,
                    para_thomas INTEGER NOT NULL,
                    nutriente TEXT NOT NULL,
                    valor REAL NOT NULL
                )
                """),
                ("alertas_nutricionais", """
                CREATE TABLE alertas_nutricionais (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nutriente TEXT NOT NULL,
                    percentual REAL,
                    para_thomas INTEGER NOT NULL,
                    data_alerta DATE DEFAULT CURRENT_DATE
                )
                """)
            ]
            
            for table_name, create_sql in tables_to_check:
                self.cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
                if not self.cursor.fetchone():
                    with self.lock:
                        self.cursor.execute(create_sql)
                        self.conn.commit()
                        messages.append(f"Tabela '{table_name}' criada")
                        
                        # Inicializar dados padrão para novas tabelas
                        if table_name == "restricoes_thomas":
                            self._inicializar_restricoes_thomas()
                        elif table_name == "necessidades_thomas":
                            self._inicializar_necessidades_thomas()
            
            return True, "\n".join(messages)
        except sqlite3.Error as e:
            return False, f"Erro durante migração do banco: {e}"
    
    def _registrar_consumo_nutrientes(self, item_id, nome_item, data, para_thomas, nutrientes):
        if not isinstance(item_id, int) or item_id <= 0:
            return False
        if not nome_item or not isinstance(nome_item, str):
            return False
        if not isinstance(data, (datetime.date, str)):
            return False
        if not isinstance(para_thomas, (bool, int)):
            return False
        if not isinstance(nutrientes, dict) or not nutrientes:
            return False
        try:
            with self.lock:
                for nutr, val in nutrientes.items():
                    if not isinstance(val, (int, float)) or val < 0:
                        continue
                    self.cursor.execute(
                        "INSERT INTO consumo_nutrientes (item_id, nome_item, data_consumo, para_thomas, nutriente, valor) VALUES (?, ?, ?, ?, ?, ?)",
                        (item_id, nome_item, data, int(para_thomas), nutr, val)
                    )
                self.conn.commit()
            return True
        except Exception:
            return False

    def obter_nutrientes_consumidos(self, apenas_thomas=False, periodo_dias=7):
        try:
            query = "SELECT data_consumo, nutriente, SUM(valor) as total FROM consumo_nutrientes"
            params = []
            if apenas_thomas:
                query += " WHERE para_thomas = 1"
            if periodo_dias:
                clause = "AND" if "WHERE" in query else " WHERE"
                query += f" {clause} data_consumo >= date('now', ?)"
                params.append(f'-{periodo_dias} days')
            query += " GROUP BY data_consumo, nutriente"
            rows = self.cursor.execute(query, params).fetchall()
            if not rows:
                return pd.DataFrame()
            df = pd.DataFrame(rows, columns=["Data", "Nutriente", "Total"])
            return df
        except Exception:
            return pd.DataFrame()

    def criar_alerta_nutricional(self, nutriente, percentual, para_thomas=False):
        if not nutriente or not isinstance(nutriente, str):
            return False
        if not isinstance(percentual, (int, float)):
            return False
        try:
            with self.lock:
                self.cursor.execute(
                    "INSERT INTO alertas_nutricionais (nutriente, percentual, para_thomas) VALUES (?, ?, ?)",
                    (nutriente, percentual, int(para_thomas))
                )
                self.conn.commit()
            return True
        except Exception:
            return False

    def obter_necessidades_thomas(self):
        try:
            rows = self.cursor.execute(
                "SELECT nutriente, quantidade_diaria FROM necessidades_thomas"
            ).fetchall()
            return [{"nutriente": r[0], "quantidade_diaria": r[1]} for r in rows]
        except Exception:
            return []