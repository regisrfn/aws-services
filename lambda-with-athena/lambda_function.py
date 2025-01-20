
from models import QueryPayload
from service import QueryService
from pydantic import ValidationError

def lambda_handler(event, context):
    try:
        payload = QueryPayload(**event)
        query_service = QueryService()
        result = query_service.execute_query(payload)
        return {
            'statusCode': 200,
            'body': result
        }
    except ValidationError as ve:
        print(f"Validation error: {ve}")
        return {
            'statusCode': 400,
            'body': {'error': str(ve)}
        }
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {
            'statusCode': 500,
            'body': {'error': 'An unexpected error occurred.', 'details': str(e)}}
