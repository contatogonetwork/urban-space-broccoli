mkdir -p ~/.streamlit/
echo "[general]
email = \"seu-email@exemplo.com\"
" > ~/.streamlit/credentials.toml

echo "[server]
headless = true
port = $PORT
enableCORS = false
" > ~/.streamlit/config.toml
