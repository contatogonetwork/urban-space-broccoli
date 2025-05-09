"""
Módulo Assistente Residencial Inteligente
Funções para automação, sugestões, previsão, relatórios e gamificação.
"""
import pandas as pd
import datetime
import requests
import os
from typing import List, Dict, Any
import json
import random

# 1. Resumo Semanal Automático
def gerar_resumo_semanal(db) -> Dict[str, Any]:
    """
    Gera um resumo semanal com:
    - Itens próximos do vencimento
    - Sugestões de compras
    - Consumo nutricional
    - Dicas de reaproveitamento
    """
    resumo = {}

    # Itens próximos do vencimento (próximos 7 dias)
    df = db.carregar_inventario()
    if not df.empty and "Validade" in df.columns:
        df["Dias Até Vencer"] = (pd.to_datetime(df["Validade"]).dt.date - datetime.date.today()).dt.days
        proximos = df[(df["Perecível"] == 1) & (df["Dias Até Vencer"] <= 7) & (df["Dias Até Vencer"] >= 0)]
        resumo["itens_proximos_vencimento"] = proximos[["Nome", "Dias Até Vencer", "Quantidade", "Unidade"]].to_dict(orient="records")
    else:
        resumo["itens_proximos_vencimento"] = []

    # Sugestões de compras (estoque baixo)
    if not df.empty and "Quantidade" in df.columns:
        estoque_baixo = df[df["Quantidade"] < 2]
        resumo["sugestoes_compras"] = estoque_baixo[["Nome", "Quantidade", "Unidade"]].to_dict(orient="records")
    else:
        resumo["sugestoes_compras"] = []

    # Consumo nutricional da semana (exemplo simplificado)
    try:
        consumo = db.obter_nutrientes_consumidos(periodo_dias=7)
        resumo["consumo_nutricional"] = consumo.to_dict(orient="records") if not consumo.empty else []
    except Exception:
        resumo["consumo_nutricional"] = []

    # Dicas de reaproveitamento (exemplo estático)
    resumo["dicas_reaproveitamento"] = [
        "Use talos e folhas em sopas e refogados.",
        "Congele frutas maduras para sucos ou vitaminas.",
        "Faça caldos com sobras de legumes."
    ]

    return resumo

# 2. Receitas Baseadas no Inventário
def sugerir_receitas(inventario: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Sugere receitas com base nos ingredientes disponíveis no inventário
    
    Args:
        inventario: DataFrame com itens do inventário
        
    Returns:
        Lista de receitas sugeridas
    """
    # Se inventário vazio, retorna lista vazia
    if inventario is None or inventario.empty:
        return []
    
    # Obter receitas do banco local baseado nos ingredientes disponíveis
    receitas_filtradas = []
    
    # Verificar se o inventário está vazio
    if not inventario.empty and "Nome" in inventario.columns:
        # Extrair ingredientes disponíveis
        ingredientes = inventario["Nome"].tolist()
        
        # Carregar receitas offline de um arquivo JSON
        try:
            receitas_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "receitas.json")
            if os.path.exists(receitas_path):
                with open(receitas_path, 'r', encoding='utf-8') as f:
                    receitas_offline = json.load(f)
            else:
                # Receitas padrão se arquivo não for encontrado
                receitas_offline = [
                    {
                        "titulo": "Omelete Simples",
                        "ingredientes_usados": ["ovo", "sal", "queijo"],
                        "ingredientes_faltantes": [],
                        "tempo_preparo": 10,
                        "porcoes": 1,
                        "instrucoes": "Bata os ovos, adicione sal a gosto. Aqueça uma frigideira com um fio de óleo, despeje os ovos batidos. Quando começar a firmar, adicione queijo ralado. Dobre ao meio e sirva.",
                        "imagem": "https://img.cybercook.com.br/receitas/776/omelete-simples-1.jpeg"
                    },
                    {
                        "titulo": "Salada Verde",
                        "ingredientes_usados": ["alface", "tomate", "cebola", "azeite"],
                        "ingredientes_faltantes": [],
                        "tempo_preparo": 5,
                        "porcoes": 2,
                        "instrucoes": "Lave e corte a alface. Corte o tomate em cubos e a cebola em rodelas finas. Misture tudo e tempere com azeite, sal e limão a gosto.",
                        "imagem": "https://img.cybercook.com.br/receitas/42/salada-verde-1.jpeg"
                    }
                ]
        except Exception as e:
            print(f"Erro ao carregar receitas: {e}")
            receitas_offline = []
        
        # Filtrar receitas com base nos ingredientes disponíveis
        for receita in receitas_offline:
            # Verificar se algum ingrediente da receita está no inventário
            for ing_usado in receita['ingredientes_usados']:
                if any(ing.lower() in ing_usado.lower() for ing in ingredientes):
                    receitas_filtradas.append(receita)
                    break
        
        # Se encontrou alguma receita correspondente, retorna-a
        if receitas_filtradas:
            return random.sample(receitas_filtradas, min(5, len(receitas_filtradas)))
    
    return []

def gerar_lista_compras_para_receitas(receitas: List[Dict[str, Any]], inventario: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Gera lista de compras complementar para as receitas sugeridas.
    
    Args:
        receitas: Lista de receitas retornadas por sugerir_receitas()
        inventario: DataFrame com itens do inventário
    
    Returns:
        Lista de itens faltantes para as receitas
    """
    # Lista de compras a ser retornada
    lista_compras = []
    
    # Verificar se o inventário está vazio
    if inventario.empty or "Nome" not in inventario.columns:
        # Se o inventário estiver vazio, retorna todos os ingredientes de todas as receitas
        for receita in receitas:
            for ingrediente in receita.get('ingredientes_usados', []):
                # Verificar se já está na lista
                if not any(item['nome'] == ingrediente for item in lista_compras):
                    lista_compras.append({
                        'nome': ingrediente,
                        'quantidade': 1,
                        'unidade': 'unidade',
                        'receitas': [receita['titulo']]
                    })
        return lista_compras
    
    # Extrair ingredientes disponíveis para comparação
    ingredientes_disponiveis = [nome.lower() for nome in inventario["Nome"].tolist()]
    
    # Para cada receita, verificar ingredientes faltantes
    for receita in receitas:
        for ingrediente in receita.get('ingredientes_usados', []):
            # Verificar se o ingrediente já está disponível
            if not any(ing in ingrediente.lower() for ing in ingredientes_disponiveis):
                # Verificar se já está na lista de compras
                item_existente = next((item for item in lista_compras if item['nome'] == ingrediente), None)
                
                if item_existente:
                    # Atualizar item existente
                    if receita['titulo'] not in item_existente['receitas']:
                        item_existente['receitas'].append(receita['titulo'])
                else:
                    # Adicionar novo item
                    lista_compras.append({
                        'nome': ingrediente,
                        'quantidade': 1,
                        'unidade': 'unidade',
                        'receitas': [receita['titulo']]
                    })
    
    return lista_compras

# 3. Cardápio Semanal Personalizado
def montar_cardapio_semanal(db, preferencias: Dict[str, Any]) -> Dict[str, Any]:
    """
    Monta cardápio semanal considerando restrições e necessidades nutricionais.
    """
    # TODO: Implementar lógica de cardápio personalizado
    pass

def restaurar_backup(backup_path: str, db_path: str):
    """
    Restaura banco de dados a partir de backup.
    """
    # TODO: Implementar restauração
    pass

# 8. Gamificação
def calcular_pontuacao(db) -> Dict[str, int]:
    """
    Calcula pontuação por economia, saúde e desperdício evitado.
    """
    # TODO: Implementar cálculo de pontos
    return {"economia": 0, "saude": 0, "desperdicio": 0}
