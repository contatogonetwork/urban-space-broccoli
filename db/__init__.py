"""
Inicialização do módulo de banco de dados para o Sistema GELADEIRA

Este pacote contém a implementação dos gerenciadores de banco de dados
e funções auxiliares para operações com SQLite.
"""

try:
    from .extended_database_manager import ExtendedDatabaseManager
except ImportError:
    # Caso a implementação completa não esteja disponível
    import logging
    logging.warning("ExtendedDatabaseManager não disponível. Algumas funcionalidades podem estar indisponíveis.")
    
    class ExtendedDatabaseManager:
        """Implementação temporária para não quebrar importações"""
        def __init__(self, db_path):
            self.db_path = db_path
            logging.error(f"Tentativa de usar ExtendedDatabaseManager não implementada")

try:
    from .error_handler import DatabaseErrorHandler
except ImportError:
    import logging
    logging.warning("DatabaseErrorHandler não disponível. Tratamento de erros pode estar limitado.")
    
    class DatabaseErrorHandler:
        """Implementação temporária para não quebrar importações"""
        @staticmethod
        def handle_critical_error(db_path, error_message):
            logging.error(f"Erro crítico no DB {db_path}: {error_message}")
            return False
            
        @staticmethod
        def verify_database_integrity(conn):
            return False, "Verificador de integridade não implementado"
            
        @staticmethod
        def optimize_database(conn):
            return False

# Definir __all__ para uso com import *
__all__ = ['ExtendedDatabaseManager', 'DatabaseErrorHandler']
