from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv, find_dotenv
import os
import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Importar constantes relevantes
try:
    from utils.constants import NIVEL_ALERTA_VENCIMENTO, NIVEL_ALERTA_QUANTIDADE
except ImportError:
    logger.warning("Constants module not found. Using default values.")
    NIVEL_ALERTA_VENCIMENTO = 7  # Default: 7 days
    NIVEL_ALERTA_QUANTIDADE = 20  # Default: 20%

# Carregar variáveis de ambiente do arquivo .env
env_path = find_dotenv()
if env_path:
    load_dotenv(env_path)
    logger.info(f"Environment variables loaded from {env_path}")
else:
    logger.warning("No .env file found")

# Diretórios do projeto
ROOT_DIR = Path(__file__).parent.absolute()
DATA_DIR = ROOT_DIR / "data"
DB_DIR = ROOT_DIR / "db"

# Garantir que os diretórios existam
try:
    DATA_DIR.mkdir(exist_ok=True)
    DB_DIR.mkdir(exist_ok=True)
    logger.info("Project directories verified")
except PermissionError:
    logger.error("Permission denied when creating directories")
except Exception as e:
    logger.error(f"Error creating directories: {str(e)}")

# Configurações da aplicação
PAGE_TITLE = os.getenv("PAGE_TITLE", "GELADEIRA - Sistema de Gerenciamento de Alimentos")
PAGE_LAYOUT = os.getenv("PAGE_LAYOUT", "wide")
INITIAL_SIDEBAR_STATE = os.getenv("INITIAL_SIDEBAR_STATE", "expanded")

# Caminho para o banco de dados
DB_PATH = Path(os.getenv("DB_PATH", str(DB_DIR / "geladeira.db")))

# Funções utilitárias
def get_current_datetime() -> str:
    """Retorna a data e hora atual formatada"""
    return datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

def get_current_user() -> str:
    """Retorna o usuário atual configurado ou um padrão"""
    return os.getenv("APP_USER", "Admin")

def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Validates configuration values and sets defaults if invalid"""
    if not isinstance(config["tema"], int) or config["tema"] not in [0, 1, 2]:
        logger.warning("Invalid tema value, setting default (2)")
        config["tema"] = 2
    
    if not isinstance(config["mostrar_alertas_inicio"], bool):
        logger.warning("Invalid mostrar_alertas_inicio value, setting default (True)")
        config["mostrar_alertas_inicio"] = True
    
    return config

def load_config() -> Dict[str, Any]:
    """Carrega configurações da aplicação"""
    # Valores padrão
    config = {
        "tema": 2,  # 0=Claro, 1=Escuro, 2=Sistema
        "mostrar_alertas_inicio": True,
        "dias_alerta_vencimento": NIVEL_ALERTA_VENCIMENTO,
        "nivel_alerta_quantidade": NIVEL_ALERTA_QUANTIDADE,
        "idade_thomas": 24,  # Em meses
        "peso_thomas": 12.0   # Em kg
    }
    
    # Sobrescrever com variáveis de ambiente, se existirem
    try:
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
    except (ValueError, TypeError) as e:
        logger.error(f"Error loading environment variables: {str(e)}")
    
    return validate_config(config)

# Initialize configuration
app_config = load_config()