"""
Fixtures compartilhadas para testes do Sistema GELADEIRA
"""
import pytest
import tempfile
import os
import datetime
from pathlib import Path

from db.extended_database_manager import ExtendedDatabaseManager

@pytest.fixture
def test_db_path():
    """Fornece um caminho temporário para o banco de dados de teste."""
    fd, path = tempfile.mkstemp(suffix='.db')
    yield path
    os.close(fd)
    if os.path.exists(path):
        os.unlink(path)

@pytest.fixture
def db_manager(test_db_path):
    """Fornece uma instância do gerenciador de banco de dados configurado para testes."""
    manager = ExtendedDatabaseManager(test_db_path)
    manager.inicializar_banco()
    yield manager
    manager.fechar()

@pytest.fixture
def sample_data(db_manager):
    """Adiciona dados de amostra ao banco de dados."""
    hoje = datetime.date.today()
    
    # Adicionar itens de teste
    items = [
        {
            'nome': 'Leite',
            'categoria': 'Laticínios',
            'quantidade': 1.0,
            'unidade': 'litro',
            'validade': hoje + datetime.timedelta(days=7),
            'localizacao': 'Geladeira – Inferior',
            'custo_unitario': 4.99,
            'para_thomas': False,
            'contem_leite': True
        },
        {
            'nome': 'Maçã',
            'categoria': 'Frutas',
            'quantidade': 5.0,
            'unidade': 'unidade',
            'validade': hoje + datetime.timedelta(days=10),
            'localizacao': 'Fruteira',
            'custo_unitario': 2.50,
            'para_thomas': True,
            'contem_leite': False
        }
    ]
    
    item_ids = []
    for item in items:
        item_id = db_manager.adicionar_item(
            nome=item['nome'],
            categoria=item['categoria'],
            quantidade=item['quantidade'],
            unidade=item['unidade'],
            validade=item['validade'],
            localizacao=item['localizacao'],
            custo_unitario=item['custo_unitario'],
            para_thomas=item['para_thomas'],
            contem_leite=item['contem_leite']
        )
        item_ids.append(item_id)
        
    return item_ids
