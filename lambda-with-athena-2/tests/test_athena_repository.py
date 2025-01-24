import unittest
from unittest.mock import MagicMock
from app.repositories.athena_repository import AthenaRepository

class TestAthenaRepository(unittest.TestCase):
    def setUp(self):
        self.repo = AthenaRepository("test_database", "s3://test-bucket/")
        self.repo.client = MagicMock()

    def test_execute_query(self):
        self.repo.client.start_query_execution.return_value = {"QueryExecutionId": "test_id"}
        query_id = self.repo.execute_query("SELECT * FROM test_table")
        self.assertEqual(query_id, "test_id")
