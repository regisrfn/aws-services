import boto3
from botocore.exceptions import ClientError
from config import logger

athena_client = boto3.client("athena")

def execute_query(query: str, database: str, output_location: str) -> str:
    try:
        logger.info(f"Executing Athena query: {query.strip()}")
        response = athena_client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={"Database": database},
            ResultConfiguration={"OutputLocation": output_location},
        )
        return response["QueryExecutionId"]
    except ClientError as e:
        logger.exception(f"Error executing Athena query: {e}")
        raise

def fetch_query_results(query_execution_id: str) -> list:
    try:
        logger.info(f"Fetching Athena query results: QueryExecutionId={query_execution_id}")
        results_paginator = athena_client.get_paginator("get_query_results")
        results_iterator = results_paginator.paginate(QueryExecutionId=query_execution_id)
        rows = []
        for page in results_iterator:
            rows.extend(page["ResultSet"]["Rows"])
        headers = [col["VarCharValue"] for col in rows[0]["Data"]]
        data = [
            {headers[i]: value.get("VarCharValue", "") for i, value in enumerate(row["Data"])}
            for row in rows[1:]
        ]
        return data
    except ClientError as e:
        logger.exception(f"Error fetching Athena query results: {e}")
        raise
