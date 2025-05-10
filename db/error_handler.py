import os
import shutil
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

class DatabaseErrorHandler:
    """Classe para lidar com erros de banco de dados e recuperação"""
    
    @staticmethod
    def handle_critical_error(db_path, error_message):
        """
        Trata erros críticos de banco de dados
        
        Args:
            db_path: Caminho para o arquivo de banco de dados
            error_message: Mensagem de erro
            
        Returns:
            bool: True se a recuperação foi bem-sucedida, False caso contrário
        """
        logging.error(f"Erro crítico no banco de dados: {error_message}")
        
        if not db_path or not os.path.exists(db_path):
            logging.error("Caminho do banco de dados inválido ou inexistente.")
            return False
        
        # Criar backup do arquivo corrompido
        try:
            backup_dir = Path(db_path).parent / "backups"
            backup_dir.mkdir(exist_ok=True)
            
            backup_path = backup_dir / f"geladeira_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(db_path, backup_path)
            logging.info(f"Backup do banco de dados criado em: {backup_path}")
        except Exception as e:
            logging.error(f"Falha ao criar backup: {e}")
            return False
            
        try:
            # Tentar recriar o banco de dados se estiver corrompido
            from .extended_database_manager import ExtendedDatabaseManager
            
            # Remover arquivo corrompido
            os.remove(db_path)
            logging.info(f"Arquivo de banco de dados corrompido removido: {db_path}")
            
            # Inicializar novo banco
            db_manager = ExtendedDatabaseManager(db_path)
            success, message = db_manager.inicializar_banco()
            
            if success:
                logging.info(f"Banco de dados reinicializado com sucesso: {db_path}")
                return True
            else:
                logging.error(f"Falha ao reinicializar banco de dados: {message}")
                return False
        except Exception as e:
            logging.error(f"Erro durante recuperação do banco de dados: {e}")
            return False
    
    @staticmethod
    def verify_database_integrity(conn):
        """
        Verifica a integridade do banco de dados
        
        Args:
            conn: Conexão com o banco de dados
            
        Returns:
            tuple: (integridade_ok, mensagem)
        """
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            
            if not result:
                return False, "Nenhum resultado retornado pelo PRAGMA integrity_check."
            
            if result[0] == "ok":
                return True, "Banco de dados íntegro"
            else:
                return False, f"Problemas de integridade encontrados: {result[0]}"
        except sqlite3.Error as e:
            return False, f"Erro ao verificar integridade: {e}"
        except Exception as e:
            return False, f"Erro inesperado ao verificar integridade: {e}"

    @staticmethod
    def optimize_database(conn):
        """
        Otimiza o banco de dados
        
        Args:
            conn: Conexão com o banco de dados
            
        Returns:
            bool: True se a otimização foi bem-sucedida
        """
        try:
            cursor = conn.cursor()
            logging.info("Iniciando otimização do banco de dados...")
            
            # Executar VACUUM para recuperar espaço
            cursor.execute("VACUUM")
            
            # Otimizar índices e estruturas
            cursor.execute("PRAGMA optimize")
            
            # Reindexar
            cursor.execute("REINDEX")
            
            logging.info("Otimização do banco de dados concluída com sucesso.")
            return True
        except sqlite3.Error as e:
            logging.error(f"Erro ao otimizar banco de dados: {e}")
            return False
        except Exception as e:
            logging.error(f"Erro inesperado ao otimizar banco de dados: {e}")
            return False
