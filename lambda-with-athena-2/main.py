from app.repositories.athena_repository import AthenaRepository
from app.repositories.s3_repository import S3Repository
from app.services.athena_service import AthenaService
from app.services.data_service import DataService
from app.constants import Constants

PAYLOAD = {
    "tipo_arquivo": "exemplo",
    "numero_documento": "12345678900",
    "data_inicio": "2023-01-01",
    "data_fim": "2023-12-31",
    "cnpj_base_participante": "00000000000191",
    "agencia": "1234",
    "conta": "567890",
    "tipo_pessoa": "F"
}

def main():
    athena_repo = AthenaRepository(Constants.DATABASE, Constants.OUTPUT_BUCKET)
    s3_repo = S3Repository(Constants.S3_BUCKET)
    data_service = DataService()
    athena_service = AthenaService(athena_repo, data_service)
    OUTPUT_KEY = "athena_results/output.json"
    athena_service.query_and_process_data(PAYLOAD, s3_repo, OUTPUT_KEY)

if __name__ == "__main__":
    main()
