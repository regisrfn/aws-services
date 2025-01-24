import boto3

class AthenaRepository:
    def __init__(self, database: str, output_bucket: str):
        self.client = boto3.client('athena')
        self.database = database
        self.output_bucket = output_bucket

    def execute_query(self, query: str) -> str:
        response = self.client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': self.database},
            ResultConfiguration={'OutputLocation': self.output_bucket}
        )
        return response['QueryExecutionId']

    def wait_for_query(self, query_execution_id: str):
        while True:
            response = self.client.get_query_execution(QueryExecutionId=query_execution_id)
            status = response['QueryExecution']['Status']['State']
            if status in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                return status
            time.sleep(2)
