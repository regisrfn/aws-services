from app.constants import Constants
from app.services.data_service import PayloadModel

class QueryBuilder:
    def __init__(self, table_name: str = Constants.TABLE_NAME):
        self.table_name = table_name

    def build_query(self, payload: PayloadModel) -> str:
        where_clauses = []
        if payload.tipo_arquivo:
            where_clauses.append(f"tipo_arquivo = '{payload.tipo_arquivo}'")
        if payload.numero_documento:
            where_clauses.append(f"numero_documento = '{payload.numero_documento}'")
        if payload.data_inicio:
            if payload.data_fim:
                where_clauses.append(f"data_vinculo BETWEEN '{payload.data_inicio}' AND '{payload.data_fim}'")
            else:
                where_clauses.append(f"data_vinculo >= '{payload.data_inicio}'")
        if payload.cnpj_base_participante:
            where_clauses.append(f"cnpj_base_participante = '{payload.cnpj_base_participante}'")
        if payload.agencia and payload.conta:
            where_clauses.append(f"agencia = '{payload.agencia}' AND conta = '{payload.conta}'")
        if payload.tipo_pessoa:
            where_clauses.append(f"tipo_pessoa = '{payload.tipo_pessoa}'")

        where_clause = " AND ".join(where_clauses)
        query = f"""
        SELECT * 
        FROM {self.table_name}
        WHERE {where_clause}
        """
        return query.strip()
