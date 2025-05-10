#!/bin/bash
# Script de configuração e gerenciamento Git para o projeto GELADEIRA

# Navegar para o diretório do projeto
cd /workspaces/GELADEIRA || { echo "Diretório do projeto não encontrado"; exit 1; }

# Verificar se Git já está inicializado
if [ ! -d ".git" ]; then
    echo "Inicializando repositório Git..."
    git init
    if [ $? -ne 0 ]; then
        echo "Falha ao inicializar Git. Verifique se o Git está instalado."
        exit 1
    fi
fi

# Configurar usuário e email do Git (substituir com valores reais)
echo "Configurando usuário Git..."
git config --global user.name "NOME_REAL"
git config --global user.email "EMAIL_REAL@exemplo.com"

# Adicionar arquivos ao staging
echo "Adicionando arquivos ao staging..."
git add .

# Commit das alterações
echo "Realizando commit das alterações..."
git commit -m "Versão inicial do Sistema GELADEIRA"

# Verificar se o remote origin já existe
if ! git remote | grep -q "^origin$"; then
    echo "Adicionando repositório remoto..."
    # Substituir com URL real do repositório
    git remote add origin https://github.com/SEU-USUARIO-REAL/geladeira
fi

# Verificar qual branch está sendo usada
branch=$(git branch --show-current)
if [ -z "$branch" ]; then
    branch="main"
    git checkout -b main
fi

# Enviar para GitHub
echo "Enviando código para o GitHub..."
git push -u origin "$branch"

echo "Operação concluída com sucesso!"
