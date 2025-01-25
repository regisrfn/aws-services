def build_athena_query(cnpj: str, agencia: str, conta: str) -> str:
    return f"""
    SELECT * FROM tb_detalhamento_spec
    WHERE cnpj_base_participante = '{cnpj}'
      AND agencia = '{agencia}'
      AND conta = '{conta}'
    """
