"""
Pacote de testes para o Sistema GELADEIRA
"""

import os
import sys
import tempfile

# Garantir que o diretório raiz está no PYTHONPATH para importações relativas funcionarem
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Utilitários para testes
def get_test_db():
    """
    Cria um banco de dados temporário para testes
    
    Returns:
        tuple: (file_descriptor, path)
    """
    return tempfile.mkstemp(suffix='.db', prefix='geladeira_test_')
