from app.constants import Constants

class QueryBuilder:
    def __init__(self, table_name: str):
        self.table_name = table_name

    def build_query(self, payload: dict) -> str:
        missing_fields = [field for field in Constants.REQUIRED_FIELDS if field not in payload]
        if missing_fields:
            raise ValueError(f"Campos obrigatórios ausentes: {', '.join(missing_fields)}")
        where_clauses = []
        if payload.get("tipo_arquivo"):
            where_clauses.append(f"tipo_arquivo = '{payload['tipo_arquivo']}'")
        if payload.get("numero_documento"):
            where_clauses.append(f"numero_documento = '{payload['numero_documento']}'")
        if payload.get("data_inicio") and payload.get("data_fim"):
            where_clauses.append(f"data_vinculo BETWEEN '{payload['data_inicio']}' AND '{payload['data_fim']}'")
        if payload.get("cnpj_base_participante"):
            where_clauses.append(f"cnpj_base_participante = '{payload['cnpj_base_participante']}'")
        if payload.get("agencia") and payload.get("conta"):
            where_clauses.append(f"agencia = '{payload['agencia']}' AND conta = '{payload['conta']}'")
        if payload.get("tipo_pessoa"):
            where_clauses.append(f"tipo_pessoa = '{payload['tipo_pessoa']}'")
        where_clause = " AND ".join(where_clauses)
        query = f"""
        SELECT * 
        FROM {self.table_name}
        WHERE {where_clause}
        """
        return query.strip()
