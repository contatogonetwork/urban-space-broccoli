import streamlit as st
import pandas as pd
import datetime
import traceback
from utils.formatters import *
from utils.constants import *
# Funções de nutrição centralizadas em utils.nutrition

def mostrar_inventario_thomas(db):
    st.title("👶 Inventário Thomás")
    
    # Descrição da área
    st.markdown("""
    Esta área é dedicada ao gerenciamento dos alimentos adequados para Thomás, 
    que possui restrições alimentares específicas.
    """)
    
    try:
        # Carregar dados apenas de Thomas
        df = db.carregar_inventario(apenas_thomas=True)
        
        # Filtros
        col1, col2, col3 = st.columns(3)
        with col1:
            filtro_nome = st.text_input("🔍 Filtrar por nome:", key="filtro_nome_thomas")
        with col2:
            localizacoes = sorted(df["Localização"].unique()) if not df.empty else []
            filtro_local = st.multiselect("📍 Filtrar por localização:", options=localizacoes, key="filtro_local_thomas")
        with col3:
            categorias = sorted(df["Categoria"].unique()) if not df.empty and "Categoria" in df.columns else []
            filtro_categoria = st.multiselect("🏷️ Filtrar por categoria:", options=categorias, key="filtro_categoria_thomas")
        
        # Aplicar filtros
        if not df.empty:
            if filtro_nome:
                df = df[df["Nome"].str.contains(filtro_nome, case=False)]
            if filtro_local:
                df = df[df["Localização"].isin(filtro_local)]
            if filtro_categoria and "Categoria" in df.columns:
                df = df[df["Categoria"].isin(filtro_categoria)]
        
        # Exibir dados
        if df.empty:
            st.info("Nenhum item cadastrado para Thomás.")
            st.markdown("""
                Para adicionar itens ao inventário de Thomás:
                1. Vá para a aba "Inventário Geral"
                2. Selecione um item e clique em "⭐ Thomas"
                
                Ou adicione um novo item marcando a opção "Item adequado para Thomás"
            """)
        else:
            # Preparar dataframe para exibição
            df_display = df.copy()
            
            # Aplicar formatação
            if "Contém Leite" in df_display.columns:
                df_display["Contém Leite"] = df_display["Contém Leite"].apply(format_leite_status)
            if "Compatibilidade Thomas" in df_display.columns:
                df_display["Compatibilidade Thomas"] = df_display["Compatibilidade Thomas"].apply(format_compatibilidade)
            
            # Selecionar colunas para exibição baseado nas disponíveis
            available_columns = df_display.columns.tolist()
            default_columns = ["ID", "Nome", "Compatibilidade Thomas"]
            
            if "Contém Leite" in available_columns:
                default_columns.append("Contém Leite")
                
            default_columns.extend(["Quantidade", "Unidade", "Localização"])
            
            if "Categoria" in available_columns:
                default_columns.append("Categoria")
                
            default_columns.extend(["Validade", "Dias Até Vencer"])
            
            # Adicionar informações nutricionais relevantes para Thomas
            nutrientes_thomas = [
                "Proteínas (g)", "Cálcio (mg)", "Vitamina D (mcg)", "Ferro (mg)", "Vitamina C (mg)"
            ]
            
            for nutriente in nutrientes_thomas:
                if nutriente in available_columns:
                    default_columns.append(nutriente)
            
            if "Nível Saúde" in available_columns:
                default_columns.append("Nível Saúde")
                
            # Filtrar colunas existentes
            colunas_exibir = [col for col in default_columns if col in available_columns]
            
            # Aplicar estilos possíveis
            styling_dict = {}
            if "Dias Até Vencer" in available_columns:
                styling_dict["Dias Até Vencer"] = highlight_expiration
            if "Quantidade" in available_columns:
                styling_dict["Quantidade"] = highlight_quantity
            if "Nível Saúde" in available_columns:
                styling_dict["Nível Saúde"] = highlight_health
                
            # Criar estilo
            df_style = df_display.style
            for col, style_func in styling_dict.items():
                df_style = df_style.applymap(style_func, subset=[col])
            
            # Configuração de colunas
            config_dict = {}
            if "ID" in colunas_exibir:
                config_dict["ID"] = st.column_config.NumberColumn("ID", width="small")
            if "Nome" in colunas_exibir:
                config_dict["Nome"] = st.column_config.TextColumn("Nome", width="medium")
            if "Compatibilidade Thomas" in colunas_exibir:
                config_dict["Compatibilidade Thomas"] = st.column_config.TextColumn(
                    "Compatibilidade", 
                    width="small", 
                    help="🟢=Seguro, 🟡=Verificar, 🔴=Não recomendado"
                )
            if "Contém Leite" in colunas_exibir:
                config_dict["Contém Leite"] = st.column_config.TextColumn("🥛 Leite", width="small", help="Contém derivados lácteos")
            if "Quantidade" in colunas_exibir:
                config_dict["Quantidade"] = st.column_config.NumberColumn("Quantidade", format="%.2f")
            if "Unidade" in colunas_exibir:
                config_dict["Unidade"] = st.column_config.TextColumn("Unidade", width="small")
            if "Localização" in colunas_exibir:
                config_dict["Localização"] = st.column_config.TextColumn("Localização")
            if "Categoria" in colunas_exibir:
                config_dict["Categoria"] = st.column_config.TextColumn("Categoria")
            if "Validade" in colunas_exibir:
                config_dict["Validade"] = st.column_config.DateColumn("Validade", format="DD/MM/YYYY")
            if "Dias Até Vencer" in colunas_exibir:
                config_dict["Dias Até Vencer"] = st.column_config.ProgressColumn(
                    "Dias Até Vencer",
                    format="%d dias",
                    min_value=0,
                    max_value=30
                )
            if "Nível Saúde" in colunas_exibir:
                config_dict["Nível Saúde"] = st.column_config.NumberColumn(
                    "Nível Saúde",
                    format="%d",
                    help="1=Saudável, 2=Intermediário, 3=Alto impacto"
                )
                
            # Configurar colunas nutricionais
            for nutriente in nutrientes_thomas:
                if nutriente in colunas_exibir:
                    config_dict[nutriente] = st.column_config.NumberColumn(nutriente, format="%.1f")
            
            # Exibir dataframe com tratamento de erro melhorado
            try:
                st.dataframe(
                    df_style.data[colunas_exibir], 
                    use_container_width=True,
                    height=400,
                    column_config=config_dict
                )
            except Exception as e:
                st.error(f"Erro ao exibir tabela: {str(e)}")
                st.dataframe(df_display[colunas_exibir])
            
            # Legenda de compatibilidade
            with st.expander("ℹ️ Legenda de compatibilidade para Thomás"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown('<div style="background-color: #d5f5d5; color: #1e6f50; padding: 10px; border-left: 3px solid #4caf50; border-radius: 5px;">🟢 Seguro para Thomás</div>', unsafe_allow_html=True)
                with col2:
                    st.markdown('<div style="background-color: #fff4cc; color: #806600; padding: 10px; border-left: 3px solid #ffcc00; border-radius: 5px;">🟡 Verificar ingredientes</div>', unsafe_allow_html=True)
                with col3:
                    st.markdown('<div style="background-color: #ffcccc; color: #cc0000; padding: 10px; border-left: 3px solid #cc0000; border-radius: 5px;">🔴 Não recomendado</div>', unsafe_allow_html=True)
            
            # Alertas para itens com leite
            itens_leite = df[df["Contém Leite"] == 1] if "Contém Leite" in df.columns else pd.DataFrame()
            if not itens_leite.empty:
                st.warning(f"⚠️ **Atenção!** {len(itens_leite)} item(s) contém leite ou derivados.")
                with st.expander("Ver itens com leite"):
                    for _, row in itens_leite.iterrows():
                        st.write(f"- {row['Nome']}")
            
            # Consumo de Thomas com validação melhorada
            st.subheader("📝 Registrar Consumo de Thomás")
            
            with st.form("form_consumo_thomas"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    item_id = st.selectbox(
                        "Selecione o item consumido", 
                        options=df["ID"].tolist(),
                        format_func=lambda x: df[df["ID"] == x]["Nome"].values[0]
                    )
                    
                    # Mostrar compatibilidade do item selecionado
                    item_comp = df[df["ID"] == item_id]["Compatibilidade Thomas"].values[0]
                    comp_icon = format_compatibilidade(item_comp)
                    
                    if item_comp == 0:  # Não recomendado
                        st.error(f"{comp_icon} Item não recomendado para Thomás!")
                        confirma_risco = st.checkbox("✓ Confirmo que este item é seguro para Thomás apesar das restrições", key="confirma_risco")
                    elif item_comp == 1:  # Verificar
                        st.warning(f"{comp_icon} Verifique os ingredientes antes de servir a Thomás.")
                        confirma_risco = st.checkbox("✓ Confirmo que verifiquei os ingredientes", key="confirma_verificacao")
                    else:  # Seguro
                        st.success(f"{comp_icon} Item seguro para Thomás.")
                        confirma_risco = True
                    
                with col2:
                    item_selecionado = df[df["ID"] == item_id]
                    unidade = item_selecionado["Unidade"].values[0] if "Unidade" in item_selecionado.columns else "unidade"
                    qtd_max = float(item_selecionado["Quantidade"].values[0])
                    
                    qtd_consumida = st.number_input(
                        f"Quantidade consumida ({unidade})",
                        min_value=0.1, 
                        max_value=qtd_max,
                        value=min(1.0, qtd_max),
                        step=0.1
                    )
                    
                    # Nutrientes consumidos em destaque
                    nutrientes_info = []
                    if "Proteínas (g)" in item_selecionado.columns and pd.notna(item_selecionado["Proteínas (g)"].values[0]):
                        proteina_cons = float(item_selecionado["Proteínas (g)"].values[0]) * qtd_consumida / 100
                        nutrientes_info.append(f"Proteínas: {proteina_cons:.1f}g")
                    
                    if "Cálcio (mg)" in item_selecionado.columns and pd.notna(item_selecionado["Cálcio (mg)"].values[0]):
                        calcio_cons = float(item_selecionado["Cálcio (mg)"].values[0]) * qtd_consumida / 100
                        nutrientes_info.append(f"Cálcio: {calcio_cons:.1f}mg")
                        
                    if "Ferro (mg)" in item_selecionado.columns and pd.notna(item_selecionado["Ferro (mg)"].values[0]):
                        ferro_cons = float(item_selecionado["Ferro (mg)"].values[0]) * qtd_consumida / 100
                        nutrientes_info.append(f"Ferro: {ferro_cons:.1f}mg")
                        
                    if nutrientes_info:
                        st.info("\n".join(nutrientes_info))
                    
                with col3:
                    data_consumo = st.date_input(
                        "Data do consumo",
                        value=datetime.date.today(),
                        max_value=datetime.date.today()  # Impede datas futuras
                    )
                
                # Validação antes de enviar
                submit_disabled = (item_comp == 0 or item_comp == 1) and not confirma_risco
                submit_button = st.form_submit_button("✅ Registrar Consumo", disabled=submit_disabled)
                
                if submit_button:
                    try:
                        success, msg = db.registrar_consumo(item_id, qtd_consumida, para_thomas=True, data=data_consumo)
                        if success:
                            st.success(msg)
                            # Registrar nutrientes consumidos para análise
                            try:
                                db.registrar_nutrientes_consumidos(item_id, qtd_consumida, para_thomas=True, data=data_consumo)
                            except:
                                st.warning("Registro de nutrientes não foi completado. A análise nutricional pode ficar incompleta.")
                            st.rerun()
                        else:
                            st.error(msg)
                    except Exception as e:
                        st.error(f"Erro ao registrar consumo: {str(e)}")
                        st.error("Por favor, tente novamente ou contate o suporte.")
                        
                # Dica para usuário quando tentando registrar item não recomendado
                if item_comp == 0 and not confirma_risco:
                    st.info("👆 Marque a opção acima para permitir o registro")

    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar o inventário de Thomás: {str(e)}")
        st.error("Por favor, atualize a página ou contate o suporte se o problema persistir.")
        st.code(traceback.format_exc())

# Stubs para páginas ainda não implementadas
def mostrar_perfil_thomas(db):
    st.title("👶 Perfil de Thomás")
    st.info("Em construção: perfil detalhado de Thomás.")

def mostrar_restricoes_alimentares(db):
    st.title("🚫 Restrições Alimentares de Thomás")
    st.info("Em construção: restrições alimentares de Thomas.")

def mostrar_necessidades_nutricionais(db):
    st.title("🥗 Necessidades Nutricionais de Thomás")
    st.info("Em construção: necessidades nutricionais de Thomas.")

def mostrar_analise_nutricional_thomas(db):
    st.title("📊 Análise Nutricional de Thomás")
    st.info("Em construção: análise nutricional de Thomas.")