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
git remote add origin https://github.com/SEU-USUARIO/geladeira

# Envie o código para o GitHub
git push -u origin main

Enumerating objects: X, done.
Counting objects: 100% (X/X), done.
Delta compression using up to Y CPU threads
Compressing objects: 100% (Z/Z), done.
Writing objects: 100% (X/X), AAAA bytes | BBBB KiB/s, done.
Total X (delta Y), reused Z (delta 0), pack-reused 0
remote: Resolving deltas: 100% (Y/Y), done.
To https://github.com/SEU-USUARIO/geladeira
 * [new branch]      main -> main
