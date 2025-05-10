
import sqlite3
import datetime
import os
import sys
import logging

# Adicionar o diretório raiz do projeto ao sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from db.extended_database_manager import ExtendedDatabaseManager

# Configuração básica de logging para o teste
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Caminho para o banco de dados de teste (pode ser em memória ou um arquivo)
DB_PATH = os.path.join(project_root, "db", "test_geladeira_nutrientes.db")

def setup_test_database(db_path):
    """Configura um banco de dados de teste limpo."""
    if os.path.exists(db_path):
        os.remove(db_path)
    
    db = ExtendedDatabaseManager(db_path)
    # A inicialização do banco já cria as tabelas necessárias
    # Adicionar itens de teste
    item1_id = db.adicionar_item(
        nome="Maçã", categoria="Fruta", quantidade=10, unidade="unidade", 
        validade=datetime.date(2025, 12, 31), localizacao="Geladeira", custo_unitario=0.5
    )
    item2_id = db.adicionar_item(
        nome="Frango (Peito)", categoria="Carne", quantidade=500, unidade="g", 
        validade=datetime.date(2025, 5, 15), localizacao="Freezer", custo_unitario=15.0/1000 # Custo por grama
    )
    item3_id = db.adicionar_item(
        nome="Leite Integral", categoria="Laticínio", quantidade=1000, unidade="ml", 
        validade=datetime.date(2025, 5, 20), localizacao="Geladeira", custo_unitario=4.0/1000 # Custo por ml
    )
    item4_id = db.adicionar_item(
        nome="Pão Integral", categoria="Padaria", quantidade=1, unidade="unidade", # Pacote
        validade=datetime.date(2025, 5, 12), localizacao="Armário", custo_unitario=6.0
    )

    # Adicionar dados nutricionais para os itens
    # Maçã (por unidade - SUPOSIÇÃO da função)
    db.cursor.execute("INSERT INTO nutricional (item_id, calorias_100g, proteinas_g, carboidratos_g, gorduras_g, fibras_g, acucar_100g, sodio_100g) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                      (item1_id, 95, 0.5, 25, 0.3, 4, 19, 0.002)) # Sódio em g (2mg)
    # Frango (por 100g)
    db.cursor.execute("INSERT INTO nutricional (item_id, calorias_100g, proteinas_g, carboidratos_g, gorduras_g, fibras_g, acucar_100g, sodio_100g) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                      (item2_id, 165, 31, 0, 3.6, 0, 0, 0.074)) # Sódio em g (74mg)
    # Leite (por 100ml)
    db.cursor.execute("INSERT INTO nutricional (item_id, calorias_100g, proteinas_g, carboidratos_g, gorduras_g, fibras_g, acucar_100g, sodio_100g) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                      (item3_id, 60, 3.4, 4.8, 3.3, 0, 4.8, 0.050)) # Sódio em g (50mg)
    # Pão Integral (por unidade/pacote - SUPOSIÇÃO da função, aqui vamos simular por fatia, e o consumo será em fatias)
    # Para este exemplo, vamos assumir que "unidade" na tabela itens é um pacote, mas o consumo é por fatia.
    # E que os dados nutricionais são por fatia (ex: 1 fatia = 30g). A função tratará 'unidade' como 'por unidade consumida'.
    # Se o consumo for de '0.1' unidade (significando 1 fatia de um pacote de 10 fatias), e os dados abaixo são por fatia:
    db.cursor.execute("INSERT INTO nutricional (item_id, calorias_100g, proteinas_g, carboidratos_g, gorduras_g, fibras_g, acucar_100g, sodio_100g) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                      (item4_id, 70, 3, 12, 1, 2, 1.5, 0.130)) # Sódio em g (130mg)

    db.conn.commit()

    # Registrar consumos de teste
    # Consumo de hoje
    hoje = datetime.date.today()
    ontem = hoje - datetime.timedelta(days=1)
    semana_passada = hoje - datetime.timedelta(days=7)
    muito_tempo_atras = hoje - datetime.timedelta(days=10)

    # Maçã: 1 unidade hoje
    db.registrar_consumo(item1_id, 1, data=hoje)
    # Frango: 150g ontem
    db.registrar_consumo(item2_id, 150, data=ontem)
    # Leite: 200ml hoje
    db.registrar_consumo(item3_id, 200, data=hoje)
    # Pão: 2 fatias (assumindo que a "quantidade" em registrar_consumo para pão é em fatias)
    # Se 1 pacote (unidade no inventário) tem, por ex, 20 fatias, e consumimos 2 fatias,
    # a quantidade consumida do item "Pão Integral" seria 2 (se a unidade de consumo for fatia)
    # A função obter_nutrientes_consumidos vai multiplicar os valores nutricionais (que são por fatia) por esta quantidade.
    db.registrar_consumo(item4_id, 2, data=ontem) 

    # Consumo antigo (não deve ser contado por padrão)
    db.registrar_consumo(item1_id, 1, data=muito_tempo_atras) # Outra maçã

    logging.info(f"Banco de dados de teste configurado em {db_path} com itens e consumos.")
    return db, item1_id, item2_id, item3_id, item4_id

def test_obter_nutrientes(db_manager, dias, item_ids):
    logging.info(f"--- Testando obter_nutrientes_consumidos para os últimos {dias} dias ---")
    nutrientes = db_manager.obter_nutrientes_consumidos(dias=dias)
    
    print(f"Nutrientes consumidos nos últimos {dias} dias:")
    for nutriente, valor in nutrientes.items():
        print(f"  {nutriente}: {valor:.2f}")
    print("---")

    # Verificações básicas (exemplos, precisam de cálculo manual para serem exatos)
    if dias == 1: # Hoje (Maçã: 1 unidade, Leite: 200ml)
        # Maçã (unidade): 95 kcal, 0.5 prot, 25 carb, 0.3 gord, 4 fibra, 19 acucar, 0.002 sodio
        # Leite (200ml): (60 kcal, 3.4 prot, 4.8 carb, 3.3 gord, 0 fibra, 4.8 acucar, 0.050 sodio) * 200/100 = * 2
        # Leite: 120 kcal, 6.8 prot, 9.6 carb, 6.6 gord, 0 fibra, 9.6 acucar, 0.100 sodio
        # Total esperado: 
        # kcal: 95 + 120 = 215
        # prot: 0.5 + 6.8 = 7.3
        # carb: 25 + 9.6 = 34.6
        # gord: 0.3 + 6.6 = 6.9
        # fibra: 4 + 0 = 4
        # acucar: 19 + 9.6 = 28.6
        # sodio: 0.002 + 0.100 = 0.102
        assert abs(nutrientes["calorias_kcal"] - 215) < 0.01, f"Falha: Calorias esperadas ~215, obtidas {nutrientes['calorias_kcal']:.2f}"
        assert abs(nutrientes["proteinas_g"] - 7.3) < 0.01, f"Falha: Proteínas esperadas ~7.3, obtidas {nutrientes['proteinas_g']:.2f}"
        assert abs(nutrientes["carboidratos_g"] - 34.6) < 0.01, f"Falha: Carboidratos esperados ~34.6, obtidos {nutrientes['carboidratos_g']:.2f}"
        assert abs(nutrientes["gorduras_g"] - 6.9) < 0.01, f"Falha: Gorduras esperadas ~6.9, obtidas {nutrientes['gorduras_g']:.2f}"
        assert abs(nutrientes["fibras_g"] - 4.0) < 0.01, f"Falha: Fibras esperadas ~4.0, obtidas {nutrientes['fibras_g']:.2f}"
        assert abs(nutrientes["acucar_g"] - 28.6) < 0.01, f"Falha: Açúcar esperado ~28.6, obtido {nutrientes['acucar_g']:.2f}"
        assert abs(nutrientes["sodio_g"] - 0.102) < 0.01, f"Falha: Sódio esperado ~0.102, obtido {nutrientes['sodio_g']:.2f}"
        logging.info("Teste para 1 dia passou (valores verificados manualmente).")

    elif dias == 2: # Hoje e Ontem (Maçã: 1un, Leite: 200ml, Frango: 150g, Pão: 2 fatias)
        # Valores de hoje (já calculados): 215 kcal, 7.3 prot, 34.6 carb, 6.9 gord, 4 fibra, 28.6 acucar, 0.102 sodio
        # Frango (150g): (165 kcal, 31 prot, 0 carb, 3.6 gord, 0 fibra, 0 acucar, 0.074 sodio) * 150/100 = * 1.5
        # Frango: 247.5 kcal, 46.5 prot, 0 carb, 5.4 gord, 0 fibra, 0 acucar, 0.111 sodio
        # Pão (2 fatias): (70 kcal, 3 prot, 12 carb, 1 gord, 2 fibra, 1.5 acucar, 0.130 sodio) * 2
        # Pão: 140 kcal, 6 prot, 24 carb, 2 gord, 4 fibra, 3 acucar, 0.260 sodio
        # Total esperado:
        # kcal: 215 + 247.5 + 140 = 602.5
        # prot: 7.3 + 46.5 + 6 = 59.8
        # carb: 34.6 + 0 + 24 = 58.6
        # gord: 6.9 + 5.4 + 2 = 14.3
        # fibra: 4 + 0 + 4 = 8
        # acucar: 28.6 + 0 + 3 = 31.6
        # sodio: 0.102 + 0.111 + 0.260 = 0.473
        assert abs(nutrientes["calorias_kcal"] - 602.5) < 0.01, f"Falha: Calorias esperadas ~602.5, obtidas {nutrientes['calorias_kcal']:.2f}"
        assert abs(nutrientes["proteinas_g"] - 59.8) < 0.01, f"Falha: Proteínas esperadas ~59.8, obtidas {nutrientes['proteinas_g']:.2f}"
        assert abs(nutrientes["carboidratos_g"] - 58.6) < 0.01, f"Falha: Carboidratos esperados ~58.6, obtidos {nutrientes['carboidratos_g']:.2f}"
        assert abs(nutrientes["gorduras_g"] - 14.3) < 0.01, f"Falha: Gorduras esperadas ~14.3, obtidas {nutrientes['gorduras_g']:.2f}"
        assert abs(nutrientes["fibras_g"] - 8.0) < 0.01, f"Falha: Fibras esperadas ~8.0, obtidas {nutrientes['fibras_g']:.2f}"
        assert abs(nutrientes["acucar_g"] - 31.6) < 0.01, f"Falha: Açúcar esperado ~31.6, obtido {nutrientes['acucar_g']:.2f}"
        assert abs(nutrientes["sodio_g"] - 0.473) < 0.01, f"Falha: Sódio esperado ~0.473, obtido {nutrientes['sodio_g']:.2f}"
        logging.info("Teste para 2 dias passou (valores verificados manualmente).")

    elif dias == 8: # Deve incluir todos os consumos de teste, exceto o de 10 dias atrás
        # Os mesmos valores de 2 dias, pois não há consumo entre 2 e 7 dias atrás.
        # O consumo de 7 dias atrás (semana_passada) não foi adicionado no setup.
        # O consumo de 10 dias atrás (muito_tempo_atras) não deve ser incluído.
        assert abs(nutrientes["calorias_kcal"] - 602.5) < 0.01, "Falha: Calorias para 8 dias (mesmo que 2 dias neste dataset)"
        logging.info("Teste para 8 dias passou (valores verificados manualmente, igual a 2 dias).")

    elif dias == 0: # Teste de borda: 0 dias
        assert all(valor == 0 for valor in nutrientes.values()), "Falha: Para 0 dias, todos os nutrientes devem ser 0"
        logging.info("Teste para 0 dias passou (todos os valores são zero).")

    elif dias == 30: # Teste com período maior, deve incluir todos os consumos relevantes
        # Inclui o consumo de "muito_tempo_atras" (1 maçã) se dias >= 10
        # Valores de 2 dias: 602.5 kcal, 59.8 prot, 58.6 carb, 14.3 gord, 8 fibra, 31.6 acucar, 0.473 sodio
        # Maçã adicional: 95 kcal, 0.5 prot, 25 carb, 0.3 gord, 4 fibra, 19 acucar, 0.002 sodio
        # Total esperado:
        # kcal: 602.5 + 95 = 697.5
        # prot: 59.8 + 0.5 = 60.3
        # carb: 58.6 + 25 = 83.6
        # gord: 14.3 + 0.3 = 14.6
        # fibra: 8 + 4 = 12
        # acucar: 31.6 + 19 = 50.6
        # sodio: 0.473 + 0.002 = 0.475
        if datetime.date.today() - (datetime.date.today() - datetime.timedelta(days=10)) < datetime.timedelta(days=dias):
             assert abs(nutrientes["calorias_kcal"] - 697.5) < 0.01, f"Falha: Calorias esperadas ~697.5, obtidas {nutrientes['calorias_kcal']:.2f}"
             assert abs(nutrientes["proteinas_g"] - 60.3) < 0.01, f"Falha: Proteínas esperadas ~60.3, obtidas {nutrientes['proteinas_g']:.2f}"
             assert abs(nutrientes["carboidratos_g"] - 83.6) < 0.01, f"Falha: Carboidratos esperados ~83.6, obtidos {nutrientes['carboidratos_g']:.2f}"
             assert abs(nutrientes["gorduras_g"] - 14.6) < 0.01, f"Falha: Gorduras esperadas ~14.6, obtidas {nutrientes['gorduras_g']:.2f}"
             assert abs(nutrientes["fibras_g"] - 12.0) < 0.01, f"Falha: Fibras esperadas ~12.0, obtidas {nutrientes['fibras_g']:.2f}"
             assert abs(nutrientes["acucar_g"] - 50.6) < 0.01, f"Falha: Açúcar esperado ~50.6, obtido {nutrientes['acucar_g']:.2f}"
             assert abs(nutrientes["sodio_g"] - 0.475) < 0.01, f"Falha: Sódio esperado ~0.475, obtido {nutrientes['sodio_g']:.2f}"
             logging.info("Teste para 30 dias passou (incluindo consumo antigo).")
        else: # Caso o consumo de 10 dias atrás não entre no período de 'dias'
             assert abs(nutrientes["calorias_kcal"] - 602.5) < 0.01, "Falha: Calorias para 30 dias (igual a 2 dias neste dataset)"
             logging.info("Teste para 30 dias passou (não incluiu consumo antigo, conforme esperado).")

def test_sem_dados_nutricionais(db_manager, item_ids):
    logging.info("--- Testando com item sem dados nutricionais ---")
    # Adicionar um novo item e um consumo para ele, mas sem dados nutricionais
    item_sem_nutri_id = db_manager.adicionar_item(
        nome="Água Mineral", categoria="Bebida", quantidade=1000, unidade="ml", 
        validade=datetime.date(2026, 1, 1), localizacao="Geladeira"
    )
    db_manager.registrar_consumo(item_sem_nutri_id, 500, data=datetime.date.today())
    
    nutrientes = db_manager.obter_nutrientes_consumidos(dias=1)
    # Os valores devem ser os mesmos do teste de 1 dia, pois a água não adiciona nutrientes
    # e a função deve ignorar itens sem entrada na tabela nutricional.
    assert abs(nutrientes["calorias_kcal"] - 215) < 0.01, "Falha: Item sem dados nutricionais afetou o cálculo."
    logging.info("Teste com item sem dados nutricionais passou.")

def test_sem_consumo_no_periodo(db_manager):
    logging.info("--- Testando com período sem consumo ---")
    # Usar um DB novo ou garantir que não há consumo nos últimos X dias
    # Para este teste, vamos usar o DB existente mas pedir para um período futuro (ou muito pequeno)
    # onde sabemos que não houve consumo.
    # Ou, mais fácil, pedir para "dias=0" que já foi testado, ou um período que não pega os dados.
    # Vamos testar para um período de 1 dia, mas com data de início amanhã.
    # Isso requer modificar temporariamente a lógica de data ou criar um DB realmente vazio.
    
    # Mais simples: usar um DB limpo e não adicionar consumo
    temp_db_path = os.path.join(project_root, "db", "temp_empty_test.db")
    if os.path.exists(temp_db_path):
        os.remove(temp_db_path)
    empty_db = ExtendedDatabaseManager(temp_db_path)
    
    nutrientes = empty_db.obter_nutrientes_consumidos(dias=7)
    assert all(valor == 0 for valor in nutrientes.values()), "Falha: Período sem consumo não retornou zero para todos os nutrientes."
    logging.info("Teste com período sem consumo passou.")
    empty_db.fechar()
    if os.path.exists(temp_db_path):
        os.remove(temp_db_path)

if __name__ == "__main__":
    logging.info(f"Iniciando testes para obter_nutrientes_consumidos em {DB_PATH}.")
    db_manager, item1, item2, item3, item4 = setup_test_database(DB_PATH)
    item_ids = {"maca": item1, "frango": item2, "leite": item3, "pao": item4}

    try:
        test_obter_nutrientes(db_manager, dias=1, item_ids=item_ids) # Teste para hoje
        test_obter_nutrientes(db_manager, dias=2, item_ids=item_ids) # Teste para hoje e ontem
        test_obter_nutrientes(db_manager, dias=8, item_ids=item_ids) # Teste para última semana (pega os mesmos de 2 dias)
        test_obter_nutrientes(db_manager, dias=30, item_ids=item_ids) # Teste para último mês (pega todos os consumos)
        test_obter_nutrientes(db_manager, dias=0, item_ids=item_ids) # Teste de borda: 0 dias

        # Teste com item consumido mas sem dados nutricionais cadastrados
        # Reutiliza o db_manager que já tem os consumos anteriores.
        test_sem_dados_nutricionais(db_manager, item_ids=item_ids) 

        # Teste com período onde não houve consumo
        test_sem_consumo_no_periodo(db_manager) # Usa um DB temporário vazio

        logging.info("Todos os testes de obter_nutrientes_consumidos passaram com sucesso!")
    
    except AssertionError as e:
        logging.error(f"Falha em um dos testes: {e}", exc_info=True)
    except Exception as e:
        logging.error(f"Erro inesperado durante os testes: {e}", exc_info=True)
    finally:
        logging.info(f"Fechando conexão com o banco de dados de teste: {DB_PATH}")
        db_manager.fechar()
        # Opcional: remover o arquivo de banco de dados de teste após a execução
        # if os.path.exists(DB_PATH):
        #     os.remove(DB_PATH)
        #     logging.info(f"Banco de dados de teste {DB_PATH} removido.")
        pass

