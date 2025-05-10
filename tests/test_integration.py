import unittest
import tempfile
import os
import pandas as pd
import sqlite3
from datetime import date, timedelta
from unittest.mock import patch

# Importações do sistema
from db.extended_database_manager import ExtendedDatabaseManager
from db.error_handler import DatabaseErrorHandler
import utils.constants as constants

class TestSystemIntegration(unittest.TestCase):
    """Testes de integração do sistema completo"""
    
    def setUp(self):
        """Configuração para cada teste"""
        # Criar um banco de dados temporário para os testes
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix='.db')
        self.db_manager = ExtendedDatabaseManager(self.temp_db_path)
        
        # Inicializar o banco com dados de teste
        self.db_manager.inicializar_banco()
        self._adicionar_dados_teste()
    
    def tearDown(self):
        """Limpeza após cada teste"""
        self.db_manager.fechar()
        os.close(self.temp_db_fd)
        os.unlink(self.temp_db_path)
    
    def _adicionar_dados_teste(self):
        """Adiciona dados de teste ao banco"""
        # Adicionar alguns items ao inventário
        items = [
            {
                'nome': 'Leite',
                'categoria': 'Laticínios',
                'quantidade': 1.0,
                'unidade': 'litro',
                'data_validade': date.today() + timedelta(days=7),
                'local': 'Geladeira – Inferior',
                'data_compra': date.today(),
                'preco': 4.99,
                'thomas_safe': False,
                'lactose_free': False
            },
            {
                'nome': 'Maçã',
                'categoria': 'Frutas',
                'quantidade': 5.0,
                'unidade': 'unidade',
                'data_validade': date.today() + timedelta(days=10),
                'local': 'Fruteira',
                'data_compra': date.today(),
                'preco': 2.50,
                'thomas_safe': True,
                'lactose_free': True
            },
            {
                'nome': 'Pão',
                'categoria': 'Padaria',
                'quantidade': 1.0,
                'unidade': 'unidade',
                'data_validade': date.today() + timedelta(days=3),
                'local': 'Armário',
                'data_compra': date.today() - timedelta(days=1),
                'preco': 7.50,
                'thomas_safe': True,
                'lactose_free': True
            }
        ]
        
        for item in items:
            self.db_manager.adicionar_item(
                nome=item['nome'],
                categoria=item['categoria'],
                quantidade=item['quantidade'],
                unidade=item['unidade'],
                validade=item['data_validade'],  # Corrigido: usando data_validade 
                localizacao=item['local'],
                custo_unitario=item.get('preco', 0.0),
                para_thomas=item.get('thomas_safe', False),
                contem_leite=not item.get('lactose_free', False)  # Corrigido: invertendo a lógica
            )
    
    def test_fluxo_principal(self):
        """Testa o fluxo principal do sistema - teste integrado"""
        # 1. Verificar se os itens iniciais estão no inventário
        df = self.db_manager.carregar_inventario()
        self.assertEqual(len(df), 3, "Deveria ter 3 itens no inventário")
        
        # 2. Registrar consumo de um item
        item_id = df[df['nome'] == 'Maçã'].iloc[0]['id']
        consumo_id = self.db_manager.registrar_consumo(item_id, 2.0, date.today(), False)
        self.assertGreater(consumo_id, 0, "Deveria registrar o consumo com sucesso")
        
        # 3. Verificar se a quantidade foi atualizada
        df = self.db_manager.carregar_inventario()
        self.assertEqual(df[df['nome'] == 'Maçã'].iloc[0]['quantidade'], 3.0, 
                         "A quantidade de maçãs deveria ser 3 após o consumo")
        
        # 4. Adicionar um novo item
        novo_item = {
            'nome': 'Arroz',
            'categoria': 'Grãos',
            'quantidade': 5.0,
            'unidade': 'kg',
            'data_validade': date.today() + timedelta(days=180),
            'local': 'Armário',
            'data_compra': date.today(),
            'preco': 22.50,
            'thomas_safe': True,
            'lactose_free': True
        }
        
        item_id = self.db_manager.adicionar_item(
            nome=novo_item['nome'],
            categoria=novo_item['categoria'],
            quantidade=novo_item['quantidade'],
            unidade=novo_item['unidade'],
            validade=novo_item['data_validade'],  # Corrigido
            localizacao=novo_item['local'],
            custo_unitario=novo_item.get('preco', 0.0),
            para_thomas=novo_item.get('thomas_safe', False),
            contem_leite=not novo_item.get('lactose_free', False)  # Corrigido: invertendo a lógica
        )
        self.assertGreater(item_id, 0, "Deveria adicionar o novo item com sucesso")
        
        # 5. Verificar se o novo item está no inventário
        df = self.db_manager.carregar_inventario()
        self.assertEqual(len(df), 4, "Deveria ter 4 itens no inventário após adicionar arroz")
        self.assertIn('Arroz', df['nome'].values, "Arroz deveria estar no inventário")
        
        # 6. Testar a filtragem por itens seguros para Thomas
        thomas_items = df[df['thomas_safe'] == True]
        self.assertEqual(len(thomas_items), 3, "Deveria ter 3 itens seguros para Thomas")
        self.assertNotIn('Leite', thomas_items['nome'].values, 
                         "Leite não deveria estar nos itens seguros para Thomas")
        
        # 7. Testar a obtenção de alertas de validade próxima
        alertas = self.db_manager.obter_alertas_validade(dias_limite=5)
        self.assertEqual(len(alertas), 1, "Deveria ter 1 alerta de validade próxima")
        self.assertEqual(alertas.iloc[0]['nome'], 'Pão', 
                         "Pão deveria estar com validade próxima")
        
        # 8. Verificar se as constantes do sistema estão disponíveis corretamente
        self.assertIn('Laticínios', constants.CATEGORIAS_ALIMENTOS, 
                      "Categorias de alimentos devem incluir Laticínios")
        self.assertIn('leite', constants.TERMOS_LACTEOS, 
                      "Termos lácteos devem incluir 'leite'")

    def test_recuperacao_erro(self):
        """Testa a funcionalidade de recuperação de erros do banco de dados"""
        # 1. Fechar o banco antes de executar os testes
        self.db_manager.fechar()
        
        # 2. Conectar diretamente ao banco para testar os manipuladores de erro
        conn = sqlite3.connect(self.temp_db_path)
        
        # 3. Verificar integridade
        result, message = DatabaseErrorHandler.verify_database_integrity(conn)
        self.assertTrue(result, f"Verificação de integridade falhou: {message}")
        
        # 4. Otimizar banco
        result = DatabaseErrorHandler.optimize_database(conn)
        self.assertTrue(result, "Otimização falhou")
        conn.close()
        
        # 5. Reabrir banco e verificar dados
        self.db_manager = ExtendedDatabaseManager(self.temp_db_path)
        df = self.db_manager.carregar_inventario()
        self.assertEqual(len(df), 3, "Deveria ainda ter 3 itens após recuperação")

if __name__ == '__main__':
    unittest.main()
