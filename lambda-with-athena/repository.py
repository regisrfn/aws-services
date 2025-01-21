
import boto3
from botocore.exceptions import ClientError
from utils import AthenaUtils
from aws_lambda_powertools import Logger

logger = Logger(service="AthenaRepository")

class AthenaRepository:
    def __init__(self):
        self.athena_client = boto3.client('athena')
        self.s3_bucket = "ccsrelacionamentocliente-detalhamento-dev"
        self.s3_prefix = "athena_results/"

    def execute_and_fetch_results(self, query: str):
        try:
            logger.info("Executing Athena query...")
            response = self.athena_client.start_query_execution(
                QueryString=query,
                QueryExecutionContext={'Database': 'your_database_name'},
                ResultConfiguration={'OutputLocation': f's3://{self.s3_bucket}/{self.s3_prefix}'}
            )
            query_execution_id = response['QueryExecutionId']
            logger.info(f"Athena query started with execution ID: {query_execution_id}")

            results = self._fetch_results(query_execution_id)
            return query_execution_id, results
        except ClientError as e:
            logger.exception(f"Error executing query in Athena: {e}")
            raise

    def _fetch_results(self, query_execution_id: str):
        state = 'RUNNING'
        while state in ['RUNNING', 'QUEUED']:
            response = self.athena_client.get_query_execution(QueryExecutionId=query_execution_id)
            state = response['QueryExecution']['Status']['State']
            if state == 'SUCCEEDED':
                logger.info("Athena query succeeded.")
                break
            elif state == 'FAILED':
                reason = response['QueryExecution']['Status']['StateChangeReason']
                logger.error(f"Athena query failed: {reason}")
                raise RuntimeError(f"Athena query failed: {reason}")
            elif state == 'CANCELLED':
                logger.error("Athena query was cancelled.")
                raise RuntimeError("Athena query was cancelled.")

        paginator = self.athena_client.get_query_results(QueryExecutionId=query_execution_id)
        rows = paginator['ResultSet']['Rows']

        # Use utility class to transform results into a DataFrame
        df = AthenaUtils.transform_results_to_dataframe(rows)
        return df
