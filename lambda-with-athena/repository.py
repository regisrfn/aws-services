
import boto3
from botocore.exceptions import ClientError

class AthenaRepository:
    def __init__(self):
        self.athena_client = boto3.client('athena')
        self.s3_bucket = "ccsrelacionamentocliente-detalhamento-dev"
        self.s3_prefix = "athena_results/"

    def execute_and_fetch_results(self, query: str):
        try:
            response = self.athena_client.start_query_execution(
                QueryString=query,
                QueryExecutionContext={'Database': 'your_database_name'},
                ResultConfiguration={'OutputLocation': f's3://{self.s3_bucket}/{self.s3_prefix}'}
            )
            query_execution_id = response['QueryExecutionId']
            print(f"Consulta Athena iniciada com ID: {query_execution_id}")

            results = self._fetch_results(query_execution_id)
            return query_execution_id, results
        except ClientError as e:
            print(f"Erro ao executar consulta no Athena: {e}")
            raise

    def _fetch_results(self, query_execution_id: str):
        state = 'RUNNING'
        while state in ['RUNNING', 'QUEUED']:
            response = self.athena_client.get_query_execution(QueryExecutionId=query_execution_id)
            state = response['QueryExecution']['Status']['State']
            if state == 'SUCCEEDED':
                print("Consulta Athena concluída com sucesso.")
                break
            elif state == 'FAILED':
                reason = response['QueryExecution']['Status']['StateChangeReason']
                raise RuntimeError(f"Consulta Athena falhou: {reason}")
            elif state == 'CANCELLED':
                raise RuntimeError("Consulta Athena foi cancelada.")

        paginator = self.athena_client.get_query_results(QueryExecutionId=query_execution_id)
        rows = paginator['ResultSet']['Rows']

        header = [col['VarCharValue'] for col in rows[0]['Data']]
        results = [
            {header[i]: row['Data'][i].get('VarCharValue', None) for i in range(len(row['Data']))}
            for row in rows[1:]  # Ignorar cabeçalho
        ]
        return results
