import pandas as pd
import datetime

def registrar_nutrientes_consumidos(db, item_id, quantidade, para_thomas=False, data=None):
    """
    Registra os nutrientes consumidos para análise nutricional posterior
    
    Args:
        db: Instância do banco de dados
        item_id: ID do item consumido
        quantidade: Quantidade consumida
        para_thomas: Indica se o consumo foi para Thomas
        data: Data do consumo (opcional)
    
    Returns:
        bool, str: Tupla com status (True/False) e mensagem
    """
    # Validação de parâmetros
    if not isinstance(item_id, int) or item_id <= 0:
        return False, "ID do item inválido."
    if not isinstance(quantidade, (int, float)) or quantidade <= 0:
        return False, "Quantidade consumida deve ser maior que zero."
    if data and not isinstance(data, (datetime.date, str)):
        return False, "Data inválida."
    try:
        # Usar data atual se não especificada
        if not data:
            data = datetime.date.today()
            
        # Obter dados do item
        item = db.carregar_item_por_id(item_id)
        if item is None or item.empty:
            return False, "Item não encontrado."
            
        # Lista de nutrientes a registrar
        nutrientes = [
            "Proteínas (g)", "Cálcio (mg)", "Vitamina D (mcg)", 
            "Ferro (mg)", "Vitamina C (mg)", "Calorias/100g"
        ]
        
        # Calcular valores de nutrientes consumidos
        nutrientes_valores = {}
        for nutriente in nutrientes:
            if nutriente in item.columns and pd.notna(item[nutriente].values[0]):
                # Valor do nutriente por 100g/ml multiplicado pela quantidade consumida
                valor = float(item[nutriente].values[0]) * quantidade / 100
                nutrientes_valores[nutriente] = valor
                
        if not nutrientes_valores:
            return False, "Nenhum nutriente registrado para este item."
        
        # Registrar na tabela de consumo de nutrientes
        registro_id = db._registrar_consumo_nutrientes(
            item_id=item_id, 
            nome_item=item["Nome"].values[0],
            data=data, 
            para_thomas=para_thomas,
            nutrientes=nutrientes_valores
        )
        
        # Verificar se há deficiências recorrentes
        verificar_deficiencias_nutricionais(db, para_thomas)
        
        return True, f"Nutrientes de {item['Nome'].values[0]} registrados com sucesso."
        
    except Exception as e:
        return False, f"Erro ao registrar nutrientes consumidos: {str(e)}"

def verificar_deficiencias_nutricionais(db, para_thomas=False):
    """
    Verifica deficiências nutricionais com base no consumo recente
    e cria alertas nutricionais se necessário
    
    Args:
        db: Instância do banco de dados
        para_thomas: Indica se a verificação é para Thomas
    """
    try:
        # Obter consumo dos últimos 7 dias
        df_nutrientes = db.obter_nutrientes_consumidos(
            apenas_thomas=para_thomas, 
            periodo_dias=7
        )
        
        if df_nutrientes is None or df_nutrientes.empty:
            return
                
        # Obter necessidades nutricionais
        necessidades = db.obter_necessidades_thomas() if para_thomas else []
        
        # Converter para dicionário para facilitar o acesso
        necessidades_dict = {n["nutriente"]: n["quantidade_diaria"] for n in necessidades}
        
        # Calcular médias diárias
        colunas_nutrientes = {
            "Proteínas (g)": "Proteínas",
            "Cálcio (mg)": "Cálcio", 
            "Ferro (mg)": "Ferro",
            "Vitamina D (mcg)": "Vitamina D",
            "Vitamina C (mg)": "Vitamina C"
        }
        
        deficiencias = []
        
        # Analisar cada nutriente
        for col, nome in colunas_nutrientes.items():
            if col in df_nutrientes.columns:
                media_diaria = df_nutrientes[col].mean()
                
                # Se temos uma referência de necessidade diária
                if nome in necessidades_dict and media_diaria > 0:
                    necessidade = necessidades_dict[nome]
                    percentual = (media_diaria / necessidade) * 100
                    
                    # Se está consumindo menos de 70% da necessidade, criar alerta
                    if percentual < 70:
                        deficiencias.append({
                            "nutriente": nome,
                            "consumo_medio": media_diaria,
                            "necessidade": necessidade,
                            "percentual": percentual
                        })
        
        # Criar alertas para deficiências encontradas
        if deficiencias and hasattr(db, 'criar_alerta_nutricional'):
            for def_item in deficiencias:
                db.criar_alerta_nutricional(
                    nutriente=def_item["nutriente"],
                    percentual=def_item["percentual"],
                    para_thomas=para_thomas
                )
            
    except Exception:
        pass

def calcular_necessidades_por_idade_peso(idade_meses, peso_kg):
    """
    Calcula necessidades nutricionais com base na idade e peso
    
    Args:
        idade_meses: Idade em meses
        peso_kg: Peso em kg
    
    Returns:
        dict: Dicionário com as necessidades nutricionais
    """
    # Validação de parâmetros
    if not isinstance(idade_meses, int) or idade_meses < 0:
        return {}
    if not isinstance(peso_kg, (int, float)) or peso_kg <= 0:
        return {}
    
    # Valores de referência por idade
    if idade_meses < 12:  # < 1 ano
        proteina_por_kg = 1.5
        calcio = 270
        ferro = 11
        vit_d = 10
        vit_c = 30
    elif idade_meses < 36:  # 1-3 anos
        proteina_por_kg = 1.1
        calcio = 500
        ferro = 7
        vit_d = 15
        vit_c = 15
    else:  # > 3 anos
        proteina_por_kg = 0.95
        calcio = 800
        ferro = 10
        vit_d = 15
        vit_c = 25
    
    # Cálculos baseados no peso
    proteina_total = proteina_por_kg * peso_kg
    
    return {
        "Proteínas": proteina_total,
        "Cálcio": calcio,
        "Ferro": ferro,
        "Vitamina D": vit_d,
        "Vitamina C": vit_c
    }
