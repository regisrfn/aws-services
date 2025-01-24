import unittest
from unittest.mock import MagicMock
from app.repositories.s3_repository import S3Repository

class TestS3Repository(unittest.TestCase):
    def setUp(self):
        self.repo = S3Repository("test-bucket")
        self.repo.s3 = MagicMock()

    def test_upload_file(self):
        self.repo.upload_file("path/to/file", "key")
        self.repo.s3.upload_file.assert_called_once_with("path/to/file", "test-bucket", "key")
