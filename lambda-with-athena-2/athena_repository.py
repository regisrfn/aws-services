import boto3
import pandas as pd
import time

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

    def get_query_results_as_dataframe(self, query_execution_id: str) -> pd.DataFrame:
        response = self.client.get_query_results(QueryExecutionId=query_execution_id)
        rows = response['ResultSet']['Rows']
        columns = [col['VarCharValue'] for col in rows[0]['Data']]
        data = [[cell.get('VarCharValue', None) for cell in row['Data']] for row in rows[1:]]
        df = pd.DataFrame(data, columns=columns)
        return df
