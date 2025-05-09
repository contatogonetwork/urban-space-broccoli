from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv, find_dotenv
import os
import datetime

# Carregar variáveis de ambiente do arquivo .env
load_dotenv(find_dotenv())

# Diretórios do projeto
ROOT_DIR = Path(__file__).parent.absolute()
DATA_DIR = ROOT_DIR / "data"
DB_DIR = ROOT_DIR / "db"

# Garantir que os diretórios existam
DATA_DIR.mkdir(exist_ok=True)
DB_DIR.mkdir(exist_ok=True)

# Configurações da aplicação
PAGE_TITLE = os.getenv("PAGE_TITLE", "GELADEIRA - Sistema de Gerenciamento de Alimentos")
PAGE_LAYOUT = os.getenv("PAGE_LAYOUT", "wide")
INITIAL_SIDEBAR_STATE = os.getenv("INITIAL_SIDEBAR_STATE", "expanded")

# Caminho para o banco de dados
DB_PATH = os.getenv("DB_PATH", str(DB_DIR / "geladeira.db"))

# Funções utilitárias
def get_current_datetime():
    """Retorna a data e hora atual formatada"""
    return datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

def get_current_user():
    """Retorna o usuário atual configurado ou um padrão"""
    return os.getenv("APP_USER", "Admin")

def load_config() -> Dict[str, Any]:
    """Carrega configurações da aplicação"""
    # Valores padrão
    config = {
        "tema": 2,  # 0=Claro, 1=Escuro, 2=Sistema
        "mostrar_alertas_inicio": True,
        "dias_alerta_vencimento": 7,
        "nivel_alerta_quantidade": 20,
        "idade_thomas": 24,  # Em meses
        "peso_thomas": 12.0   # Em kg
    }
    
    # Sobrescrever com variáveis de ambiente, se existirem
    if os.getenv("TEMA"):
        config["tema"] = int(os.getenv("TEMA"))
    if os.getenv("MOSTRAR_ALERTAS"):
        config["mostrar_alertas_inicio"] = os.getenv("MOSTRAR_ALERTAS").lower() == "true"
    if os.getenv("DIAS_ALERTA"):
        config["dias_alerta_vencimento"] = int(os.getenv("DIAS_ALERTA"))
    if os.getenv("NIVEL_ALERTA"):
        config["nivel_alerta_quantidade"] = int(os.getenv("NIVEL_ALERTA"))
    if os.getenv("IDADE_THOMAS"):
        config["idade_thomas"] = int(os.getenv("IDADE_THOMAS"))
    if os.getenv("PESO_THOMAS"):
        config["peso_thomas"] = float(os.getenv("PESO_THOMAS"))
        
    return config