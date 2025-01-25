from aws_lambda_powertools.logging import Logger
import os

logger = Logger(service="AthenaQueryHandler")
ATHENA_DATABASE = os.getenv("ATHENA_DATABASE", "default")
S3_BUCKET = os.getenv("S3_BUCKET", "ccsrelacionamentocliente-detalhamento-dev")
S3_PREFIX = os.getenv("S3_PREFIX", "athena_results")
