
from repository import AthenaRepository
from s3_service import S3Service
from models import QueryPayload
from constants import QUERY_TEMPLATE
from datetime import datetime
from aws_lambda_powertools import Logger

logger = Logger(service="QueryService")

class QueryService:
    def __init__(self):
        self.athena_repository = AthenaRepository()
        self.s3_service = S3Service()

    def execute_query(self, payload: QueryPayload):
        query = QUERY_TEMPLATE.format(
            data_inicio=payload.data_inicio,
            data_fim=payload.data_fim,
            cnpj_base_participante=payload.cnpj_base_participante,
            agencia=payload.agencia,
            conta=payload.conta,
            tipo_pessoa=payload.tipo_pessoa
        )
        logger.info(f"Generated query: {query}")

        query_execution_id, df = self.athena_repository.execute_and_fetch_results(query)

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_name = f"{payload.tipo_arquivo}_{timestamp}.json"

        s3_path = self.s3_service.save_dataframe_to_s3(df, file_name)

        return {
            'query_execution_id': query_execution_id,
            's3_path': s3_path
        }
