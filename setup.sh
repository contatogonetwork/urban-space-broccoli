#!/bin/bash
# Script para configurar o ambiente Streamlit

# Verificar se PORT está definido
if [ -z "$PORT" ]; then
    export PORT=8501  # Porta padrão do Streamlit
    echo "⚠️ Variável PORT não definida. Usando porta padrão: $PORT"
fi

# Criar diretório com feedback
echo "🔧 Criando diretório de configuração Streamlit..."
mkdir -p ~/.streamlit/ || { echo "❌ Falha ao criar diretório ~/.streamlit/"; exit 1; }

# Criar arquivo de credenciais
echo "🔑 Configurando credenciais..."
echo "[general]
email = \"seu-email@dominio.com\"
" > ~/.streamlit/credentials.toml || { echo "❌ Falha ao criar arquivo de credenciais"; exit 1; }

# Criar arquivo de configuração
echo "⚙️ Configurando servidor na porta $PORT..."
echo "[server]
headless = true
port = $PORT
enableCORS = false
" > ~/.streamlit/config.toml || { echo "❌ Falha ao criar arquivo de configuração"; exit 1; }

echo "✅ Configuração Streamlit concluída com sucesso!"
