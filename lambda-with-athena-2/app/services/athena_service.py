from app.query_builder import QueryBuilder

class AthenaService:
    def __init__(self, athena_repo, data_service, query_builder=None):
        self.athena_repo = athena_repo
        self.data_service = data_service
        self.query_builder = query_builder or QueryBuilder()

    def query_and_process_data(self, payload, s3_repo, output_key):
        query = self.query_builder.build_query(payload)
        query_execution_id = self.athena_repo.execute_query(query)
        status = self.athena_repo.wait_for_query(query_execution_id)
        
        if status != "SUCCEEDED":
            raise Exception(f"Query failed with status: {status}")
        
        df = self.athena_repo.get_query_results_as_dataframe(query_execution_id)
        json_data = self.data_service.convert_to_json(df)
        self.data_service.save(json_data, s3_repo=s3_repo, key=output_key)
