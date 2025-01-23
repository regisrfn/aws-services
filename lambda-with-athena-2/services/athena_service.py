from app.query_builder import QueryBuilder
from app.constants import Constants

class AthenaService:
    def __init__(self, athena_repo, data_service):
        self.athena_repo = athena_repo
        self.data_service = data_service
        self.query_builder = QueryBuilder(Constants.TABLE_NAME)

    def query_and_process_data(self, payload: dict, s3_repo, output_key: str):
        query = self.query_builder.build_query(payload)
        query_execution_id = self.athena_repo.execute_query(query)
        status = self.athena_repo.wait_for_query(query_execution_id)
        
        if status != "SUCCEEDED":
            raise Exception(f"Query falhou com status: {status}")
        
        df = self.athena_repo.get_query_results_as_dataframe(query_execution_id)
        json_data = self.data_service.convert_to_json(df)
        self.data_service.save(json_data, s3_repo=s3_repo, key=output_key)
