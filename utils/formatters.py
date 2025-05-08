import pandas as pd
import datetime

# Formatações para valores booleanos
def format_thomas_status(val):
    """Formata o status para Thomas como emoji"""
    if val:
        return "✅"
    return ""

def format_leite_status(val):
    """Formata o status de leite como emoji"""
    if val:
        return "🥛"
    return ""

def format_compatibilidade(val):
    """Formata o nível de compatibilidade como emoji"""
    if val == 3:
        return "🟢"  # Seguro
    elif val == 2:
        return "🟡"  # Verificar
    elif val == 1:
        return "🔴"  # Não recomendado
    return "❓"     # Desconhecido

# Formatações para células destacadas
def highlight_expiration(val):
    """Estiliza células de validade baseado nos dias restantes"""
    if pd.isna(val):
        return ""
    
    # Se for negativo, já venceu
    if val < 0:
        return 'background-color: #ffcccc; color: #cc0000; font-weight: bold'
    # Se for menos de 7 dias, está perto de vencer
    elif val < 7:
        return 'background-color: #fff4cc; color: #806600'
    # Senão, está bom
    return ''
    
def highlight_quantity(val):
    """Estiliza células de quantidade com base no valor"""
    if pd.isna(val):
        return ""
    
    # Quase acabando
    if val < 1:
        return 'background-color: #ffcccc; color: #cc0000; font-weight: bold'
    # Pouca quantidade
    elif val < 3:
        return 'background-color: #fff4cc; color: #806600'
    # Quantidade boa
    return ''
    
def highlight_health(val):
    """Estiliza células de nível de saúde"""
    if pd.isna(val):
        return ""
    
    if val == 1:  # Saudável
        return 'background-color: #d5f5d5; color: #1e6f50'
    elif val == 2:  # Intermediário
        return 'background-color: #fff4cc; color: #806600'
    elif val == 3:  # Alto impacto
        return 'background-color: #ffcccc; color: #cc0000'
    return ""

# Nova função para formatação de tendência de preço
def format_tendencia_preco(val):
    """Formata o indicador de tendência de preço"""
    if pd.isna(val):
        return "➖"
    if val == 1:  # Alta
        return "🔺"
    elif val == -1:  # Baixa
        return "🔽"
    else:  # Na média
        return "➖"

# Nova função para destacar posição de preço
def highlight_price_position(val):
    """Estiliza células de posição de preço em relação à média"""
    if pd.isna(val):
        return ""
    if val > 5:
        return 'background-color: #ffcccc; color: #cc0000; font-weight: bold'
    elif val < -5:
        return 'background-color: #d5f5d5; color: #1e6f50'
    else:
        return 'background-color: #fff4cc; color: #806600'