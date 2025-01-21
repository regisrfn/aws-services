
QUERY_TEMPLATE = """ 
SELECT * 
FROM tb_detalhamento_spec 
WHERE data_inicio_vinculo BETWEEN '{data_inicio}' AND '{data_fim}' 
  AND numero_cnpj_base_instituicao_financeira = '{cnpj_base_participante}' 
  AND agencia_conta = '{agencia}' 
  AND numero_conta = '{conta}' 
  AND tipo_pessoa = '{tipo_pessoa}';
"""
