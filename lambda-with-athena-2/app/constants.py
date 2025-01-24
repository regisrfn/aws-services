class Constants:
    DATABASE = "nome_do_database"
    OUTPUT_BUCKET = "s3://bucket-output-athena/"
    S3_BUCKET = "nome-do-seu-bucket"
    TABLE_NAME = "tb_detalhamento_spec"
    REQUIRED_FIELDS = [
        "tipo_arquivo", "numero_documento", "data_inicio", "data_fim",
        "cnpj_base_participante", "agencia", "conta", "tipo_pessoa"
    ]
