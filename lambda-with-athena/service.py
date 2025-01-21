
from repository import AthenaRepository
from models import QueryPayload
from constants import QUERY_TEMPLATE
from datetime import datetime

class QueryService:
    def __init__(self):
        self.athena_repository = AthenaRepository()

    def execute_query(self, payload: QueryPayload):
        query = QUERY_TEMPLATE.format(
            data_inicio=payload.data_inicio,
            data_fim=payload.data_fim,
            cnpj_base_participante=payload.cnpj_base_participante,
            agencia=payload.agencia,
            conta=payload.conta,
            tipo_pessoa=payload.tipo_pessoa
        )
        print("Generated Query:", query)
        query_execution_id = self.athena_repository.execute_query(query)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_name = f"{payload.tipo_arquivo}_{timestamp}.json"
        return {'query_execution_id': query_execution_id, 'file_name': file_name}
