# app.py
import os
import json
import uuid
import datetime
import io
import boto3
from decimal import Decimal

import pyarrow as pa
import pyarrow.parquet as pq

# Clientes AWS
s3   = boto3.client('s3')
glue = boto3.client('glue')

# Variáveis de ambiente
BUCKET    = os.environ['BUCKET_DADOS']
GLUE_DB   = os.environ['GLUE_DB']
GLUE_TABLE= os.environ['GLUE_TABLE']
S3_PREFIX = os.environ['S3_PREFIX'].rstrip('/')

def _decimal_to_native(val):
    if isinstance(val, list):
        return [_decimal_to_native(v) for v in val]
    if isinstance(val, dict):
        return {k: _decimal_to_native(v) for k, v in val.items()}
    if isinstance(val, Decimal):
        return float(val)
    return val

def handler(event, context):
    records_to_write = []
    failures        = []
    now_utc         = datetime.datetime.utcnow()
    part_date       = now_utc.strftime("%Y%m%d")
    part_hour       = now_utc.strftime("%H")

    # Processa cada mensagem
    for rec in event.get("Records", []):
        msg_id = rec['messageId']
        try:
            body = json.loads(rec['body'], parse_float=Decimal)
            body = _decimal_to_native(body)

            # Campos defaults
            body.setdefault("id_evento", str(uuid.uuid4()))
            body.setdefault("tipo", "desconhecido")
            body.setdefault("valor", None)

            # TS
            ts = body.get("ts_evento")
            if ts:
                try:
                    ts_dt = datetime.datetime.fromisoformat(ts.replace("Z","+00:00"))
                except:
                    ts_dt = now_utc
            else:
                ts_dt = now_utc
            body["ts_evento"] = ts_dt

            # Partições
            body["anomesdia"] = part_date
            body["hh"]        = part_hour

            records_to_write.append(body)

        except Exception as e:
            print(f"Erro na msg {msg_id}: {e}")
            failures.append({"itemIdentifier": msg_id})

    # Se não sobrou nada válido, reporta só as falhas
    if not records_to_write:
        return {"batchItemFailures": failures}

    # Esquema Arrow consistente
    schema = pa.schema([
        pa.field("id_evento", pa.string()),
        pa.field("tipo",     pa.string()),
        pa.field("valor",    pa.float64()),
        pa.field("ts_evento",pa.timestamp('ms')),
        pa.field("anomesdia",pa.string()),
        pa.field("hh",       pa.string()),
    ])

    # Constrói colunas
    cols = {f: [r[f] for r in records_to_write] for f in schema.names}
    batch = pa.record_batch([pa.array(cols[name], type=schema.field(name).type)
                              for name in schema.names],
                             schema=schema)
    table = pa.Table.from_batches([batch], schema=schema)

    # Escreve Parquet em buffer
    buf = io.BytesIO()
    pq.write_table(table, buf, compression="snappy")
    buf.seek(0)

    s3_key = f"{S3_PREFIX}/anomesdia={part_date}/hh={part_hour}/lote-{uuid.uuid4()}.parquet"
    s3.put_object(Bucket=BUCKET, Key=s3_key, Body=buf.getvalue())

    # Registra partição no Glue (ignora se já existir)
    partition = {
        "Values": [part_date, part_hour],
        "StorageDescriptor": {
            "Columns": [
                {"Name": "id_evento",  "Type": "string"},
                {"Name": "tipo",       "Type": "string"},
                {"Name": "valor",      "Type": "double"},
                {"Name": "ts_evento",  "Type": "timestamp"},
            ],
            "Location": f"s3://{BUCKET}/{S3_PREFIX}/anomesdia={part_date}/hh={part_hour}/",
            "InputFormat":  "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
            "OutputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
            "SerdeInfo": {
              "SerializationLibrary": "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
            }
        }
    }
    try:
        glue.batch_create_partition(
            DatabaseName       = GLUE_DB,
            TableName          = GLUE_TABLE,
            PartitionInputList = [partition]
        )
    except glue.exceptions.AlreadyExistsException:
        pass

    # Retorna falhas parciais (se houver)
    return {"batchItemFailures": failures}
