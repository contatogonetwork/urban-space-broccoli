import unittest
from db.extended_database_manager import ExtendedDatabaseManager

class TestExtendedDatabaseManager(unittest.TestCase):
    def setUp(self):
        self.db = ExtendedDatabaseManager(":memory:")

    def test_adicionar_item(self):
        item_id = self.db.adicionar_item(
            nome="Leite",
            categoria="Laticínios",
            quantidade=2,
            unidade="L",
            validade=None,
            localizacao="Geladeira",
            custo_unitario=4.99,
            para_thomas=False,
            contem_leite=True
        )
        self.assertIsNotNone(item_id)