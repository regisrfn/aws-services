
from models import QueryPayload
from service import QueryService
from pydantic import ValidationError
from aws_lambda_powertools import Logger

logger = Logger(service="AthenaQueryService")

@logger.inject_lambda_context
def lambda_handler(event, context):
    try:
        logger.info("Received event: %s", event)
        payload = QueryPayload(**event)
        query_service = QueryService()
        result = query_service.execute_query(payload)
        return {
            'statusCode': 200,
            'body': result
        }
    except ValidationError as ve:
        logger.error("Validation error: %s", ve)
        return {
            'statusCode': 400,
            'body': {'error': str(ve)}
        }
    except Exception as e:
        logger.exception("Unexpected error occurred: %s", e)
        return {
            'statusCode': 500,
            'body': {'error': 'An unexpected error occurred.', 'details': str(e)}}
