import json
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler.api_gateway import ApiGatewayRestResolver
from aws_lambda_powertools.event_handler.exceptions import BadRequestError, UnauthorizedError
import inflection

logger = Logger()
tracer = Tracer()
app = ApiGatewayRestResolver()

def convert_to_snake_case(data):
    if isinstance(data, dict):
        return {inflection.underscore(k): convert_to_snake_case(v) for k, v in data.items()}
    if isinstance(data, list):
        return [convert_to_snake_case(i) for i in data]
    return data

def my_middleware(handler, event, context):
    try:
        if "body" in event and event["body"]:
            event["body"] = convert_to_snake_case(json.loads(event["body"]))
        return handler(event, context)
    except Exception as e:
        raise BadRequestError(f"Invalid request: {str(e)}")

@app.post("/cadastro")
@my_middleware
def cadastro_post_method(event, context):
    try:
        request_body = event['body']
        
        # Parse the request with the unified model
        request_model = UnifiedModel(**request_body)
        logger.info(f"Request data: {request_model.json()}")

        # Prepare the response data in snake_case
        response_data = request_model.dict()
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Data processed successfully",
                "data": response_data
            })
        }
    except Exception as e:
        raise BadRequestError(f"Invalid request: {str(e)}")

@logger.inject_lambda_context
@tracer.capture_lambda_handler
def lambda_handler(event, context):
    return app.resolve(event, context)
