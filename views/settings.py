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
        value=config.get("dias_alerta_vencimento", 7),
        help="Defina o número de dias antes do vencimento para receber alertas."
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
    if st.button("💾 Salvar Configurações", use_container_width=True):
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
    
    # Adicionar hover effects
    st.markdown(
        """
        <style>
        button:hover {
            background-color: #f0f0f0;
            color: #333;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

def mostrar_backup_restauracao(db):
    st.header("💾 Backup e Restauração")
    
    # Coluna para backup
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Backup de Dados")
        
        st.markdown("Crie uma cópia de segurança completa do seu banco de dados.")
        
        # Botão para gerar backup do arquivo .db
        if st.button("📥 Baixar Backup do Banco de Dados (.zip)"):
            try:
                backup_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                db_file_name = os.path.basename(db.db_path)
                zip_file_name = f"geladeira_db_backup_{backup_timestamp}.zip"
                
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    zip_file.write(db.db_path, arcname=db_file_name)
                    
                    # Adicionar README simples ao ZIP
                    readme_text = f"""
                    Backup Completo do Banco de Dados GELADEIRA
                    Data: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
                    Arquivo: {db_file_name}
                    
                    Este arquivo ZIP contém uma cópia completa do banco de dados SQLite.
                    Para restaurar, use a função de restauração no sistema, enviando este arquivo ZIP
                    ou o arquivo .db contido nele.
                    """
                    zip_file.writestr("README_backup.txt", readme_text)
                
                st.download_button(
                    label="📥 Baixar Arquivo de Backup (.zip)",
                    data=zip_buffer.getvalue(),
                    file_name=zip_file_name,
                    mime="application/zip",
                )
                st.success("✅ Backup do banco de dados gerado com sucesso!")
            except AttributeError:
                st.error("❌ Erro: O objeto 'db' não possui o atributo 'db_path'. Verifique a inicialização.")
            except FileNotFoundError:
                st.error(f"❌ Erro: Arquivo do banco de dados não encontrado em {db.db_path}")
            except Exception as e:
                st.error(f"❌ Erro ao gerar backup do banco de dados: {str(e)}")
                st.code(traceback.format_exc())
    
    with col2:
        st.subheader("Restaurar Dados do Banco de Dados")
        
        st.markdown("Restaure o sistema a partir de um arquivo de backup do banco de dados (`.db` ou `.zip` contendo um `.db`).")
        st.warning("⚠️ **ATENÇÃO**: A restauração substituirá TODOS os dados atuais do sistema.")

        uploaded_file = st.file_uploader(
            "Selecione o arquivo de backup (.db ou .zip)", 
            type=["db", "zip"]
        )
        
        if uploaded_file is not None:
            try:
                temp_dir = "temp_restore_dir"
                os.makedirs(temp_dir, exist_ok=True)
                
                backup_db_path = None

                if uploaded_file.name.endswith(".zip"):
                    with zipfile.ZipFile(uploaded_file) as zip_ref:
                        # Encontrar o primeiro arquivo .db dentro do zip
                        db_files_in_zip = [name for name in zip_ref.namelist() if name.endswith('.db')]
                        if not db_files_in_zip:
                            st.error("❌ O arquivo ZIP não contém um arquivo de banco de dados (.db).")
                            return
                        
                        # Extrair o arquivo .db para um local temporário
                        zip_ref.extract(db_files_in_zip[0], path=temp_dir)
                        backup_db_path = os.path.join(temp_dir, db_files_in_zip[0])
                        st.info(f"Arquivo .db extraído do ZIP: {db_files_in_zip[0]}")
                elif uploaded_file.name.endswith(".db"):
                    # Salvar o arquivo .db carregado diretamente em um local temporário
                    backup_db_path = os.path.join(temp_dir, uploaded_file.name)
                    with open(backup_db_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    st.info(f"Arquivo .db carregado: {uploaded_file.name}")
                else:
                    st.error("Tipo de arquivo não suportado. Por favor, envie um arquivo .db ou .zip.")
                    return

                if backup_db_path and os.path.exists(backup_db_path):
                    if st.button("🔄 Restaurar Banco de Dados Agora"):
                        # Importar a função de restauração do assistente
                        from utils.assistente import restaurar_backup as assistente_restaurar_backup
                        
                        # Obter o caminho do banco de dados atual
                        # É crucial que db.db_path seja o caminho correto para o arquivo .db ativo
                        current_db_path = db.db_path 
                        
                        # Fechar a conexão atual antes de restaurar, se possível
                        # Idealmente, o objeto db teria um método para fechar a conexão
                        if hasattr(db, 'fechar') and callable(db.fechar):
                            db.fechar()
                            st.info("Conexão com o banco de dados atual fechada.")
                        else:
                            st.warning("Não foi possível fechar a conexão com o banco de dados automaticamente. A restauração prosseguirá, mas pode ser necessário reiniciar a aplicação.")

                        success, msg = assistente_restaurar_backup(current_db_path, backup_db_path)
                        
                        if success:
                            st.success(f"✅ Banco de dados restaurado com sucesso! {msg}")
                            st.warning("⚠️ Por favor, recarregue a aplicação para aplicar as alterações.")
                            if st.button("🔄 Recarregar Aplicação Agora"):
                                st.rerun()
                        else:
                            st.error(f"❌ Erro ao restaurar o banco de dados: {msg}")
                else:
                    st.error("Não foi possível processar o arquivo de backup.")
            
            except Exception as e:
                st.error(f"❌ Erro ao processar arquivo de backup: {str(e)}")
                st.code(traceback.format_exc())
            finally:
                # Limpar diretório temporário
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)

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
        value=config.get("habilitar_alertas_vencimento", True),
        help="Ative para receber notificações sobre itens próximos do vencimento."
    )
    
    dias_antecedencia = st.slider(
        "Dias de antecedência para alertas de vencimento", 
        min_value=1, 
        max_value=30, 
        value=config.get("dias_alerta_vencimento", 7),
        help="Defina quantos dias antes do vencimento você deseja ser alertado.",
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
