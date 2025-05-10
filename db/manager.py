"""
Gerenciador básico de banco de dados.
Essa classe é mantida por questões de compatibilidade, mas a implementação 
principal está em ExtendedDatabaseManager.
"""
import datetime
import sqlite3
import logging
from threading import Lock

logger = logging.getLogger(__name__)

class Manager:
    """
    Gerenciador básico de banco de dados SQLite com suporte a threading.
    """
    def __init__(self, db_path):
        """
        Inicializa o gerenciador de banco de dados.
        
        Args:
            db_path (str): Caminho para o arquivo de banco de dados.
        """
        self.db_path = db_path
        self.lock = Lock()
        try:
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            logger.error(f"Erro ao conectar ao banco de dados: {str(e)}")
            self.conn = None
            self.cursor = None

    def _registrar_consumo_nutrientes(self, item_id, nome_item, data, para_thomas, nutrientes):
        """
        Registra o consumo de nutrientes no banco de dados.
        
        Args:
            item_id (int): ID do item consumido
            nome_item (str): Nome do item
            data (date|str): Data do consumo
            para_thomas (bool): Indica se o consumo foi para Thomas
            nutrientes (dict): Dicionário de nutrientes e valores
            
        Returns:
            int: ID do registro ou 0 se falhar
        """
        # Validação de parâmetros
        if not isinstance(item_id, int) or item_id <= 0:
            raise ValueError("ID do item inválido.")
        if not nome_item or not isinstance(nome_item, str):
            raise ValueError("Nome do item inválido.")
        if isinstance(data, str):
            try:
                data = datetime.datetime.strptime(data, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("Data inválida.")
        elif not isinstance(data, datetime.date):
            raise ValueError("Data inválida.")
        if not isinstance(para_thomas, (bool, int)):
            raise ValueError("Valor para 'para_thomas' inválido.")
        if not isinstance(nutrientes, dict) or not nutrientes:
            raise ValueError("Nutrientes inválidos.")

        # Inserção no banco de dados
        try:
            with self.lock:
                last_id = 0
                for nutr, val in nutrientes.items():
                    if not isinstance(val, (int, float)) or val < 0:
                        logger.warning(f"Valor inválido para o nutriente '{nutr}': {val}")
                        continue
                    self.cursor.execute(
                        """
                        INSERT INTO consumo_nutrientes (item_id, nome_item, data_consumo, para_thomas, nutriente, valor)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (item_id, nome_item, data, int(para_thomas), nutr, val)
                    )
                    last_id = self.cursor.lastrowid
                self.conn.commit()
            return last_id
        except sqlite3.Error as e:
            logger.error(f"Erro ao registrar consumo de nutrientes: {e}")
            self.conn.rollback()
            return 0
        except Exception as e:
            logger.error(f"Erro inesperado ao registrar consumo de nutrientes: {e}")
            self.conn.rollback()
            return 0
            
    def fechar(self):
        """
        Fecha a conexão com o banco de dados.
        """
        if self.conn:
            try:
                self.conn.close()
                self.conn = None
                self.cursor = None
            except sqlite3.Error as e:
                logger.error(f"Erro ao fechar conexão com banco de dados: {str(e)}")
                
    def __del__(self):
        """
        Destrutor para garantir que a conexão seja fechada.
        """
        self.fechar()
