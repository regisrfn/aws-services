import unittest
from app.query_builder import QueryBuilder
from app.services.data_service import PayloadModel

class TestQueryBuilder(unittest.TestCase):
    def setUp(self):
        self.query_builder = QueryBuilder()

    def test_build_query(self):
        payload = PayloadModel(
            tipo_arquivo="example",
            numero_documento="123456789",
            data_inicio="2023-01-01",
            data_fim="2023-12-31",
            cnpj_base_participante="987654321",
            agencia="1234",
            conta="567890",
            tipo_pessoa="F"
        )
        query = self.query_builder.build_query(payload)
        self.assertIn("tipo_arquivo = 'example'", query)
