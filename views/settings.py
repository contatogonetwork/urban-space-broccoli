import streamlit as st
import pandas as pd
import datetime
import os
import io
import json
import zipfile
import shutil
import traceback

def mostrar_configuracoes(db):
    st.title("⚙️ Configurações do Sistema")
    
    tab1, tab2, tab3 = st.tabs(["🔧 Geral", "💾 Backup e Restauração", "⚠️ Alertas"])
    
    with tab1:
        mostrar_configuracoes_gerais(db)
        
    with tab2:
        mostrar_backup_restauracao(db)
        
    with tab3:
        mostrar_configuracoes_alertas(db)

def mostrar_configuracoes_gerais(db):
    st.header("🔧 Configurações Gerais")
    
    # Inicializar configurações na sessão se não existirem
    if "config" not in st.session_state:
        # Carregar configurações do banco de dados
        st.session_state.config = db.carregar_configuracoes()
    
    config = st.session_state.config
    
    # Configurações da interface
    st.subheader("Interface")
    
    tema = st.selectbox(
        "Tema da interface", 
        options=["Claro", "Escuro", "Sistema"],
        index=config.get("tema", 2)
    )
    
    mostrar_alertas_inicio = st.checkbox(
        "Mostrar alertas na página inicial", 
        value=config.get("mostrar_alertas_inicio", True)
    )
    
    # Configurações do inventário
    st.subheader("Inventário")
    
    dias_alerta_vencimento = st.slider(
        "Alertar sobre vencimentos com quantos dias de antecedência", 
        min_value=1, 
        max_value=30, 
        value=config.get("dias_alerta_vencimento", 7)
    )
    
    nivel_alerta_quantidade = st.slider(
        "Alertar quando a quantidade estiver abaixo de (%)", 
        min_value=5, 
        max_value=50, 
        value=config.get("nivel_alerta_quantidade", 20)
    )
    
    # Configurações para Thomás
    st.subheader("Configurações para Thomás")
    
    idade_thomas = st.number_input(
        "Idade de Thomás (meses)", 
        min_value=6, 
        max_value=60,
        value=config.get("idade_thomas", 24),
        step=1,
        help="A idade influencia as necessidades nutricionais recomendadas"
    )
    
    peso_thomas = st.number_input(
        "Peso de Thomás (kg)", 
        min_value=5.0, 
        max_value=30.0,
        value=config.get("peso_thomas", 12.0),
        step=0.1,
        help="O peso é usado para calcular doses apropriadas"
    )
    
    # Botão para salvar configurações
    if st.button("💾 Salvar Configurações"):
        # Atualizar dicionário de configurações
        novas_config = {
            "tema": tema,
            "mostrar_alertas_inicio": mostrar_alertas_inicio,
            "dias_alerta_vencimento": dias_alerta_vencimento,
            "nivel_alerta_quantidade": nivel_alerta_quantidade,
            "idade_thomas": idade_thomas,
            "peso_thomas": peso_thomas
        }
        
        # Atualizar na sessão
        st.session_state.config = novas_config
        
        # Salvar no banco de dados
        try:
            success, msg = db.salvar_configuracoes(novas_config)
            if success:
                st.success("✅ Configurações salvas com sucesso!")
                # Aplicar mudanças imediatas
                if novas_config.get("tema") == 0:  # Claro
                    st.markdown("""
                    <style>
                    [data-testid="stAppViewContainer"] {
                        background-color: #ffffff;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                elif novas_config.get("tema") == 1:  # Escuro
                    st.markdown("""
                    <style>
                    [data-testid="stAppViewContainer"] {
                        background-color: #0e1117;
                    }
                    </style>
                    """, unsafe_allow_html=True)
            else:
                st.error(f"❌ Erro ao salvar configurações: {msg}")
        except Exception as e:
            st.error(f"❌ Erro: {str(e)}")
            st.code(traceback.format_exc())

def mostrar_backup_restauracao(db):
    st.header("💾 Backup e Restauração")
    
    # Coluna para backup
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Backup de Dados")
        
        # Opções de backup
        backup_options = st.multiselect(
            "Selecione os dados para backup",
            options=["Inventário", "Histórico de Consumo", "Configurações de Thomas", "Lista de Compras"],
            default=["Inventário", "Histórico de Consumo", "Configurações de Thomas"]
        )
        
        # Botão para gerar backup
        if st.button("📥 Gerar Backup"):
            if not backup_options:
                st.error("Selecione pelo menos um tipo de dado para backup")
            else:
                try:
                    # Criar arquivo de backup
                    backup_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_data = {}
                    
                    # Coletar dados
                    if "Inventário" in backup_options:
                        backup_data["inventario"] = db.carregar_inventario().to_dict()
                        
                    if "Histórico de Consumo" in backup_options:
                        backup_data["consumo"] = db.obter_estatisticas_consumo(periodo_dias=365).to_dict()
                        
                    if "Configurações de Thomas" in backup_options:
                        backup_data["thomas_config"] = {
                            "restricoes": db.obter_restricoes_thomas(),
                            "necessidades": db.obter_necessidades_thomas()
                        }
                        
                    if "Lista de Compras" in backup_options:
                        # Usar dados da sessão se disponíveis
                        if "lista_compras" in st.session_state:
                            backup_data["lista_compras"] = st.session_state.lista_compras
                    
                    # Converter para JSON
                    backup_json = json.dumps(backup_data, default=str)
                    
                    # Criar arquivo ZIP com o backup
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED) as zip_file:
                        zip_file.writestr(f"geladeira_backup_{backup_timestamp}.json", backup_json)
                        
                        # Adicionar README
                        readme_text = f"""
                        Backup do Sistema GELADEIRA
                        Data: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
                        
                        Este arquivo contém um backup dos seguintes dados:
                        {', '.join(backup_options)}
                        
                        Para restaurar, use a função de restauração no sistema.
                        """
                        zip_file.writestr("README.txt", readme_text)
                    
                    # Oferecer download
                    st.download_button(
                        label="📥 Baixar Arquivo de Backup",
                        data=zip_buffer.getvalue(),
                        file_name=f"geladeira_backup_{backup_timestamp}.zip",
                        mime="application/zip",
                    )
                    
                    st.success("✅ Backup gerado com sucesso!")
                except Exception as e:
                    st.error(f"❌ Erro ao gerar backup: {str(e)}")
                    st.code(traceback.format_exc())
    
    with col2:
        st.subheader("Restaurar Dados")
        
        uploaded_file = st.file_uploader("Selecione um arquivo de backup (.zip)", type=["zip"])
        
        if uploaded_file is not None:
            # Verificar o arquivo
            try:
                # Ler arquivo ZIP
                with zipfile.ZipFile(uploaded_file) as zip_ref:
                    # Listar conteúdo
                    file_list = zip_ref.namelist()
                    
                    # Encontrar arquivo JSON
                    json_files = [f for f in file_list if f.endswith('.json')]
                    
                    if not json_files:
                        st.error("❌ Arquivo de backup inválido: não contém dados JSON")
                    else:
                        # Extrair dados do primeiro arquivo JSON
                        with zip_ref.open(json_files[0]) as json_file:
                            backup_data = json.loads(json_file.read())
                            
                            # Mostrar resumo dos dados
                            st.write("📋 Resumo dos dados de backup:")
                            
                            if "inventario" in backup_data:
                                st.info(f"✓ Inventário: {len(backup_data['inventario'].get('ID', []))} itens")
                                
                            if "consumo" in backup_data:
                                st.info(f"✓ Histórico de Consumo: {len(backup_data['consumo'].get('ID', []))} registros")
                                
                            if "thomas_config" in backup_data:
                                st.info(f"✓ Configurações de Thomas: {len(backup_data['thomas_config'].get('restricoes', []))} restrições, {len(backup_data['thomas_config'].get('necessidades', []))} necessidades nutricionais")
                                
                            if "lista_compras" in backup_data:
                                st.info(f"✓ Lista de Compras: {len(backup_data['lista_compras'])} itens")
                            
                            # Opções de restauração
                            st.warning("⚠️ **ATENÇÃO**: A restauração substituirá os dados atuais.")
                            
                            # Selecionar tipos de dados a restaurar
                            tipos_dados = []
                            if "inventario" in backup_data:
                                tipos_dados.append("Inventário")
                            if "consumo" in backup_data:
                                tipos_dados.append("Histórico de Consumo")
                            if "thomas_config" in backup_data:
                                tipos_dados.append("Configurações de Thomas")
                            if "lista_compras" in backup_data:
                                tipos_dados.append("Lista de Compras")
                            
                            dados_restaurar = st.multiselect(
                                "Selecione os dados a restaurar",
                                options=tipos_dados,
                                default=tipos_dados
                            )
                            
                            # Botão de restauração
                            if st.button("🔄 Restaurar Dados Selecionados"):
                                if not dados_restaurar:
                                    st.error("Selecione pelo menos um tipo de dado para restaurar")
                                else:
                                    try:
                                        restaurados = 0
                                        
                                        # Restaurar inventário
                                        if "Inventário" in dados_restaurar and "inventario" in backup_data:
                                            # Implementar função no DB para restaurar inventário
                                            success, msg = db.restaurar_inventario(backup_data["inventario"])
                                            if success:
                                                st.success(f"✅ Inventário restaurado: {msg}")
                                                restaurados += 1
                                            else:
                                                st.error(f"❌ Erro ao restaurar inventário: {msg}")
                                        
                                        # Restaurar histórico de consumo
                                        if "Histórico de Consumo" in dados_restaurar and "consumo" in backup_data:
                                            # Implementar função no DB para restaurar consumo
                                            success, msg = db.restaurar_consumo(backup_data["consumo"])
                                            if success:
                                                st.success(f"✅ Histórico de consumo restaurado: {msg}")
                                                restaurados += 1
                                            else:
                                                st.error(f"❌ Erro ao restaurar histórico de consumo: {msg}")
                                        
                                        # Restaurar configurações de Thomas
                                        if "Configurações de Thomas" in dados_restaurar and "thomas_config" in backup_data:
                                            # Implementar funções no DB para restaurar configurações de Thomas
                                            success_r, msg_r = db.restaurar_restricoes_thomas(backup_data["thomas_config"].get("restricoes", []))
                                            success_n, msg_n = db.restaurar_necessidades_thomas(backup_data["thomas_config"].get("necessidades", []))
                                            
                                            if success_r and success_n:
                                                st.success("✅ Configurações de Thomas restauradas com sucesso")
                                                restaurados += 1
                                            else:
                                                if not success_r:
                                                    st.error(f"❌ Erro ao restaurar restrições: {msg_r}")
                                                if not success_n:
                                                    st.error(f"❌ Erro ao restaurar necessidades: {msg_n}")
                                        
                                        # Restaurar lista de compras
                                        if "Lista de Compras" in dados_restaurar and "lista_compras" in backup_data:
                                            # Atualizar lista na sessão
                                            st.session_state.lista_compras = backup_data["lista_compras"]
                                            st.success("✅ Lista de compras restaurada com sucesso")
                                            restaurados += 1
                                        
                                        if restaurados > 0:
                                            st.success(f"✅ Restauração concluída! {restaurados} conjunto(s) de dados restaurados.")
                                            st.warning("⚠️ Recarregue a aplicação para ver os dados restaurados.")
                                            if st.button("🔄 Recarregar Aplicação"):
                                                st.rerun()
                                        else:
                                            st.warning("⚠️ Nenhum dado foi restaurado.")
                                        
                                    except Exception as e:
                                        st.error(f"❌ Erro durante a restauração: {str(e)}")
                                        st.code(traceback.format_exc())
                
            except Exception as e:
                st.error(f"❌ Erro ao processar arquivo: {str(e)}")
                st.code(traceback.format_exc())

def mostrar_configuracoes_alertas(db):
    st.header("⚠️ Configurações de Alertas")
    
    # Carregar configurações de alertas atuais
    if "config_alertas" not in st.session_state:
        # Carregar do banco de dados
        st.session_state.config_alertas = db.carregar_configuracoes_alertas()
    
    config = st.session_state.config_alertas
    
    # Alertas de vencimento
    st.subheader("Alertas de Vencimento")
    
    habilitar_alertas_vencimento = st.checkbox(
        "Habilitar alertas de vencimento", 
        value=config.get("habilitar_alertas_vencimento", True)
    )
    
    dias_antecedencia = st.slider(
        "Alertar com quantos dias de antecedência", 
        min_value=1, 
        max_value=30, 
        value=config.get("dias_antecedencia", 7),
        disabled=not habilitar_alertas_vencimento
    )
    
    sempre_mostrar_vencidos = st.checkbox(
        "Sempre mostrar itens vencidos", 
        value=config.get("sempre_mostrar_vencidos", True),
        disabled=not habilitar_alertas_vencimento
    )
    
    # Alertas de estoque
    st.subheader("Alertas de Estoque")
    
    habilitar_alertas_estoque = st.checkbox(
        "Habilitar alertas de estoque baixo", 
        value=config.get("habilitar_alertas_estoque", True)
    )
    
    percentual_estoque = st.slider(
        "Alertar quando estoque abaixo de (%)", 
        min_value=5, 
        max_value=50, 
        value=config.get("percentual_estoque", 20),
        disabled=not habilitar_alertas_estoque
    )
    
    # Alertas específicos para Thomás
    st.subheader("Alertas para Thomás")
    
    habilitar_alertas_thomas = st.checkbox(
        "Habilitar alertas específicos para Thomás", 
        value=config.get("habilitar_alertas_thomas", True)
    )
    
    prioridade_thomas = st.slider(
        "Prioridade dos alertas de Thomás", 
        min_value=1, 
        max_value=5, 
        value=config.get("prioridade_thomas", 3),
        help="1=Baixa, 5=Alta; Define a visibilidade dos alertas relacionados a Thomás",
        disabled=not habilitar_alertas_thomas
    )
    
    monitorar_nutricao_thomas = st.checkbox(
        "Monitorar nutrição de Thomás", 
        value=config.get("monitorar_nutricao_thomas", True),
        disabled=not habilitar_alertas_thomas
    )
    
    limite_alerta_nutricional = st.slider(
        "Alertar quando consumo nutricional abaixo de (%)", 
        min_value=50, 
        max_value=90, 
        value=config.get("limite_alerta_nutricional", 70),
        disabled=not (habilitar_alertas_thomas and monitorar_nutricao_thomas)
    )
    
    # Botão para salvar configurações
    if st.button("💾 Salvar Configurações de Alertas"):
        # Atualizar dicionário de configurações
        novas_config = {
            "habilitar_alertas_vencimento": habilitar_alertas_vencimento,
            "dias_antecedencia": dias_antecedencia,
            "sempre_mostrar_vencidos": sempre_mostrar_vencidos,
            "habilitar_alertas_estoque": habilitar_alertas_estoque,
            "percentual_estoque": percentual_estoque,
            "habilitar_alertas_thomas": habilitar_alertas_thomas,
            "prioridade_thomas": prioridade_thomas,
            "monitorar_nutricao_thomas": monitorar_nutricao_thomas,
            "limite_alerta_nutricional": limite_alerta_nutricional
        }
        
        # Atualizar na sessão
        st.session_state.config_alertas = novas_config
        
        # Salvar no banco de dados
        try:
            success, msg = db.salvar_configuracoes_alertas(novas_config)
            if success:
                st.success("✅ Configurações de alertas salvas com sucesso!")
            else:
                st.error(f"❌ Erro ao salvar configurações de alertas: {msg}")
        except Exception as e:
            st.error(f"❌ Erro: {str(e)}")
            st.code(traceback.format_exc())
