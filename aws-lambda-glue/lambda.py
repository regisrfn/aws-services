# app.py

import os
import json
import io
import uuid
import logging
import datetime

import boto3
import pyarrow as pa
import pyarrow.parquet as pq

# ——————————————————————————————————————————————————————————————
# Configuração de logging
# ——————————————————————————————————————————————————————————————
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ——————————————————————————————————————————————————————————————
# Carrega o schema do Glue (lista de {"Name":..., "Type":...})
# ——————————————————————————————————————————————————————————————
with open("glue_schema.json", "r") as f:
    SCHEMA_DEFS = json.load(f)

# Map Glue types para PyArrow DataType
_TYPE_MAP = {
    "string":    pa.string(),
    "double":    pa.float64(),
    "int":       pa.int64(),
    "timestamp": pa.timestamp("ms"),
}

# Constrói o pa.Schema
_fields = []
for col in SCHEMA_DEFS:
    dtype = _TYPE_MAP.get(col["Type"])
    if dtype is None:
        raise ValueError(f"Tipo desconhecido no schema: {col['Type']}")
    _fields.append(pa.field(col["Name"], dtype))
PARQUET_SCHEMA = pa.schema(_fields)

# ——————————————————————————————————————————————————————————————
# Mapeamento de nomes JSON → nomes do schema Glue
# (quando diferente; se iguais, bastaria usar identity)
# ——————————————————————————————————————————————————————————————
FIELD_MAP = {
    "codigo_identificacao_pessoa":        "cod_idef_pess",
    "codigo_tipo_pessoa":                 "cod_tipo_pess",
    "documento_pessoa":                   "num_cpf_cnpj",
    "ano_mes_referencia":                 "txt_ano_mes_risc_bace",
    "origem_risco":                       "cod_orig_risc_bace",
    "modalidade_risco":                   "cod_moda_cred_risc_bace",
    "codigo_itau":                        None,  # não persiste
    "data_atualizacao_risco":             None,  # não persiste
    "hora_consulta_bacen":                "dat_hor_cslt_risc_bace",
    "codigo_tipo_consulta":               None,
    "codigo_tipo_envio":                  None,
    "codigo_tipo_retorno":                None,
    "codigo_tipo_autorizacao_cliente":    None,
    "codigo_tipo_publico_pesquisa":       None,
    "percentual_remessa_instituicao":     "pct_docm_prcs_risc_bace",
    "data_inicio_relacionamento":         "dat_inio_rlmt_clie_risc_bace",
    "vinculo_moeda_estrangeira":          "cod_vncl_moed_esgr_risc_bace",
    "quantidade_instituicao_financeira_risco": "qtd_inst_finn_risc_bace",
    "quantidade_operacao_financeira_cliente":  "qtd_totl_oper_finn_rspl_risc",
    "quantidade_operacao_judice_cliente":      "qtd_oper_judc_risc_bace",
    "valor_operacao_judice":              "vlr_oper_judc_resp_totl_risc",
    "quantidade_operacao_discordancia":   "qtd_oper_dsco_risc_bace",
    "valor_operacao_discordancia":        "vlr_resp_totl_dsco_risc_bace",
    # buckets “vencer”
    "valor_vencer_30":                    "vlr_cred_vncr_30_dia_risc",
    "valor_vencer_60":                    "vlr_cred_vncr_60_dia_risc",
    "valor_vencer_90":                    "vlr_cred_vncr_90_dia_risc",
    "valor_vencer_180":                   "vlr_cred_vncr_180_dia_risc",
    "valor_vencer_360":                   "vlr_cred_vncr_360_dia_risc",
    "valor_vencer_540":                   "vlr_cred_vncr_5400_dia_risc",
    "valor_vencer_acima_540":             "vlr_cred_vncr_prz_indm_risc",
    "valor_total_vencer":                 "vlr_totl_cred_vncr_risc",
    # buckets “vencido”
    "valor_vencido_14":                   "vlr_cred_vncd_14_dia_risc",
    "valor_vencido_30":                   "vlr_cred_vncd_30_dia_risc",
    "valor_vencido_60":                   "vlr_cred_vncd_60_dia_risc",
    "valor_vencido_90":                   "vlr_cred_vncd_90_dia_risc",
    "valor_vencido_120":                  "vlr_cred_vncd_120_dia_risc",
    "valor_vencido_180":                  "vlr_cred_vncd_180_dia_risc",
    "valor_vencido_240":                  "vlr_cred_vncd_240_dia_risc",
    "valor_vencido_300":                  "vlr_cred_vncd_300_dia_risc",
    "valor_vencido_360":                  "vlr_cred_vncd_360_dia_risc",
    "valor_vencido_540":                  "vlr_cred_vncd_540_dia_risc",
    "valor_vencido_acima_540":            "vlr_cred_vncd_acim_540_dia",
    "valor_total_vencido":                "vlr_totl_cred_vncd_risc",
    # crédito liberado / vencimento
    "valor_credito_liberar_ate360":       "vlr_cred_lbra_limi_360_dia",
    "valor_credito_liberar_mais360":      "vlr_cred_lbra_acim_360_dia",
    "valor_credito_liberar_total":        "vlr_totl_cred_lbra_dia_risc",
    "valor_credito_vencimento_ate360":    "vlr_cred_vcto_limi_360_dia",
    "valor_credito_vencimento_mais360":   "vlr_cred_vcto_acim_360_dia",
    "valor_credito_vencimento_total":     "vlr_totl_limi_cred_dia_risc",
    # prejuízo
    "valor_credito_prejuizo_ate12_cliente":"vlr_cred_prej_12_mes_risc",
    "valor_credito_prejuizo_12_48":       "vlr_cred_prej_48_mes_risc",
    "valor_credito_prejuizo_mais12_cliente":"vlr_prej_acim_12_mes_risc",
    "valor_credito_prejuizo_total":       "vlr_totl_cred_prej_risc",
    # flags/índices
    "percentual_informacao_bacen":        "pct_volu_prcs_risc_bace",
    # metadados finais
    "codigo_operacao":                    "cod_prco_risc_bace",
    "sistema":                            "sistema",
    "codigo_retorno":                     "codigo_retorno",
    "cliente":                            "cliente",
    "origem_consulta":                    "origem_consulta",
}

# ——————————————————————————————————————————————————————————————
# Clientes AWS e configurações via env
# ——————————————————————————————————————————————————————————————
s3   = boto3.client("s3")
glue = boto3.client("glue")

BUCKET       = os.environ["BUCKET_DADOS"]
S3_PREFIX    = os.environ.get("S3_PREFIX", "bronze/eventos").rstrip("/")
GLUE_DB      = os.environ.get("GLUE_DB")
GLUE_TABLE   = os.environ.get("GLUE_TABLE")
REGISTER_PARTITIONS = os.environ.get("REGISTER_PARTITIONS", "true").lower() == "true"

# ——————————————————————————————————————————————————————————————
# Funções auxiliares
# ——————————————————————————————————————————————————————————————
def parse_sns_envelope(body: str) -> dict:
    o = json.loads(body)
    if isinstance(o, dict) and o.get("Type") == "Notification" and "Message" in o:
        try:
            return json.loads(o["Message"])
        except:
            return {"raw": o["Message"]}
    return o

def normalize(payload: dict):
    # id_evento
    payload.setdefault("id_evento", str(uuid.uuid4()))
    # ts_evento
    ts = payload.get("ts_evento")
    try:
        dt = datetime.datetime.fromisoformat(ts.replace("Z","+00:00"))
    except:
        dt = datetime.datetime.utcnow()
        payload["ts_evento"] = dt.isoformat()
    # particionamento
    payload["anomesdia"] = dt.strftime("%Y%m%d")
    payload["hh"]        = dt.strftime("%H")

def map_and_convert(raw: dict) -> dict:
    out = {}
    for json_key, col_name in FIELD_MAP.items():
        if col_name is None:
            continue
        v = raw.get(json_key)
        if v is None:
            out[col_name] = None
            continue
        dtype = PARQUET_SCHEMA.field(col_name).type
        # converte
        if pa.types.is_int64(dtype):
            try:    out[col_name] = int(v)
            except: out[col_name] = None
        elif pa.types.is_float64(dtype):
            try:    out[col_name] = float(v)
            except: out[col_name] = None
        else:
            out[col_name] = str(v)
    # adiciona cols de partição (já em string)
    out["anomesdia"] = raw.get("anomesdia")
    out["hh"]        = raw.get("hh")
    return out

def write_parquet(records: list[dict]):
    if not records:
        return None
    # monta colunas
    data = {f.name: [] for f in PARQUET_SCHEMA}
    for rec in records:
        for f in PARQUET_SCHEMA:
            data[f.name].append(rec.get(f.name))
    table = pa.Table.from_pydict(data, schema=PARQUET_SCHEMA)
    buf = io.BytesIO()
    pq.write_table(table, buf, compression="snappy")
    buf.seek(0)
    d = records[0]["anomesdia"]
    h = records[0]["hh"]
    key = f"{S3_PREFIX}/anomesdia={d}/hh={h}/lote-{uuid.uuid4()}.parquet"
    s3.put_object(Bucket=BUCKET, Key=key, Body=buf.getvalue())
    return key, d, h

def register_partition(d: str, h: str):
    loc = f"s3://{BUCKET}/{S3_PREFIX}/anomesdia={d}/hh={h}/"
    try:
        glue.batch_create_partition(
            DatabaseName=GLUE_DB,
            TableName=GLUE_TABLE,
            PartitionInputList=[{
                "Values": [d, h],
                "StorageDescriptor": {
                  "Columns": [
                    {"Name": f.name, "Type": str(f.type)} for f in PARQUET_SCHEMA
                  ],
                  "Location": loc,
                  "InputFormat":  "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
                  "OutputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
                  "SerdeInfo": {
                    "SerializationLibrary":"org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
                  }
                }
            }]
        )
    except glue.exceptions.AlreadyExistsException:
        pass
    except Exception as e:
        logger.error(f"Erro ao registrar partição {d}/{h}: {e}")

# ——————————————————————————————————————————————————————————————
# Handler
# ——————————————————————————————————————————————————————————————
def handler(event, context):
    processed = []
    failures  = []

    for rec in event.get("Records", []):
        mid = rec["messageId"]
        try:
            raw = parse_sns_envelope(rec["body"])
            normalize(raw)
            mapped = map_and_convert(raw)
            processed.append(mapped)
        except Exception as e:
            logger.warning(f"Falha ao processar mensagem {mid}: {e}")
            failures.append({ "itemIdentifier": mid })

    result = write_parquet(processed)
    if result and REGISTER_PARTITIONS:
        _, d, h = result
        register_partition(d, h)

    logger.info({
        "batch_received": len(event.get("Records", [])),
        "processed":      len(processed),
        "failures":       [f["itemIdentifier"] for f in failures],
        "parquet":        result[0] if result else None
    })

    return { "batchItemFailures": failures }
