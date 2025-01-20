
from repository import AthenaRepository
from models import QueryPayload
from datetime import datetime

class QueryService:
    def __init__(self):
        self.athena_repository = AthenaRepository()

    def execute_query(self, payload: QueryPayload):
        query = f"""SELECT * FROM tb_detalhamento_spec
        WHERE data_hor_incu_rgto BETWEEN '{payload.data_inicio}' AND '{payload.data_fim}'
        AND cnpj_base_participante = '{payload.cnpj_base_participante}'
        AND agencia = '{payload.agencia}'
        AND conta = '{payload.conta}'
        AND tipo_pessoa = '{payload.tipo_pessoa}';"""
        print("Generated Query:", query)
        query_execution_id = self.athena_repository.execute_query(query)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_name = f"{payload.tipo_arquivo}_{timestamp}.json"
        return {'query_execution_id': query_execution_id, 'file_name': file_name}
