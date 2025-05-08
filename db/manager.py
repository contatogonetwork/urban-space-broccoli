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
                ingredientes TEXT,
                saudavel INTEGER DEFAULT 1,
                para_thomas INTEGER DEFAULT 0,
                contem_leite INTEGER DEFAULT 0,
                compatibilidade_thomas INTEGER DEFAULT 0
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nutriente TEXT NOT NULL,
                quantidade_diaria REAL NOT NULL,
                unidade TEXT NOT NULL,
                prioridade INTEGER DEFAULT 1  -- 1=Baixa, 2=Média, 3=Alta
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
            ('Cálcio', 1000, 'mg', 3),
            ('Proteínas', 30, 'g', 3),
            ('Vitamina D', 15, 'mcg', 3),
            ('Ferro', 10, 'mg', 2),
            ('Vitamina C', 45, 'mg', 2)
        ]
        
        try:
            for necessidade in necessidades_default:
                self.cursor.execute("""
                INSERT INTO necessidades_thomas (nutriente, quantidade_diaria, unidade, prioridade)
                VALUES (?, ?, ?, ?)
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
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nutriente TEXT NOT NULL,
                    quantidade_diaria REAL NOT NULL,
                    unidade TEXT NOT NULL,
                    prioridade INTEGER DEFAULT 1
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
    
    def avaliar_compatibilidade_thomas(self, nome, ingredientes, contem_leite):
        """
        Avalia a compatibilidade do alimento para Thomas
        Retorna: 
        0 = Não recomendado (vermelho)
        1 = Verificar ingredientes (amarelo)
        2 = Seguro (verde)
        """
        # Verificar restrições cadastradas
        restricoes = self.obter_restricoes_thomas()
        
        # Se contém leite já é automaticamente não recomendado
        if contem_leite:
            return 0
        
        if not ingredientes:
            # Verificar pelo nome se não temos os ingredientes
            nome_lower = nome.lower()
            
            # Verificar por termos lácteos no nome
            for termo in TERMOS_LACTEOS:
                if termo in nome_lower:
                    return 0  # Não recomendado
            
            # Verificar outras restrições cadastradas
            for restricao in restricoes:
                substancia = restricao.get('substancia', '').lower()
                if substancia and substancia in nome_lower:
                    return 0  # Não recomendado
                
            return 1  # Verificar (sem info completa)
        else:
            # Temos ingredientes, verificar restrições
            ingredientes_lower = ingredientes.lower()
            
            # Verificar por termos lácteos nos ingredientes
            for termo in TERMOS_LACTEOS:
                if termo in ingredientes_lower:
                    return 0  # Não recomendado
            
            # Verificar outras restrições cadastradas
            for restricao in restricoes:
                substancia = restricao.get('substancia', '').lower()
                if substancia and substancia in ingredientes_lower:
                    return 0  # Não recomendado
            
            return 2  # Seguro (verificamos e não tem restrições)
    
    def adicionar_item(self, nome, qtd, unidade, local, categoria, perecivel, validade=None, 
                       valor_compra=None, local_compra=None, calorias=None, proteinas=None, 
                       carboidratos=None, gorduras=None, fibras=None, calcio=None, ferro=None,
                       vitamina_a=None, vitamina_c=None, vitamina_d=None, acucar=None, 
                       sodio=None, ingredientes=None, para_thomas=False, contem_leite=False):
        """Adiciona um novo item ao inventário"""
        try:
            with self.lock:
                # Calcular nível de saúde (1=Saudável, 2=Intermediário, 3=Alto impacto)
                nivel_saudavel = 1  # padrão saudável
                
                if acucar is not None and acucar > 15:
                    nivel_saudavel = 3
                elif sodio is not None and sodio > 400:
                    nivel_saudavel = 3
                elif acucar is not None and acucar > 5:
                    nivel_saudavel = 2
                elif sodio is not None and sodio > 200:
                    nivel_saudavel = 2
                
                # Avaliar compatibilidade com Thomas
                compatibilidade = self.avaliar_compatibilidade_thomas(nome, ingredientes, contem_leite)
                
                # Inserir item na tabela principal
                self.cursor.execute(
                    """INSERT INTO itens (nome, quantidade, unidade, localizacao, categoria, perecivel, 
                    validade, valor_compra, local_compra, calorias_100g, proteinas_g, carboidratos_g,
                    gorduras_g, fibras_g, calcio_mg, ferro_mg, vitamina_a_mcg, vitamina_c_mg,
                    vitamina_d_mcg, acucar_100g, sodio_100g, ingredientes, saudavel, para_thomas, 
                    contem_leite, compatibilidade_thomas) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (nome, qtd, unidade, local, categoria, int(perecivel), 
                     validade.isoformat() if validade else None, valor_compra, local_compra,
                     calorias, proteinas, carboidratos, gorduras, fibras, calcio, ferro,
                     vitamina_a, vitamina_c, vitamina_d, acucar, sodio, ingredientes,
                     nivel_saudavel, int(para_thomas), int(contem_leite), compatibilidade)
                )
                
                # Se houver valor de compra, registrar no histórico de preços
                if valor_compra and qtd > 0 and unidade:
                    item_id = self.cursor.lastrowid
                    valor_unitario = valor_compra / qtd
                    
                    self.cursor.execute(
                        """INSERT INTO historico_precos (item_id, data_compra, valor_unitario, local_compra)
                        VALUES (?, ?, ?, ?)""",
                        (item_id, datetime.date.today().isoformat(), valor_unitario, local_compra)
                    )
                
                self.conn.commit()
                return True, f"Item {nome} adicionado com sucesso!"
        except sqlite3.Error as e:
            return False, f"Erro ao adicionar item: {e}"
    
    def atualizar_item(self, item_id, nome, qtd, unidade, local, categoria, perecivel, validade=None, 
                       valor_compra=None, local_compra=None, calorias=None, proteinas=None, 
                       carboidratos=None, gorduras=None, fibras=None, calcio=None, ferro=None,
                       vitamina_a=None, vitamina_c=None, vitamina_d=None, acucar=None, 
                       sodio=None, ingredientes=None, para_thomas=False, contem_leite=False):
        """Atualiza um item existente no inventário"""
        try:
            with self.lock:
                # Verificar se o valor mudou
                self.cursor.execute("SELECT valor_compra, quantidade FROM itens WHERE id = ?", (item_id,))
                result = self.cursor.fetchone()
                valor_anterior, qtd_anterior = result if result else (None, None)
                
                # Calcular nível de saúde
                nivel_saudavel = 1  # padrão saudável
                
                if acucar is not None and acucar > 15:
                    nivel_saudavel = 3
                elif sodio is not None and sodio > 400:
                    nivel_saudavel = 3
                elif acucar is not None and acucar > 5:
                    nivel_saudavel = 2
                elif sodio is not None and sodio > 200:
                    nivel_saudavel = 2
                
                # Avaliar compatibilidade com Thomas
                compatibilidade = self.avaliar_compatibilidade_thomas(nome, ingredientes, contem_leite)
                
                # Atualizar o item
                self.cursor.execute(
                    """UPDATE itens SET 
                       nome = ?, quantidade = ?, unidade = ?, localizacao = ?, categoria = ?, 
                       perecivel = ?, validade = ?, valor_compra = ?, local_compra = ?,
                       calorias_100g = ?, proteinas_g = ?, carboidratos_g = ?, gorduras_g = ?, 
                       fibras_g = ?, calcio_mg = ?, ferro_mg = ?, vitamina_a_mcg = ?, 
                       vitamina_c_mg = ?, vitamina_d_mcg = ?, acucar_100g = ?, sodio_100g = ?, 
                       ingredientes = ?, saudavel = ?, para_thomas = ?, contem_leite = ?,
                       compatibilidade_thomas = ?
                       WHERE id = ?""",
                    (nome, qtd, unidade, local, categoria, int(perecivel), 
                     validade.isoformat() if validade else None, valor_compra, local_compra,
                     calorias, proteinas, carboidratos, gorduras, fibras, calcio, ferro,
                     vitamina_a, vitamina_c, vitamina_d, acucar, sodio, ingredientes,
                     nivel_saudavel, int(para_thomas), int(contem_leite), compatibilidade, item_id)
                )
                
                # Se o valor mudou e houver quantidade, registrar novo preço
                if valor_compra != valor_anterior and valor_compra is not None and qtd > 0:
                    valor_unitario = valor_compra / qtd
                    
                    self.cursor.execute(
                        """INSERT INTO historico_precos (item_id, data_compra, valor_unitario, local_compra)
                        VALUES (?, ?, ?, ?)""",
                        (item_id, datetime.date.today().isoformat(), valor_unitario, local_compra)
                    )
                
                self.conn.commit()
                return True, f"Item {nome} atualizado com sucesso!"
        except sqlite3.Error as e:
            return False, f"Erro ao atualizar item: {e}"
    
    def registrar_consumo(self, item_id, qtd_consumida, para_thomas=False, data=None):
        """Registra o consumo de um item"""
        if data is None:
            data = datetime.date.today()
            
        try:
            with self.lock:
                # Obter dados do item
                self.cursor.execute("SELECT quantidade, unidade FROM itens WHERE id = ?", (item_id,))
                result = self.cursor.fetchone()
                
                if not result:
                    return False, "Item não encontrado!"
                    
                qtd_atual, unidade = result
                
                # Verificar se há quantidade suficiente
                if qtd_atual < qtd_consumida:
                    return False, "Quantidade insuficiente no estoque!"
                
                # Atualizar quantidade no estoque
                nova_qtd = qtd_atual - qtd_consumida
                self.cursor.execute("UPDATE itens SET quantidade = ? WHERE id = ?", (nova_qtd, item_id))
                
                # Registrar consumo na tabela apropriada
                if para_thomas:
                    self.cursor.execute(
                        "INSERT INTO consumo_thomas (item_id, quantidade_consumida, data_consumo) VALUES (?, ?, ?)",
                        (item_id, qtd_consumida, data.isoformat())
                    )
                else:
                    self.cursor.execute(
                        "INSERT INTO consumo_geral (item_id, quantidade_consumida, data_consumo) VALUES (?, ?, ?)",
                        (item_id, qtd_consumida, data.isoformat())
                    )
                
                self.conn.commit()
                return True, "Consumo registrado com sucesso!"
        except sqlite3.Error as e:
            return False, f"Erro ao registrar consumo: {e}"
    
    def excluir_item(self, item_id):
        """Remove um item do inventário"""
        try:
            with self.lock:
                # Verificar se o item existe
                self.cursor.execute("SELECT id, nome FROM itens WHERE id = ?", (item_id,))
                result = self.cursor.fetchone()
                if not result:
                    return False, "Item não encontrado!"
                
                item_id, nome = result
                
                # Remover registros relacionados primeiro
                try:
                    self.cursor.execute("DELETE FROM historico_precos WHERE item_id = ?", (item_id,))
                except sqlite3.Error:
                    pass  # Ignora se a tabela não existir
                    
                try:
                    self.cursor.execute("DELETE FROM consumo_thomas WHERE item_id = ?", (item_id,))
                except sqlite3.Error:
                    pass  # Ignora se a tabela não existir
                    
                try:
                    self.cursor.execute("DELETE FROM consumo_geral WHERE item_id = ?", (item_id,))
                except sqlite3.Error:
                    pass  # Ignora se a tabela não existir
                
                # Remover o item principal
                self.cursor.execute("DELETE FROM itens WHERE id = ?", (item_id,))
                self.conn.commit()
                return True, f"Item {nome} excluído com sucesso!"
        except sqlite3.Error as e:
            return False, f"Erro ao excluir item: {e}"
    
    def carregar_inventario(self, apenas_thomas=False):
        """Carrega o inventário completo em um DataFrame"""
        try:
            # Verificar colunas disponíveis na tabela
            self.cursor.execute("PRAGMA table_info(itens)")
            cols_info = self.cursor.fetchall()
            available_cols = [col[1] for col in cols_info]
            
            # Construir consulta baseada nas colunas disponíveis
            base_cols = ["id", "nome", "quantidade", "localizacao", "perecivel", "validade"]
            extra_cols = [
                "unidade", "categoria", "data_cadastro", "valor_compra", "local_compra",
                "calorias_100g", "proteinas_g", "carboidratos_g", "gorduras_g", 
                "fibras_g", "calcio_mg", "ferro_mg", "vitamina_a_mcg", 
                "vitamina_c_mg", "vitamina_d_mcg", "acucar_100g", "sodio_100g", 
                "ingredientes", "saudavel", "para_thomas", "contem_leite", 
                "compatibilidade_thomas"
            ]
            
            # Filtrar apenas colunas que existem
            query_cols = base_cols + [col for col in extra_cols if col in available_cols]
            query = f"SELECT {', '.join(query_cols)} FROM itens"
            
            # Adicionar filtro para Thomas se necessário
            if apenas_thomas and "para_thomas" in available_cols:
                query += " WHERE para_thomas = 1"
                
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
            
            if not rows:
                return pd.DataFrame()
            
            # Criar cabeçalhos corretos para o DataFrame
            headers = []
            for col in query_cols:
                if col == "id": headers.append("ID")
                elif col == "nome": headers.append("Nome")
                elif col == "quantidade": headers.append("Quantidade")
                elif col == "unidade": headers.append("Unidade") 
                elif col == "localizacao": headers.append("Localização")
                elif col == "categoria": headers.append("Categoria")
                elif col == "perecivel": headers.append("Perecível")
                elif col == "validade": headers.append("Validade")
                elif col == "data_cadastro": headers.append("Data Cadastro")
                elif col == "valor_compra": headers.append("Valor Compra")
                elif col == "local_compra": headers.append("Local Compra")
                elif col == "calorias_100g": headers.append("Calorias/100g")
                elif col == "proteinas_g": headers.append("Proteínas (g)")
                elif col == "carboidratos_g": headers.append("Carboidratos (g)")
                elif col == "gorduras_g": headers.append("Gorduras (g)")
                elif col == "fibras_g": headers.append("Fibras (g)")
                elif col == "calcio_mg": headers.append("Cálcio (mg)")
                elif col == "ferro_mg": headers.append("Ferro (mg)")
                elif col == "vitamina_a_mcg": headers.append("Vitamina A (mcg)")
                elif col == "vitamina_c_mg": headers.append("Vitamina C (mg)")
                elif col == "vitamina_d_mcg": headers.append("Vitamina D (mcg)")
                elif col == "acucar_100g": headers.append("Açúcar/100g")
                elif col == "sodio_100g": headers.append("Sódio/100g")
                elif col == "ingredientes": headers.append("Ingredientes")
                elif col == "saudavel": headers.append("Nível Saúde")
                elif col == "para_thomas": headers.append("Para Thomas")
                elif col == "contem_leite": headers.append("Contém Leite")
                elif col == "compatibilidade_thomas": headers.append("Compatibilidade Thomas")
                else: headers.append(col)
                
            df = pd.DataFrame(rows, columns=headers)
            
            # Adicionar unidade se não existir na tabela
            if "Unidade" not in df.columns:
                df["Unidade"] = "unidade"
                
            # Adicionar categoria se não existir na tabela
            if "Categoria" not in df.columns:
                df["Categoria"] = "Outros"
                
            # Adicionar Para Thomas se não existir na tabela
            if "Para Thomas" not in df.columns:
                df["Para Thomas"] = 0
                
            # Adicionar Contém Leite se não existir na tabela
            if "Contém Leite" not in df.columns:
                df["Contém Leite"] = 0
                
            # Adicionar Compatibilidade Thomas se não existir na tabela
            if "Compatibilidade Thomas" not in df.columns:
                df["Compatibilidade Thomas"] = 0
                
            # Adicionar Nível Saúde se não existir na tabela  
            if "Nível Saúde" not in df.columns:
                df["Nível Saúde"] = 1
            
            # Calcular dias até vencer
            def calc_days(val, per):
                if per and val:
                    try:
                        d = datetime.datetime.strptime(val, '%Y-%m-%d').date()
                        return (d - datetime.date.today()).days
                    except (ValueError, TypeError):
                        return None
                return None
            
            df["Dias Até Vencer"] = df.apply(
                lambda r: calc_days(r["Validade"], r["Perecível"]), axis=1
            )
            
            # Calcular custo unitário para exibição
            if "Valor Compra" in df.columns and "Quantidade" in df.columns and "Unidade" in df.columns:
                def calc_unit_cost(valor, qtd, unidade):
                    if pd.notna(valor) and pd.notna(qtd) and qtd > 0:
                        return f"R$ {valor/qtd:.2f}/{unidade}"
                    return None
                
                df["Custo Unitário"] = df.apply(
                    lambda r: calc_unit_cost(r["Valor Compra"], r["Quantidade"], r["Unidade"]), axis=1
                )
            
            return df
        except sqlite3.Error as e:
            # Ao invés de mostrar erros na UI, logamos e retornamos dataframe vazio
            print(f"Erro ao carregar inventário: {e}")
            return pd.DataFrame()
    
    def carregar_por_categoria(self, categoria=None):
        """Carrega itens de uma categoria específica"""
        try:
            if not categoria:
                return self.carregar_inventario()
                
            # Verificar primeiro se a coluna categoria existe
            self.cursor.execute("PRAGMA table_info(itens)")
            cols_info = self.cursor.fetchall()
            available_cols = [col[1] for col in cols_info]
            
            if "categoria" not in available_cols:
                print("A coluna 'categoria' não existe na tabela.")
                return self.carregar_inventario()
            
            # Verificar colunas disponíveis na tabela
            base_cols = ["id", "nome", "quantidade", "localizacao", "perecivel", "validade"]
            extra_cols = [
                "unidade", "categoria", "data_cadastro", "valor_compra", "local_compra",
                "calorias_100g", "proteinas_g", "carboidratos_g", "gorduras_g", 
                "fibras_g", "calcio_mg", "ferro_mg", "vitamina_a_mcg", 
                "vitamina_c_mg", "vitamina_d_mcg", "acucar_100g", "sodio_100g", 
                "ingredientes", "saudavel", "para_thomas", "contem_leite",
                "compatibilidade_thomas"
            ]
            
            # Filtrar apenas colunas que existem
            query_cols = base_cols + [col for col in extra_cols if col in available_cols]
            query = f"SELECT {', '.join(query_cols)} FROM itens WHERE categoria = ?"
                
            self.cursor.execute(query, (categoria,))
            rows = self.cursor.fetchall()
            
            if not rows:
                return pd.DataFrame()
            
            # Criar cabeçalhos corretos para o DataFrame
            headers = []
            for col in query_cols:
                if col == "id": headers.append("ID")
                elif col == "nome": headers.append("Nome")
                elif col == "quantidade": headers.append("Quantidade")
                elif col == "unidade": headers.append("Unidade") 
                elif col == "localizacao": headers.append("Localização")
                elif col == "categoria": headers.append("Categoria")
                elif col == "perecivel": headers.append("Perecível")
                elif col == "validade": headers.append("Validade")
                elif col == "data_cadastro": headers.append("Data Cadastro")
                elif col == "valor_compra": headers.append("Valor Compra")
                elif col == "local_compra": headers.append("Local Compra")
                elif col == "calorias_100g": headers.append("Calorias/100g")
                elif col == "proteinas_g": headers.append("Proteínas (g)")
                elif col == "carboidratos_g": headers.append("Carboidratos (g)")
                elif col == "gorduras_g": headers.append("Gorduras (g)")
                elif col == "fibras_g": headers.append("Fibras (g)")
                elif col == "calcio_mg": headers.append("Cálcio (mg)")
                elif col == "ferro_mg": headers.append("Ferro (mg)")
                elif col == "vitamina_a_mcg": headers.append("Vitamina A (mcg)")
                elif col == "vitamina_c_mg": headers.append("Vitamina C (mg)")
                elif col == "vitamina_d_mcg": headers.append("Vitamina D (mcg)")
                elif col == "acucar_100g": headers.append("Açúcar/100g")
                elif col == "sodio_100g": headers.append("Sódio/100g")
                elif col == "ingredientes": headers.append("Ingredientes")
                elif col == "saudavel": headers.append("Nível Saúde")
                elif col == "para_thomas": headers.append("Para Thomas")
                elif col == "contem_leite": headers.append("Contém Leite")
                elif col == "compatibilidade_thomas": headers.append("Compatibilidade Thomas")
                else: headers.append(col)
                
            df = pd.DataFrame(rows, columns=headers)
            
            # Adicionar unidade se não existir na tabela
            if "Unidade" not in df.columns:
                df["Unidade"] = "unidade"
                
            # Adicionar Para Thomas se não existir na tabela
            if "Para Thomas" not in df.columns:
                df["Para Thomas"] = 0
                
            # Adicionar Contém Leite se não existir na tabela
            if "Contém Leite" not in df.columns:
                df["Contém Leite"] = 0
                
            # Adicionar Compatibilidade Thomas se não existir na tabela
            if "Compatibilidade Thomas" not in df.columns:
                df["Compatibilidade Thomas"] = 0
                
            # Adicionar Nível Saúde se não existir na tabela  
            if "Nível Saúde" not in df.columns:
                df["Nível Saúde"] = 1
            
            # Calcular dias até vencer
            def calc_days(val, per):
                if per and val:
                    try:
                        d = datetime.datetime.strptime(val, '%Y-%m-%d').date()
                        return (d - datetime.date.today()).days
                    except (ValueError, TypeError):
                        return None
                return None
            
            df["Dias Até Vencer"] = df.apply(
                lambda r: calc_days(r["Validade"], r["Perecível"]), axis=1
            )
            
            return df
        except sqlite3.Error as e:
            print(f"Erro ao carregar itens por categoria: {e}")
            return pd.DataFrame()
    
    def obter_tendencia_precos(self, item_id=None):
        """Obtém a tendência de preços de um item ou de todos os itens"""
        try:
            # Verificar se a tabela historico_precos existe
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='historico_precos'")
            if not self.cursor.fetchone():
                return pd.DataFrame()
            
            if item_id:
                query = """
                    SELECT i.nome, h.data_compra, h.valor_unitario, h.local_compra
                    FROM historico_precos h
                    JOIN itens i ON h.item_id = i.id
                    WHERE h.item_id = ?
                    ORDER BY h.data_compra
                """
                self.cursor.execute(query, (item_id,))
            else:
                query = """
                    SELECT i.nome, h.data_compra, h.valor_unitario, h.local_compra
                    FROM historico_precos h
                    JOIN itens i ON h.item_id = i.id
                    ORDER BY h.data_compra
                """
                self.cursor.execute(query)
                
            rows = self.cursor.fetchall()
            
            if not rows:
                return pd.DataFrame()
                
            df = pd.DataFrame(rows, columns=["Nome", "Data", "Valor Unitário", "Local Compra"])
            df["Data"] = pd.to_datetime(df["Data"])
            
            return df
        except sqlite3.Error as e:
            print(f"Erro ao obter tendência de preços: {e}")
            return pd.DataFrame()
    
    def obter_categorias(self):
        """Obtém lista de categorias cadastradas"""
        try:
            # Verificar se a coluna categoria existe
            self.cursor.execute("PRAGMA table_info(itens)")
            cols_info = self.cursor.fetchall()
            available_cols = [col[1] for col in cols_info]
            
            if "categoria" not in available_cols:
                return []
                
            self.cursor.execute("SELECT DISTINCT categoria FROM itens WHERE categoria IS NOT NULL")
            categorias = [row[0] for row in self.cursor.fetchall()]
            return categorias
        except sqlite3.Error as e:
            print(f"Erro ao obter categorias: {e}")
            return []
    
    def obter_locais_compra(self):
        """Obtém lista de locais de compra cadastrados"""
        try:
            # Verificar se a coluna local_compra existe
            self.cursor.execute("PRAGMA table_info(itens)")
            cols_info = self.cursor.fetchall()
            available_cols = [col[1] for col in cols_info]
            
            if "local_compra" not in available_cols:
                return []
                
            self.cursor.execute("SELECT DISTINCT local_compra FROM itens WHERE local_compra IS NOT NULL")
            locais = [row[0] for row in self.cursor.fetchall() if row[0]]
            return locais
        except sqlite3.Error as e:
            print(f"Erro ao obter locais de compra: {e}")
            return []
    
    def obter_estatisticas_consumo(self, apenas_thomas=False, periodo_dias=30):
        """Obtém estatísticas de consumo"""
        try:
            # Verificar se as tabelas de consumo existem
            if apenas_thomas:
                table_name = "consumo_thomas"
            else:
                table_name = "consumo_geral"
                
            self.cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            if not self.cursor.fetchone():
                return pd.DataFrame()
            
            # Verificar se a coluna unidade e categoria existem
            self.cursor.execute("PRAGMA table_info(itens)")
            cols_info = self.cursor.fetchall()
            available_cols = [col[1] for col in cols_info]
            
            categoria_col = "categoria" if "categoria" in available_cols else "localizacao"
            unidade_col = "unidade" if "unidade" in available_cols else "'unidade'"
            
            # Data limite para o período de análise
            data_limite = (datetime.date.today() - datetime.timedelta(days=periodo_dias)).isoformat()
            
            # Consulta com filtro de data
            query = f"""
                SELECT i.nome, i.{categoria_col}, SUM(c.quantidade_consumida), i.{unidade_col},
                       i.proteinas_g, i.calcio_mg, i.vitamina_d_mcg, i.ferro_mg, i.vitamina_c_mg
                FROM {table_name} c
                JOIN itens i ON c.item_id = i.id
                WHERE c.data_consumo >= ?
                GROUP BY i.nome, i.{categoria_col}, i.{unidade_col}, 
                         i.proteinas_g, i.calcio_mg, i.vitamina_d_mcg, i.ferro_mg, i.vitamina_c_mg
                ORDER BY SUM(c.quantidade_consumida) DESC
            """
            
            self.cursor.execute(query, (data_limite,))
            rows = self.cursor.fetchall()
            
            if not rows:
                return pd.DataFrame()
            
            col_header = "Categoria" if categoria_col == "categoria" else "Localização" 
            
            # Incluir colunas nutricionais
            df = pd.DataFrame(rows, columns=[
                "Nome", col_header, "Quantidade Consumida", "Unidade", 
                "Proteínas (g)", "Cálcio (mg)", "Vitamina D (mcg)", 
                "Ferro (mg)", "Vitamina C (mg)"
            ])
            
            # Calcular nutrientes consumidos totais
            for col in ["Proteínas (g)", "Cálcio (mg)", "Vitamina D (mcg)", 
                        "Ferro (mg)", "Vitamina C (mg)"]:
                # Multiplicar valor nutricional pela quantidade consumida
                df[f"{col} Consumido"] = df.apply(
                    lambda r: r[col] * r["Quantidade Consumida"] / 100 if pd.notna(r[col]) else 0, axis=1
                )
            
            return df
        except sqlite3.Error as e:
            print(f"Erro ao obter estatísticas de consumo: {e}")
            return pd.DataFrame()
            
    def obter_nutrientes_consumidos(self, apenas_thomas=False, periodo_dias=7):
        """
        Obtém os nutrientes consumidos em um período
        Retorna um DataFrame com soma diária de nutrientes principais
        """
        try:
            # Tabela de consumo apropriada
            tabela = "consumo_thomas" if apenas_thomas else "consumo_geral"
            
            # Data limite para o período
            data_limite = (datetime.date.today() - datetime.timedelta(days=periodo_dias)).isoformat()
            
            # Consulta para obter consumo diário com nutrientes
            query = f"""
                SELECT 
                    c.data_consumo,
                    SUM(i.proteinas_g * c.quantidade_consumida / 100) as proteinas,
                    SUM(i.calcio_mg * c.quantidade_consumida / 100) as calcio,
                    SUM(i.ferro_mg * c.quantidade_consumida / 100) as ferro,
                    SUM(i.vitamina_d_mcg * c.quantidade_consumida / 100) as vit_d,
                    SUM(i.vitamina_c_mg * c.quantidade_consumida / 100) as vit_c
                FROM {tabela} c
                JOIN itens i ON c.item_id = i.id
                WHERE c.data_consumo >= ?
                GROUP BY c.data_consumo
                ORDER BY c.data_consumo
            """
            
            self.cursor.execute(query, (data_limite,))
            rows = self.cursor.fetchall()
            
            if not rows:
                return pd.DataFrame()
            
            df = pd.DataFrame(rows, columns=[
                "Data", "Proteínas (g)", "Cálcio (mg)", "Ferro (mg)", 
                "Vitamina D (mcg)", "Vitamina C (mg)"
            ])
            
            # Converter data para formato datetime
            df["Data"] = pd.to_datetime(df["Data"])
            
            # Preencher valores nulos com 0
            df = df.fillna(0)
            
            return df
            
        except sqlite3.Error as e:
            print(f"Erro ao obter nutrientes consumidos: {e}")
            return pd.DataFrame()

    def obter_restricoes_thomas(self, apenas_ativos=True):
        """Obtém lista de restrições alimentares de Thomas"""
        try:
            query = """
                SELECT id, tipo, substancia, nivel_gravidade, sintomas, substituicoes, ativo
                FROM restricoes_thomas
            """
            
            if apenas_ativos:
                query += " WHERE ativo = 1"
                
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
            
            if not rows:
                return []
                
            restricoes = []
            for row in rows:
                restricao = {
                    'id': row[0],
                    'tipo': row[1],
                    'substancia': row[2],
                    'nivel_gravidade': row[3],
                    'sintomas': row[4].split(',') if row[4] else [],
                    'substituicoes': row[5].split(',') if row[5] else [],
                    'ativo': bool(row[6])
                }
                restricoes.append(restricao)
                
            return restricoes
            
        except sqlite3.Error as e:
            print(f"Erro ao obter restrições: {e}")
            return []
    
    def adicionar_restricao_thomas(self, tipo, substancia, nivel_gravidade, sintomas=None, substituicoes=None):
        """Adiciona uma nova restrição alimentar para Thomas"""
        try:
            with self.lock:
                # Converter listas para string separada por vírgulas
                sintomas_str = ','.join(sintomas) if sintomas else None
                substituicoes_str = ','.join(substituicoes) if substituicoes else None
                
                self.cursor.execute(
                    """INSERT INTO restricoes_thomas (tipo, substancia, nivel_gravidade, sintomas, substituicoes)
                    VALUES (?, ?, ?, ?, ?)""",
                    (tipo, substancia, nivel_gravidade, sintomas_str, substituicoes_str)
                )
                
                self.conn.commit()
                return True, f"Restrição a {substancia} adicionada com sucesso!"
        except sqlite3.Error as e:
            return False, f"Erro ao adicionar restrição: {e}"
    
    def remover_restricao_thomas(self, restricao_id):
        """Remove uma restrição alimentar (marca como inativa)"""
        try:
            with self.lock:
                self.cursor.execute(
                    "SELECT substancia FROM restricoes_thomas WHERE id = ?",
                    (restricao_id,)
                )
                result = self.cursor.fetchone()
                
                if not result:
                    return False, "Restrição não encontrada!"
                
                substancia = result[0]
                
                self.cursor.execute(
                    "UPDATE restricoes_thomas SET ativo = 0 WHERE id = ?",
                    (restricao_id,)
                )
                
                self.conn.commit()
                return True, f"Restrição a {substancia} removida com sucesso!"
        except sqlite3.Error as e:
            return False, f"Erro ao remover restrição: {e}"
    
    def obter_necessidades_thomas(self):
        """Obtém as necessidades nutricionais de Thomas"""
        try:
            self.cursor.execute("""
                SELECT id, nutriente, quantidade_diaria, unidade, prioridade
                FROM necessidades_thomas
                ORDER BY prioridade DESC, nutriente
            """)
            
            rows = self.cursor.fetchall()
            
            if not rows:
                return []
                
            necessidades = []
            for row in rows:
                necessidade = {
                    'id': row[0],
                    'nutriente': row[1],
                    'quantidade_diaria': row[2],
                    'unidade': row[3],
                    'prioridade': row[4]
                }
                necessidades.append(necessidade)
                
            return necessidades
            
        except sqlite3.Error as e:
            print(f"Erro ao obter necessidades nutricionais: {e}")
            return []
    
    def atualizar_necessidade_thomas(self, necessidade_id, quantidade_diaria, prioridade):
        """Atualiza uma necessidade nutricional de Thomas"""
        try:
            with self.lock:
                self.cursor.execute(
                    "SELECT nutriente FROM necessidades_thomas WHERE id = ?",
                    (necessidade_id,)
                )
                result = self.cursor.fetchone()
                
                if not result:
                    return False, "Necessidade nutricional não encontrada!"
                    
                nutriente = result[0]
                
                self.cursor.execute(
                    """UPDATE necessidades_thomas 
                    SET quantidade_diaria = ?, prioridade = ? 
                    WHERE id = ?""",
                    (quantidade_diaria, prioridade, necessidade_id)
                )
                
                self.conn.commit()
                return True, f"Necessidade de {nutriente} atualizada com sucesso!"
        except sqlite3.Error as e:
            return False, f"Erro ao atualizar necessidade nutricional: {e}"
    
    def recalcular_compatibilidade_todos_itens(self):
        """Recalcula a compatibilidade de todos os itens para Thomas"""
        try:
            with self.lock:
                # Obter todos os itens
                self.cursor.execute("SELECT id, nome, ingredientes, contem_leite FROM itens")
                itens = self.cursor.fetchall()
                
                atualizados = 0
                for item in itens:
                    item_id, nome, ingredientes, contem_leite = item
                    compatibilidade = self.avaliar_compatibilidade_thomas(nome, ingredientes, contem_leite)
                    
                    # Atualizar compatibilidade
                    self.cursor.execute(
                        "UPDATE itens SET compatibilidade_thomas = ? WHERE id = ?",
                        (compatibilidade, item_id)
                    )
                    atualizados += 1
                    
                self.conn.commit()
                return True, f"Compatibilidade de {atualizados} itens recalculada com sucesso!"
        except sqlite3.Error as e:
            return False, f"Erro ao recalcular compatibilidades: {e}"
    
    def exportar_csv(self):
        """Exporta o inventário para um arquivo CSV"""
        try:
            df = self.carregar_inventario()
            if df.empty:
                return False, "Não há dados para exportar.", ""
                
            csv_file = "inventario_geladeira.csv"
            df.to_csv(csv_file, index=False)
            return True, "Arquivo CSV criado com sucesso!", csv_file
        except Exception as e:
            return False, f"Erro ao exportar CSV: {e}", ""
    
    def importar_csv(self, uploaded_file):
        """Importa itens de um arquivo CSV"""
        try:
            df = pd.read_csv(uploaded_file)
            
            # Requisitos mínimos (compatibilidade com versões antigas)
            required_cols = ["Nome", "Quantidade"]
            
            if not all(col in df.columns for col in required_cols):
                return False, "Arquivo CSV não contém as colunas básicas necessárias (Nome, Quantidade)"
                
            with self.lock:
                itens_importados = 0
                for _, row in df.iterrows():
                    nome = row["Nome"]
                    
                    try:
                        qtd = float(row["Quantidade"])
                    except (ValueError, TypeError):
                        qtd = 1.0
                    
                    # Campos que podem não existir no CSV
                    unidade = row.get("Unidade", "unidade") if "Unidade" in df.columns else "unidade"
                    local = row.get("Localização", "Geladeira – Inferior") if "Localização" in df.columns else "Geladeira – Inferior"
                    categoria = row.get("Categoria", "Outros") if "Categoria" in df.columns else "Outros"
                    perecivel = bool(row.get("Perecível", True)) if "Perecível" in df.columns else True
                    
                    validade = None
                    if "Validade" in df.columns and pd.notna(row["Validade"]):
                        try:
                            validade = datetime.datetime.strptime(
                                str(row["Validade"]), '%Y-%m-%d'
                            ).date()
                        except ValueError:
                            pass
                    
                    valor_compra = None
                    if "Valor Compra" in df.columns and pd.notna(row["Valor Compra"]):
                        try:
                            valor_compra = float(row["Valor Compra"])
                        except (ValueError, TypeError):
                            pass
                    
                    local_compra = None
                    if "Local Compra" in df.columns and pd.notna(row["Local Compra"]):
                        local_compra = row["Local Compra"]
                    
                    calorias = None
                    if "Calorias/100g" in df.columns and pd.notna(row["Calorias/100g"]):
                        try:
                            calorias = float(row["Calorias/100g"])
                        except (ValueError, TypeError):
                            pass
                            
                    # Nutrientes
                    proteinas = None
                    if "Proteínas (g)" in df.columns and pd.notna(row["Proteínas (g)"]):
                        try:
                            proteinas = float(row["Proteínas (g)"])
                        except (ValueError, TypeError):
                            pass
                    
                    carboidratos = None
                    if "Carboidratos (g)" in df.columns and pd.notna(row["Carboidratos (g)"]):
                        try:
                            carboidratos = float(row["Carboidratos (g)"])
                        except (ValueError, TypeError):
                            pass
                    
                    gorduras = None
                    if "Gorduras (g)" in df.columns and pd.notna(row["Gorduras (g)"]):
                        try:
                            gorduras = float(row["Gorduras (g)"])
                        except (ValueError, TypeError):
                            pass
                    
                    fibras = None
                    if "Fibras (g)" in df.columns and pd.notna(row["Fibras (g)"]):
                        try:
                            fibras = float(row["Fibras (g)"])
                        except (ValueError, TypeError):
                            pass
                    
                    calcio = None
                    if "Cálcio (mg)" in df.columns and pd.notna(row["Cálcio (mg)"]):
                        try:
                            calcio = float(row["Cálcio (mg)"])
                        except (ValueError, TypeError):
                            pass
                    
                    ferro = None
                    if "Ferro (mg)" in df.columns and pd.notna(row["Ferro (mg)"]):
                        try:
                            ferro = float(row["Ferro (mg)"])
                        except (ValueError, TypeError):
                            pass
                    
                    vitamina_a = None
                    if "Vitamina A (mcg)" in df.columns and pd.notna(row["Vitamina A (mcg)"]):
                        try:
                            vitamina_a = float(row["Vitamina A (mcg)"])
                        except (ValueError, TypeError):
                            pass
                    
                    vitamina_c = None
                    if "Vitamina C (mg)" in df.columns and pd.notna(row["Vitamina C (mg)"]):
                        try:
                            vitamina_c = float(row["Vitamina C (mg)"])
                        except (ValueError, TypeError):
                            pass
                    
                    vitamina_d = None
                    if "Vitamina D (mcg)" in df.columns and pd.notna(row["Vitamina D (mcg)"]):
                        try:
                            vitamina_d = float(row["Vitamina D (mcg)"])
                        except (ValueError, TypeError):
                            pass
                    
                    acucar = None
                    if "Açúcar/100g" in df.columns and pd.notna(row["Açúcar/100g"]):
                        try:
                            acucar = float(row["Açúcar/100g"])
                        except (ValueError, TypeError):
                            pass
                    
                    sodio = None
                    if "Sódio/100g" in df.columns and pd.notna(row["Sódio/100g"]):
                        try:
                            sodio = float(row["Sódio/100g"])
                        except (ValueError, TypeError):
                            pass
                    
                    ingredientes = None
                    if "Ingredientes" in df.columns and pd.notna(row["Ingredientes"]):
                        ingredientes = str(row["Ingredientes"])
                    
                    para_thomas = False
                    if "Para Thomas" in df.columns:
                        para_thomas = bool(row["Para Thomas"])
                        
                    contem_leite = False
                    if "Contém Leite" in df.columns:
                        contem_leite = bool(row["Contém Leite"])
                    else:
                        # Verificação automática para produtos lácteos
                        nome_lower = nome.lower()
                        if any(term in nome_lower for term in TERMOS_LACTEOS):
                            contem_leite = True
                        
                        if ingredientes:
                            ingredientes_lower = ingredientes.lower()
                            if any(term in ingredientes_lower for term in TERMOS_LACTEOS):
                                contem_leite = True
                            
                    success, _ = self.adicionar_item(
                        nome, qtd, unidade, local, categoria, perecivel, validade, 
                        valor_compra, local_compra, calorias, proteinas, carboidratos,
                        gorduras, fibras, calcio, ferro, vitamina_a, vitamina_c,
                        vitamina_d, acucar, sodio, ingredientes, para_thomas, contem_leite
                    )
                    
                    if success:
                        itens_importados += 1
                    
                return True, f"{itens_importados} itens importados com sucesso!"
        except Exception as e:
            return False, f"Erro ao importar CSV: {e}"
    
    def resetar_banco(self):
        """Reseta completamente o banco de dados"""
        try:
            # Fechar conexão atual
            self.conn.close()
            
            # Criar backup
            if os.path.exists(self.db_path):
                backup_name = f"geladeira_backup_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.db"
                os.rename(self.db_path, backup_name)
                msg = f"Backup criado: {backup_name}"
            else:
                msg = "Não havia banco de dados anterior para backup."
            
            # Recriar conexão e tabelas
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.cursor = self.conn.cursor()
            success, create_msg = self._create_new_tables()
            
            if success:
                return True, f"{msg}\n{create_msg}"
            else:
                return False, f"{msg}\nFalha ao criar novas tabelas: {create_msg}"
        except Exception as e:
            return False, f"Erro ao resetar banco de dados: {e}"
def obter_historico_preco_detalhado(self, item_id=None):
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
        
        self.cursor.execute(query_base, params)
        rows = self.cursor.fetchall()
        
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

def calcular_estatisticas_preco(self):
    """Calcula estatísticas avançadas de preços dos produtos"""
    df = self.obter_historico_preco_detalhado()
    
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    # Estatísticas por produto
    estatisticas_produtos = df.groupby(["ID", "Nome", "Unidade"]).agg(
        media=("Valor Unitário", "mean"),
        mediana=("Valor Unitário", "median"),
        minimo=("Valor Unitário", "min"),
        maximo=("Valor Unitário", "max"),
        desvio_padrao=("Valor Unitário", "std"),
        contagem=("Valor Unitário", "count"),
        ultima_compra=("Data Compra", "max")
    ).reset_index()
    
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
            
            # Calcular tendências
            variacao_total = ((ultimo_preco - primeiro_preco) / primeiro_preco) * 100
            variacao_recente = ((ultimo_preco - penultimo_preco) / penultimo_preco) * 100
            
            # Calcular posição em relação à média
            posicao_media = ((ultimo_preco - item_stats["media"]) / item_stats["media"]) * 100
            
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
            volatilidade = (item_stats["desvio_padrao"] / item_stats["media"]) * 100
            
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
                economia = ((item_por_local["preco_medio"].max() - melhor["preco_medio"]) / 
                           item_por_local["preco_medio"].max()) * 100
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
        if not produtos_quantidades:
            return pd.DataFrame(), 0, 0, {}
        
        # Obter histórico de preços
        produto_ids = list(produtos_quantidades.keys())
        
        # Consulta para obter preços mais recentes de cada produto por local
        query = """
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
                WHERE h.item_id IN ({})
            )
            SELECT item_id, nome, unidade, local_compra, valor_unitario, data_compra
            FROM RankedPrices
            WHERE rn = 1
            ORDER BY nome, local_compra
        """.format(','.join(['?'] * len(produto_ids)))
        
        self.cursor.execute(query, produto_ids)
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
                
                # Encontrar o local mais barato disponível
                mais_barato = produto_precos.loc[produto_precos["Valor Unitário"].idxmin()]
                melhor_local[id_produto] = {
                    "local": mais_barato["Local Compra"],
                    "preco": mais_barato["Valor Unitário"],
                }
        
        # Criar DataFrame de resultado
        resultados = []
        locais_compra = set()
        
        for id_produto, quantidade in produtos_quantidades.items():
            nome_produto = precos_df[precos_df["ID"] == id_produto]["Nome"].iloc[0]
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
                    nome_produto, preco_unitario, unidade = item
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
                economia_percentual = ((preco_max - preco_unitario) / preco_max) * 100 if preco_unitario else None
                valor_economia = (preco_max - preco_unitario) * quantidade if preco_unitario else None
            
            # Calcular posição em relação à média global
            preco_medio_global = precos_medios_globais[precos_medios_globais["ID"] == id_produto]["Preço Médio Global"].iloc[0]
            posicao_vs_media = ((preco_unitario - preco_medio_global) / preco_medio_global) * 100 if preco_unitario else None
            
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
        
        # Criar DataFrame final
        resultado_df = pd.DataFrame(resultados)
        
        # Calcular totais
        custo_total = resultado_df["Preço Total"].sum() if "Preço Total" in resultado_df else 0
        economia_total = resultado_df["Valor Economizado"].sum() if "Valor Economizado" in resultado_df else 0
        
        # Calcular total por local
        total_por_local = {}
        for local in locais_compra:
            itens_local = resultado_df[resultado_df["Local Recomendado"] == local]
            total_por_local[local] = itens_local["Preço Total"].sum() if "Preço Total" in itens_local else 0
        
        return resultado_df, custo_total, economia_total, total_por_local
        
    except sqlite3.Error as e:
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