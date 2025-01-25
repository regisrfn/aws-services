from config import ATHENA_DATABASE, S3_BUCKET, S3_PREFIX, logger
from models.payload_model import PayloadModel
from services.athena_service import execute_query, fetch_query_results
from repository.s3_repository import save_to_s3
from utils.query_builder import build_athena_query

def lambda_handler(event, context):
    try:
        logger.info("Validating input payload.")
        payload = PayloadModel(**event["payload"])
        query = build_athena_query(
            cnpj=payload.cnpj_base_participante,
            agencia=payload.agencia,
            conta=payload.conta,
        )
        logger.info("Executing Athena query.")
        query_execution_id = execute_query(
            query=query,
            database=ATHENA_DATABASE,
            output_location=f"s3://{S3_BUCKET}/{S3_PREFIX}",
        )
        logger.info("Fetching query results.")
        query_results = fetch_query_results(query_execution_id)
        logger.info("Saving results to S3.")
        s3_key = f"{S3_PREFIX}/{query_execution_id}.json"
        save_to_s3(S3_BUCKET, s3_key, query_results)
        logger.info(f"Query executed successfully. Results saved to {s3_key}")
        return {"status": "success", "query_execution_id": query_execution_id}
    except Exception as e:
        logger.exception(f"Error occurred: {e}")
        return {"status": "error", "message": str(e)}
