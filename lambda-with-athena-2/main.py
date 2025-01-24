from pydantic import BaseModel, ValidationError, validator
import boto3
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime

# Configurações iniciais
ATHENA_DATABASE = os.getenv("ATHENA_DATABASE", "default_database")
ATHENA_TABLE = os.getenv("ATHENA_TABLE", "tb_detalhamento_spec")
S3_BUCKET = os.getenv("S3_BUCKET", "ccsrelacionamentocliente-detalhamento-dev")
S3_PREFIX = os.getenv("S3_PREFIX", "athena_results")

# Modelo de Payload usando Pydantic
class PayloadModel(BaseModel):
    cnpj_base_participante: str
    agencia: str
    conta: str
    tipo_arquivo: Optional[str]
    numero_documento: Optional[str]
    data_inicio: Optional[str]
    data_fim: Optional[str]
    tipo_pessoa: Optional[str]

    @validator("data_inicio", "data_fim", pre=True, always=True, allow_reuse=True)
    def validate_dates(cls, value):
        if not value or value.strip() == "":
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"Invalid date format for {value}. Expected format: YYYY-MM-DD")

    @validator("tipo_arquivo", "numero_documento", "tipo_pessoa", pre=True, always=True, allow_reuse=True)
    def empty_string_to_none(cls, value):
        return None if not value or value.strip() == "" else value

# Query Builder class
class QueryBuilder:
    def __init__(self, table: str):
        self.table = table
        self.conditions = []

    def add_condition(self, column: str, operator: str, value: Any, cast: Optional[str] = None):
        if cast:
            condition = f"CAST({column} AS {cast}) {operator} {value}"
        else:
            condition = f"{column} {operator} {value}"
        self.conditions.append(condition)

    def build(self) -> str:
        if not self.conditions:
            where_clause = ""
        else:
            where_clause = f"WHERE {' AND '.join(self.conditions)}"

        ranked_query = f"""
        WITH ranked_data AS (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY cnpj_base_participante, agencia, conta
                    ORDER BY data_processamento_glue_job DESC
                ) AS row_num
            FROM {self.table}
            {where_clause}
        )
        SELECT *
        FROM ranked_data
        WHERE row_num = 1
        """
        return ranked_query

    def from_payload(self, payload: PayloadModel) -> str:
        if payload.cnpj_base_participante:
            self.add_condition("cnpj_base_participante", "=", f"'{payload.cnpj_base_participante}'")
        if payload.agencia:
            self.add_condition("agencia", "=", f"'{payload.agencia}'")
        if payload.conta:
            self.add_condition("conta", "=", f"'{payload.conta}'")
        if payload.data_inicio:
            self.add_condition("data_inicio", ">=", f"DATE('{payload.data_inicio}')", cast="DATE")
        if payload.data_fim:
            self.add_condition("data_fim", "<=", f"DATE('{payload.data_fim}')", cast="DATE")
        return self.build()

# Repository: Gerenciamento de dados com AWS
class AthenaRepository:
    def __init__(self):
        self.client = boto3.client("athena")

    def execute_query(self, query: str) -> str:
        response = self.client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={"Database": ATHENA_DATABASE},
            ResultConfiguration={"OutputLocation": f"s3://{S3_BUCKET}/{S3_PREFIX}/"},
        )
        return response["QueryExecutionId"]


class S3Repository:
    def __init__(self):
        self.client = boto3.client("s3")

    def upload_json(self, data: Dict[str, Any], file_name: str):
        key = f"{S3_PREFIX}/{file_name}"
        self.client.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=json.dumps(data),
            ContentType="application/json",
        )
        return key

# Serviço principal
class QueryService:
    def __init__(self, athena_repo: AthenaRepository, s3_repo: S3Repository):
        self.athena_repo = athena_repo
        self.s3_repo = s3_repo

    def process_payload(self, payload: Dict[str, Any]):
        # Valida o payload
        try:
            validated_payload = PayloadModel(**payload)
        except ValidationError as e:
            raise ValueError(f"Payload inválido: {e}")

        # Constrói a query usando o QueryBuilder
        qb = QueryBuilder(ATHENA_TABLE)
        query = qb.from_payload(validated_payload)

        # Executa a query no Athena
        query_id = self.athena_repo.execute_query(query)

        # Cria o JSON de resultado e faz upload no S3
        result_data = {"query_id": query_id, "payload": payload}
        file_name = f"result_{query_id}.json"
        key = self.s3_repo.upload_json(result_data, file_name)
        return key

# Função handler da Lambda
def lambda_handler(event, context):
    athena_repo = AthenaRepository()
    s3_repo = S3Repository()
    service = QueryService(athena_repo, s3_repo)

    try:
        key = service.process_payload(event)
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Success", "s3_key": key})
        }
    except ValueError as e:
        return {"statusCode": 400, "body": json.dumps({"error": str(e)})}
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": "Internal Server Error", "details": str(e)})}
