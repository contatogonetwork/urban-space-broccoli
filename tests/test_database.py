import os
import unittest
import tempfile
import sqlite3
from datetime import date, timedelta

# Importe os componentes a serem testados
from db.extended_database_manager import ExtendedDatabaseManager
from db.error_handler import DatabaseErrorHandler

class TestDatabaseManager(unittest.TestCase):
    """Testes para o gerenciador de banco de dados"""
    
    def setUp(self):
        """Configuração para cada teste"""
        # Criar um banco de dados temporário para os testes
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix='.db')
        self.db_manager = ExtendedDatabaseManager(self.temp_db_path)
        self.db_manager.inicializar_banco()
    
    def tearDown(self):
        """Limpeza após cada teste"""
        self.db_manager.fechar()
        os.close(self.temp_db_fd)
        os.unlink(self.temp_db_path)
    
    def test_inicializacao_banco(self):
        """Testa se o banco é inicializado corretamente"""
        # Verificar se as tabelas foram criadas
        conn = sqlite3.connect(self.temp_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        
        # Verificar tabelas essenciais
        essential_tables = ['itens', 'consumo', 'configuracoes']
        for table in essential_tables:
            self.assertIn(table, table_names, f"Tabela {table} não foi criada")
        
        conn.close()
    
    def test_adicionar_item(self):
        """Testa a adição de itens ao inventário"""
        # Dados de teste
        item = {
            'nome': 'Leite',
            'categoria': 'Laticínios',
            'quantidade': 1.0,
            'unidade': 'litro',
            'data_validade': date.today() + timedelta(days=7),
            'local': 'Geladeira – Inferior',
            'data_compra': date.today(),
            'preco': 4.99,
            'thomas_safe': True,
            'contem_leite': True
        }
        
        # Adicionar o item
        item_id = self.db_manager.adicionar_item(
            nome=item['nome'],
            categoria=item['categoria'],
            quantidade=item['quantidade'],
            unidade=item['unidade'],
            validade=item['data_validade'],
            localizacao=item['local'],
            custo_unitario=item.get('preco', 0.0),
            para_thomas=item.get('thomas_safe', False),
            contem_leite=item.get('contem_leite', False)
        )
        
        # Verificar se o item foi adicionado com sucesso
        self.assertGreater(item_id, 0, "Item não foi adicionado corretamente")
        
        # Verificar se o item pode ser recuperado
        items = self.db_manager.carregar_inventario()
        self.assertEqual(len(items), 1, "Inventário deveria ter 1 item")
        self.assertEqual(items.iloc[0]['nome'], 'Leite', "Nome do item não corresponde")
    
    def test_registrar_consumo(self):
        """Testa o registro de consumo de itens"""
        # Adicionar um item de teste
        item_id = self.db_manager.adicionar_item(
            nome="Maçã",
            categoria="Frutas",
            quantidade=5.0,
            unidade="unidade",
            validade=date.today() + timedelta(days=10),
            localizacao="Fruteira",
            custo_unitario=2.50,
            para_thomas=True,
            contem_leite=False
        )
        
        # Verificar quantidade inicial
        items = self.db_manager.carregar_inventario()
        self.assertEqual(items.iloc[0]['quantidade'], 5.0, "Quantidade inicial deve ser 5.0")
        
        # Registrar consumo do item
        consumo_id = self.db_manager.registrar_consumo(item_id, 2.0, date.today(), True)
        self.assertGreater(consumo_id, 0, "Consumo não foi registrado corretamente")
        
        # Verificar se a quantidade foi atualizada no banco
        items = self.db_manager.carregar_inventario()
        self.assertEqual(items.iloc[0]['quantidade'], 3.0, "Quantidade não foi atualizada corretamente")
    
    def test_atualizar_item(self):
        """Testa a atualização de itens no inventário"""
        # Adicionar um item de teste
        item_id = self.db_manager.adicionar_item(
            nome="Queijo",
            categoria="Laticínios",
            quantidade=2.0,
            unidade="kg",
            validade=date.today() + timedelta(days=15),
            localizacao="Geladeira - Superior",
            custo_unitario=30.0,
            para_thomas=False,
            contem_leite=True
        )
        
        # Atualizar o item
        nova_validade = date.today() + timedelta(days=20)
        self.db_manager.atualizar_item(
            item_id=item_id,
            nome="Queijo Prato",
            categoria="Laticínios",
            quantidade=1.5,
            unidade="kg",
            validade=nova_validade,
            localizacao="Geladeira - Superior",
            custo_unitario=35.0,
            para_thomas=False,
            contem_leite=True
        )
        
        # Verificar se as alterações foram salvas
        items = self.db_manager.carregar_inventario()
        self.assertEqual(items.iloc[0]['nome'], "Queijo Prato", "Nome não foi atualizado")
        self.assertEqual(items.iloc[0]['quantidade'], 1.5, "Quantidade não foi atualizada")
        self.assertEqual(items.iloc[0]['custo_unitario'], 35.0, "Preço não foi atualizado")
    
    def test_excluir_item(self):
        """Testa a exclusão de itens do inventário"""
        # Adicionar um item de teste
        item_id = self.db_manager.adicionar_item(
            nome="Item para excluir",
            categoria="Teste",
            quantidade=1.0,
            unidade="unidade",
            validade=date.today(),
            localizacao="Teste",
            custo_unitario=1.0,
            para_thomas=False,
            contem_leite=False
        )
        
        # Verificar se o item existe
        items = self.db_manager.carregar_inventario()
        self.assertEqual(len(items), 1, "Item deveria existir antes da exclusão")
        
        # Excluir o item
        self.db_manager.excluir_item(item_id)
        
        # Verificar se o item foi excluído
        items = self.db_manager.carregar_inventario()
        self.assertEqual(len(items), 0, "Item não foi excluído corretamente")
    
    def test_consumo_erro(self):
        """Testa o tratamento de erro ao tentar consumir mais que o disponível"""
        # Adicionar um item de teste
        item_id = self.db_manager.adicionar_item(
            nome="Iogurte",
            categoria="Laticínios",
            quantidade=1.0,
            unidade="unidade",
            validade=date.today() + timedelta(days=5),
            localizacao="Geladeira",
            custo_unitario=3.0,
            para_thomas=True,
            contem_leite=True
        )
        
        # Tentar consumir mais do que existe
        with self.assertRaises(Exception):
            self.db_manager.registrar_consumo(item_id, 2.0, date.today(), True)
            
        # Verificar que a quantidade original não foi alterada
        items = self.db_manager.carregar_inventario()
        self.assertEqual(items.iloc[0]['quantidade'], 1.0, "Quantidade não deveria ser alterada")
    
    def test_error_handler(self):
        """Testa o manipulador de erros do banco de dados"""
        # Criar uma conexão para testar
        conn = sqlite3.connect(self.temp_db_path)
        
        # Testar verificação de integridade
        result, message = DatabaseErrorHandler.verify_database_integrity(conn)
        self.assertTrue(result, f"Verificação de integridade falhou: {message}")
        
        # Testar otimização
        result = DatabaseErrorHandler.optimize_database(conn)
        self.assertTrue(result, "Otimização do banco falhou")
        
        conn.close()

if __name__ == '__main__':
    unittest.main()
