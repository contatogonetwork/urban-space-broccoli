import unittest
import pandas as pd
import json
import os
import tempfile
from unittest.mock import patch, MagicMock
from pathlib import Path

from utils.assistente import sugerir_receitas, gerar_lista_compras_para_receitas
from views.receitas import mostrar_receitas

class TestReceitas(unittest.TestCase):
    """Testes para as funcionalidades de receitas"""
    
    def setUp(self):
        """Configuração para cada teste"""
        # Criar dados de teste para o inventário
        self.test_inventory = pd.DataFrame({
            'id': [1, 2, 3, 4, 5],
            'nome': ['Ovos', 'Farinha de Trigo', 'Leite', 'Açúcar', 'Manteiga'],
            'categoria': ['Ovos', 'Grãos', 'Laticínios', 'Condimentos', 'Laticínios'],
            'quantidade': [6, 500, 1, 200, 100],
            'unidade': ['unidade', 'g', 'l', 'g', 'g'],
            'data_validade': ['2023-12-31', '2023-12-31', '2023-12-15', '2024-01-31', '2023-12-20'],
            'local': ['Geladeira – Superior'] * 5,
            'thomas_safe': [True, True, False, True, False]
        })
        
        # Criar arquivo temporário para receitas
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_recipe_file = Path(self.temp_dir.name) / 'test_recipes.json'
        
        # Criar algumas receitas de teste
        self.test_recipes = [
            {
                "titulo": "Panquecas Simples",
                "ingredientes": ["Ovos", "Farinha de Trigo", "Leite", "Açúcar"],
                "ingredientes_quantidades": {"Ovos": 2, "Farinha de Trigo": 200, "Leite": 0.5, "Açúcar": 20},
                "instrucoes": "1. Misture todos os ingredientes\n2. Aqueça uma frigideira\n3. Despeje a massa\n4. Vire quando dourar",
                "tempo_preparo": 20,
                "porcoes": 4,
                "thomas_safe": False
            },
            {
                "titulo": "Bolo de Baunilha",
                "ingredientes": ["Ovos", "Farinha de Trigo", "Açúcar", "Manteiga", "Fermento"],
                "ingredientes_quantidades": {"Ovos": 3, "Farinha de Trigo": 300, "Açúcar": 150, "Manteiga": 100, "Fermento": 10},
                "instrucoes": "1. Bata os ovos com açúcar\n2. Adicione manteiga\n3. Misture farinha e fermento\n4. Asse por 30 min",
                "tempo_preparo": 60,
                "porcoes": 8,
                "thomas_safe": False
            }
        ]
        
        # Salvar receitas no arquivo temporário
        with open(self.test_recipe_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_recipes, f)
    
    def tearDown(self):
        """Limpeza após cada teste"""
        self.temp_dir.cleanup()
    
    @patch('utils.assistente.os.path.exists')
    @patch('utils.assistente.json.load')
    def test_sugerir_receitas(self, mock_json_load, mock_path_exists):
        """Testa a sugestão de receitas baseada no inventário"""
        # Configurar mocks
        mock_path_exists.return_value = True
        mock_json_load.return_value = self.test_recipes
        
        # Chamar a função sendo testada
        receitas_sugeridas = sugerir_receitas(self.test_inventory)
        
        # Verificar se encontrou duas receitas
        self.assertEqual(len(receitas_sugeridas), 2, "Deveria sugerir duas receitas")
        
        # Verificar se identificou corretamente os ingredientes que temos
        panquecas = receitas_sugeridas[0]
        self.assertEqual(set(panquecas.get('ingredientes_usados')), 
                        set(['Ovos', 'Farinha de Trigo', 'Leite', 'Açúcar']),
                        "Identificou incorretamente os ingredientes disponíveis")
        
        # Verificar se identificou corretamente os ingredientes faltantes
        bolo = receitas_sugeridas[1]
        self.assertIn('Fermento', bolo.get('ingredientes_faltantes', []),
                     "Não identificou corretamente os ingredientes faltantes")
    
    def test_gerar_lista_compras(self):
        """Testa a geração de lista de compras para receitas"""
        # Preparar dados de teste
        receitas = [
            {
                "titulo": "Panquecas Simples",
                "ingredientes_usados": ["Ovos", "Farinha de Trigo"],
                "ingredientes_faltantes": ["Fermento"],
                "ingredientes_quantidades": {"Ovos": 2, "Farinha de Trigo": 200, "Fermento": 10}
            }
        ]
        
        # Chamar a função sendo testada
        lista_compras = gerar_lista_compras_para_receitas(receitas, self.test_inventory)
        
        # Verificar se a lista de compras contém o item faltante
        self.assertEqual(len(lista_compras), 1, "Deveria ter 1 item na lista de compras")
        self.assertEqual(lista_compras[0]['nome'], 'Fermento', "O item faltante deveria ser Fermento")
        self.assertEqual(lista_compras[0]['quantidade'], 10, "A quantidade não corresponde")
        self.assertEqual(lista_compras[0]['receitas'], ['Panquecas Simples'], 
                         "A receita associada não corresponde")

if __name__ == '__main__':
    unittest.main()
