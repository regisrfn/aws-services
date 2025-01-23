from app.services.data_service import DataService
from app.services.athena_service import AthenaService
from app.repositories.athena_repository import AthenaRepository
from app.repositories.s3_repository import S3Repository
from app.constants import Constants

def lambda_handler(event, context):
    payload = event.get("payload", {})
    data_service = DataService()

    try:
        # Validar payload
        validated_payload = data_service.validate_payload(payload)

        # Inicializar serviços
        athena_repo = AthenaRepository(Constants.DATABASE, Constants.OUTPUT_BUCKET)
        s3_repo = S3Repository(Constants.S3_BUCKET)
        athena_service = AthenaService(athena_repo, data_service)

        # Processar consulta no Athena e salvar no S3
        athena_service.query_and_process_data(validated_payload.dict(), s3_repo, "athena_results/output.json")
        return {"statusCode": 200, "body": "Processamento concluído com sucesso."}
    except ValueError as e:
        return {"statusCode": 400, "body": str(e)}
