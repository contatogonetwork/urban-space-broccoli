import requests
import pandas as pd
import time
import json
import os
import traceback
from typing import Dict, Any, Optional, List, Tuple

class IntegracaoAlimentos:
    """
    Classe para integração com APIs de informações nutricionais
    """
    
    def __init__(self):
        self.cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        self.cache_file = os.path.join(self.cache_dir, "alimentos_cache.json")
        self._load_cache()
    
    def _load_cache(self):
        """Carrega o cache de um arquivo JSON"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
            else:
                self.cache = {}
        except Exception as e:
            print(f"Erro ao carregar cache: {e}")
            self.cache = {}
    
    def _save_cache(self):
        """Salva o cache em um arquivo JSON"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erro ao salvar cache: {e}")
    
    def buscar_info_nutricional(self, nome_produto: str) -> Dict[str, Any]:
        """
        Busca informações nutricionais de um produto pelo nome
        
        Args:
            nome_produto: Nome do produto para busca
            
        Returns:
            dict: Informações nutricionais ou dicionário vazio se não encontrado
        """
        # Verifica se está no cache
        if nome_produto in self.cache:
            return self.cache[nome_produto]
        
        try:
            # Primeiro método: Open Food Facts
            info = self._buscar_openfoodfacts(nome_produto)
            if info and info.get("encontrado", False):
                self.cache[nome_produto] = info
                self._save_cache()
                return info
            
            # Segundo método: TACO (Tabela Brasileira de Composição de Alimentos)
            info = self._buscar_taco(nome_produto)
            if info and info.get("encontrado", False):
                self.cache[nome_produto] = info
                self._save_cache()
                return info
                
            # Nenhum resultado encontrado
            return {"encontrado": False}
        except Exception as e:
            traceback.print_exc()
            return {"encontrado": False, "erro": str(e)}
    
    def _buscar_openfoodfacts(self, nome_produto: str) -> Dict[str, Any]:
        """
        Busca no Open Food Facts
        """
        try:
            # Usando a API do Open Food Facts
            url = f"https://world.openfoodfacts.org/cgi/search.pl"
            params = {
                "search_terms": nome_produto,
                "search_simple": 1,
                "action": "process",
                "json": 1,
                "page_size": 1
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if data["count"] > 0:
                product = data["products"][0]
                nutriments = product.get("nutriments", {})
                
                return {
                    "encontrado": True,
                    "nome": product.get("product_name", nome_produto),
                    "marca": product.get("brands", ""),
                    "calorias": nutriments.get("energy-kcal_100g", 0),
                    "proteinas": nutriments.get("proteins_100g", 0),
                    "carboidratos": nutriments.get("carbohydrates_100g", 0),
                    "gorduras": nutriments.get("fat_100g", 0),
                    "fibras": nutriments.get("fiber_100g", 0),
                    "acucar": nutriments.get("sugars_100g", 0),
                    "sodio": nutriments.get("sodium_100g", 0) * 1000,  # converter para mg
                    "calcio": nutriments.get("calcium_100g", 0) * 1000,  # converter para mg
                    "ferro": nutriments.get("iron_100g", 0) * 1000,  # converter para mg
                    "vitamina_c": nutriments.get("vitamin-c_100g", 0) * 1000,  # converter para mg
                    "contem_leite": any(allergen.lower() in ["milk", "leite"] 
                                        for allergen in product.get("allergens_tags", []))
                }
            return {"encontrado": False}
        except Exception as e:
            print(f"Erro ao buscar OpenFoodFacts: {e}")
            return {"encontrado": False, "erro": str(e)}
    
    def _buscar_taco(self, nome_produto: str) -> Dict[str, Any]:
        """
        Busca na base TACO (implementação simulada, em produção usaria uma API real)
        """
        try:
            # Simular busca na base TACO com alguns alimentos comuns
            base_taco = {
                "arroz": {"calorias": 128, "proteinas": 2.5, "carboidratos": 28.1, 
                         "gorduras": 0.2, "calcio": 4, "ferro": 0.3, "vitamina_c": 0},
                "feijão": {"calorias": 76, "proteinas": 4.8, "carboidratos": 13.6, 
                          "gorduras": 0.5, "calcio": 27, "ferro": 1.5, "vitamina_c": 0},
                "leite": {"calorias": 61, "proteinas": 3.2, "carboidratos": 4.7, 
                         "gorduras": 3.3, "calcio": 123, "ferro": 0.1, "vitamina_c": 1.5, 
                         "contem_leite": True},
                "banana": {"calorias": 89, "proteinas": 1.1, "carboidratos": 22.8, 
                          "gorduras": 0.1, "calcio": 6, "ferro": 0.4, "vitamina_c": 21.6},
                "carne": {"calorias": 219, "proteinas": 26.7, "carboidratos": 0, 
                         "gorduras": 13, "calcio": 9, "ferro": 3.4, "vitamina_c": 0}
            }
            
            # Procurar na base de alimentos
            for key, dados in base_taco.items():
                if key in nome_produto.lower():
                    dados["encontrado"] = True
                    dados["nome"] = nome_produto
                    if "contem_leite" not in dados:
                        dados["contem_leite"] = False
                    return dados
            
            return {"encontrado": False}
            
        except Exception as e:
            print(f"Erro ao buscar TACO: {e}")
            return {"encontrado": False, "erro": str(e)}
    
    def analisar_ingredientes(self, ingredientes_texto: str) -> Dict[str, Any]:
        """
        Analisa a lista de ingredientes para identificar alergênicos
        
        Args:
            ingredientes_texto: Texto com ingredientes separados por vírgula
            
        Returns:
            dict: Análise dos ingredientes
        """
        try:
            # Lista de ingredientes alérgicos comuns
            alergenos = {
                "leite": ["leite", "lactose", "caseína", "whey", "manteiga", "queijo", "iogurte"],
                "glúten": ["trigo", "gluten", "cevada", "centeio", "aveia", "malte"],
                "soja": ["soja", "lecitina de soja", "proteína de soja"],
                "frutos do mar": ["peixe", "camarão", "lagosta", "caranguejo", "mariscos", "frutos do mar"],
                "nozes": ["amendoim", "nozes", "castanha", "avelã", "macadâmia", "pistache", "amêndoas"]
            }
            
            ingredientes = [ing.strip().lower() for ing in ingredientes_texto.split(',')]
            alergenos_encontrados = {}
            
            # Para cada tipo de alérgeno, verificar se algum item da lista está nos ingredientes
            for tipo, lista in alergenos.items():
                encontrados = []
                for ingrediente in ingredientes:
                    if any(alerg in ingrediente for alerg in lista):
                        encontrados.append(ingrediente)
                
                if encontrados:
                    alergenos_encontrados[tipo] = encontrados
            
            # Analisar aditivos artificiais
            aditivos = []
            for ingrediente in ingredientes:
                # Identificar corantes, conservantes e adoçantes artificiais por padrões comuns
                if any(palavra in ingrediente for palavra in ["corante", "artificial", "conservante", 
                                                               "ácido", "nitrito", "nitrato", "benzoato", 
                                                               "sorbato", "adoçante", "aspartame", 
                                                               "sacarina", "glutamato"]):
                    aditivos.append(ingrediente)
            
            return {
                "alergenos": alergenos_encontrados,
                "contem_leite": any(alerg in ["leite"] for alerg in alergenos_encontrados.keys()),
                "contem_gluten": any(alerg in ["glúten"] for alerg in alergenos_encontrados.keys()),
                "aditivos": aditivos,
                "ingredientes_processados": len(aditivos) > 0
            }
            
        except Exception as e:
            print(f"Erro ao analisar ingredientes: {e}")
            return {
                "alergenos": {},
                "aditivos": [],
                "erro": str(e)
            }
