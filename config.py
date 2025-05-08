import os
from dotenv import load_dotenv
import datetime

# Carregar variáveis de ambiente
load_dotenv(override=True)

# Data e usuário atual
CURRENT_DATE = "2025-05-08 15:07:16"
CURRENT_USER = "contatogonetworkSim"

# Configuração do banco de dados
DB_PATH = os.getenv("DB_PATH", "geladeira.db")

# Configuração de UI
PAGE_TITLE = "🏡 Admin Doméstica"
PAGE_LAYOUT = "wide"
INITIAL_SIDEBAR_STATE = "expanded"