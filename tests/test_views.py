from datetime import date, timedelta
from unittest.mock import patch, MagicMock, call
import unittest
import tempfile
import os
import pandas as pd

# Importar componentes a serem testados
from db.extended_database_manager import ExtendedDatabaseManager
from views import (
    mostrar_inventario_geral,
    mostrar_inventario_thomas,
    registrar_consumo
)

class TestViews(unittest.TestCase):
    """Testes para as funções de visualização"""
    
    def setUp(self):
        """Configuração para cada teste"""
        # Criar um banco de dados temporário para os testes
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix='.db')
        self.db_manager = ExtendedDatabaseManager(self.temp_db_path)
        self.db_manager.inicializar_banco()
        
        # Adicionar alguns dados de teste
        self._adicionar_dados_teste()
        
        # Mock para o streamlit com inicialização apropriada
        self.st_mock = MagicMock()
        self.st_mock.title_calls = []
        
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
                'data_compra': date.today(),
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
                validade=item.get('data_validade', None),
                localizacao=item['local'],
                custo_unitario=item.get('preco', 0.0),
                para_thomas=item.get('thomas_safe', False),
                contem_leite=item.get('lactose_free', False)
            )
    
    @patch('views.inventory.st')
    def test_mostrar_inventario_geral(self, mock_st):
        """Testa a visualização do inventário geral"""
        # Configurar mock
        mock_st.title = MagicMock()
        cols_mock = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        mock_st.columns.return_value = cols_mock
        
        # Chamar a função de visualização
        mostrar_inventario_geral(self.db_manager)
        
        # Verificar se o título foi exibido
        mock_st.title.assert_called_once()
        self.assertIn('Inventário', mock_st.title.call_args[0][0])
        
    @patch('views.thomas.st')
    def test_mostrar_inventario_thomas(self, mock_st):
        """Testa a visualização do inventário específico para Thomas"""
        # Configurar mock
        mock_st.title = MagicMock()
        cols_mock = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        mock_st.columns.return_value = cols_mock
        
        # Chamar a função de visualização
        mostrar_inventario_thomas(self.db_manager)
        
        # Verificar se o título foi exibido
        mock_st.title.assert_called_once()
        self.assertIn('Thomas', mock_st.title.call_args[0][0])
    
    @patch('views.consumption.st')
    def test_registrar_consumo(self, mock_st):
        """Testa o registro de consumo pela interface"""
        # Configurar mock com comportamento realista do Streamlit
        form_mock = MagicMock()
        mock_st.form.return_value.__enter__.return_value = form_mock
        
        # Simular seleção de item no selectbox
        items_df = self.db_manager.carregar_inventario()
        item_names = items_df['nome'].tolist()
        form_mock.selectbox.return_value = 'Maçã'  # Seleciona maçã
        
        # Simular entrada de quantidade e data
        form_mock.number_input.return_value = 2.0  # Quantidade consumida
        form_mock.date_input.return_value = date.today()
        
        # Simular envio do formulário
        form_mock.form_submit_button.return_value = True
        
        # Chamar a função de visualização
        registrar_consumo(self.db_manager)
        
        # Verificar se a quantidade foi atualizada no banco
        df = self.db_manager.carregar_inventario()
        maca_item = df[df['nome'] == 'Maçã'].iloc[0]
        self.assertEqual(maca_item['quantidade'], 3.0, "Quantidade de maçãs deveria ser 3 após consumo de 2")
        
        # Verificar se o formulário foi usado corretamente
        form_mock.selectbox.assert_called()
        form_mock.number_input.assert_called()
        form_mock.date_input.assert_called()
        form_mock.form_submit_button.assert_called()

if __name__ == '__main__':
    unittest.main()
