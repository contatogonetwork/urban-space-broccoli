# Navegar para o diretório do projeto (se não estiver nele)
cd /workspaces/GELADEIRA

# Inicialize Git se ainda não estiver inicializado
# (Parece que você já tem um repositório Git baseado no arquivo COMMIT_EDITMSG)
# git init

# Configurar usuário e email do Git (se ainda não configurou)
git config --global user.name "Seu Nome"
git config --global user.email "seu-email@exemplo.com"

# Adicione todos os arquivos do projeto
git add .

# Faça o commit das alterações
git commit -m "Versão inicial do Sistema GELADEIRA"

# Adicione o repositório remoto (substitua com a URL do seu repositório)
git remote add origin https://github.com/SEU-USUARIO/geladeira.git

# Envie o código para o GitHub
git push -u origin main
