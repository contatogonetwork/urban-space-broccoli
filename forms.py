def adicionar_item_form(db):
    st.title("➕ Adicionar Item ao Inventário")
    
    with st.form("form_adicionar_item"):
        nome = st.text_input("Nome do Item")
        quantidade = st.number_input("Quantidade", min_value=1, value=1, step=1)
        categoria = st.selectbox("Categoria", ["Laticínios", "Vegetais", "Frutas", "Carnes", "Bebidas", "Outros"])
        data_validade = st.date_input("Data de Validade")
        notas = st.text_area("Observações", height=100)
        submitted = st.form_submit_button("Adicionar Item")
        
        if submitted:
            if not nome or len(nome.strip()) == 0:
                st.error("O nome do item é obrigatório.")
                return
                
            try:
                # Create new item in database
                novo_item = {
                    "nome": nome,
                    "quantidade": quantidade,
                    "categoria": categoria,
                    "data_validade": data_validade.strftime("%Y-%m-%d"),
                    "notas": notas
                }
                
                # Insert into database (assuming db has an insert method)
                db.add_item(novo_item)
                st.success(f"Item '{nome}' adicionado com sucesso!")
                
                # Clear form by rerunning
                st.experimental_rerun()
                
            except Exception as e:
                st.error(f"Erro ao adicionar item: {str(e)}")