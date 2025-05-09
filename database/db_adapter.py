import pandas as pd
import datetime
import logging
from utils.nutrition import registrar_nutrientes_consumidos as registrar_nutrientes_util

logger = logging.getLogger(__name__)

class DatabaseAdapter:
    """Classe adaptadora para funções de banco de dados"""
    def __init__(self, db_connection):
        self.db = db_connection

    def registrar_nutrientes_consumidos(self, item_id, quantidade, para_thomas=False, data=None):
        """
        Registra os nutrientes consumidos para análise nutricional posterior
        """
        try:
            return registrar_nutrientes_util(self.db, item_id, quantidade, para_thomas, data)
        except Exception as e:
            logger.exception("Erro ao registrar nutrientes consumidos via adapter")
            return False, f"Erro ao registrar nutrientes consumidos: {str(e)}"
    
    def _verificar_deficiencias_nutricionais(self, para_thomas=False):
        """
        Verifica deficiências nutricionais com base no consumo recente
        e cria alertas nutricionais se necessário
        """
        try:
            # Obter consumo dos últimos 7 dias
            df_nutrientes = self.db.obter_nutrientes_consumidos(
                apenas_thomas=para_thomas, 
                periodo_dias=7
            )
            
            if df_nutrientes.empty:
                return
                
            # Obter necessidades nutricionais
            necessidades = self.db.obter_necessidades_thomas() if para_thomas else []
            
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
            if deficiencias:
                for def_item in deficiencias:
                    # Verificar se já existe um alerta recente para este nutriente
                    # Se não existir, criar um novo
                    self.db.criar_alerta_nutricional(
                        nutriente=def_item["nutriente"],
                        percentual=def_item["percentual"],
                        para_thomas=para_thomas
                    )
            
        except Exception as e:
            logger.exception("Erro ao verificar deficiências nutricionais")
