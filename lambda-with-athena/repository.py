
import boto3
from botocore.exceptions import ClientError

class AthenaRepository:
    def __init__(self):
        self.athena_client = boto3.client('athena')
        self.s3_bucket = "ccsrelacionamentocliente-detalhamento-dev"
        self.s3_prefix = "athena_results/"

    def execute_query(self, query: str) -> str:
        try:
            response = self.athena_client.start_query_execution(
                QueryString=query,
                QueryExecutionContext={'Database': 'your_database_name'},
                ResultConfiguration={'OutputLocation': f's3://{self.s3_bucket}/{self.s3_prefix}'}
            )
            query_execution_id = response['QueryExecutionId']
            print(f"Query execution started with ID: {query_execution_id}")
            self._wait_for_query_to_complete(query_execution_id)
            return query_execution_id
        except ClientError as e:
            print(f"Client error while executing Athena query: {e}")
            raise

    def _wait_for_query_to_complete(self, query_execution_id: str):
        state = 'RUNNING'
        while state in ['RUNNING', 'QUEUED']:
            response = self.athena_client.get_query_execution(QueryExecutionId=query_execution_id)
            state = response['QueryExecution']['Status']['State']
            if state == 'SUCCEEDED':
                print("Query execution succeeded.")
            elif state == 'FAILED':
                reason = response['QueryExecution']['Status']['StateChangeReason']
                raise RuntimeError(f"Query execution failed: {reason}")
            elif state == 'CANCELLED':
                raise RuntimeError("Query execution was cancelled.")
