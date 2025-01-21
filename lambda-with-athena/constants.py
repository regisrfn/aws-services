
QUERY_TEMPLATE = """
SELECT * FROM tb_detalhamento_spec
WHERE data_hor_incu_rgto BETWEEN '{data_inicio}' AND '{data_fim}'
AND cnpj_base_participante = '{cnpj_base_participante}'
AND agencia = '{agencia}'
AND conta = '{conta}'
AND tipo_pessoa = '{tipo_pessoa}';
"""
