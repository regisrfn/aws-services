import os, json, uuid, datetime, io, logging
import boto3
import pyarrow as pa
import pyarrow.parquet as pq

# --- Config ---
BUCKET        = os.environ["BUCKET_DADOS"]
GLUE_DB       = os.environ["GLUE_DB"]
GLUE_TABLE    = os.environ["GLUE_TABLE"]
S3_PREFIX     = os.environ.get("S3_PREFIX", "bronze/eventos").rstrip("/")
REGISTER_PART = os.environ.get("REGISTER_PARTITIONS", "true").lower() == "true"
LOG_LEVEL     = os.environ.get("LOG_LEVEL", "INFO").upper()

logging.getLogger().setLevel(LOG_LEVEL)
logger = logging.getLogger(__name__)

s3   = boto3.client("s3")
glue = boto3.client("glue")

# --- Helpers ---

def parse_envelope(body_raw: str):
    """
    Lida com duas possibilidades:
    1. Payload direto JSON
    2. Envelope SNS (Type=Notification, field 'Message')
    """
    try:
        outer = json.loads(body_raw)
    except json.JSONDecodeError:
        return None

    # Envelope SNS
    if isinstance(outer, dict) and outer.get("Type") == "Notification" and "Message" in outer:
        inner_raw = outer["Message"]
        try:
            inner = json.loads(inner_raw)
        except Exception:
            inner = {"raw_message": inner_raw}
        # Pode extrair atributos SNS:
        attrs = outer.get("MessageAttributes") or {}
        for k, v in attrs.items():
            key_attr = f"sns_attr_{k}"
            if key_attr not in inner:
                inner[key_attr] = v.get("Value")
        if "sns_message_id" not in inner:
            inner["sns_message_id"] = outer.get("MessageId")
        return inner
    else:
        # Payload direto
        return outer

def normalize(payload: dict):
    # id_evento
    payload.setdefault("id_evento", str(uuid.uuid4()))
    # tipo
    payload.setdefault("tipo", "desconhecido")
    # ts_evento
    ts_raw = payload.get("ts_evento")
    if ts_raw:
        try:
            dt = datetime.datetime.fromisoformat(ts_raw.replace("Z","+00:00"))
        except Exception:
            dt = datetime.datetime.utcnow()
            payload["ts_evento"] = dt.isoformat()
    else:
        dt = datetime.datetime.utcnow()
        payload["ts_evento"] = dt.isoformat()

    payload["anomesdia"] = dt.strftime("%Y%m%d")
    payload["hh"]        = dt.strftime("%H")
    return payload, dt

def build_arrow_table(records):
    # Add/convert timestamp list
    schema = pa.schema([
        pa.field("id_evento", pa.string()),
        pa.field("tipo", pa.string()),
        pa.field("ts_evento", pa.timestamp('ms')),
        pa.field("anomesdia", pa.string()),
        pa.field("hh", pa.string()),
        pa.field("sns_message_id", pa.string())
    ])

    # Ensure all keys exist
    for r in records:
        if "sns_message_id" not in r:
            r["sns_message_id"] = None

    ts_list = []
    for r in records:
        try:
            ts_list.append(datetime.datetime.fromisoformat(r["ts_evento"].replace("Z","+00:00")))
        except:
            ts_list.append(datetime.datetime.utcnow())

    table = pa.Table.from_pydict({
        "id_evento": [r["id_evento"] for r in records],
        "tipo":      [r["tipo"] for r in records],
        "ts_evento": ts_list,
        "anomesdia": [r["anomesdia"] for r in records],
        "hh":        [r["hh"] for r in records],
        "sns_message_id": [r["sns_message_id"] for r in records],
    }, schema=schema)

    return table

def write_parquet(records):
    if not records:
        return None
    table = build_arrow_table(records)
    buf = io.BytesIO()
    pq.write_table(table, buf, compression="snappy")
    buf.seek(0)
    first = records[0]
    key = f"{S3_PREFIX}/anomesdia={first['anomesdia']}/hh={first['hh']}/lote-{uuid.uuid4()}.parquet"
    s3.put_object(Bucket=BUCKET, Key=key, Body=buf.getvalue())
    return key, first['anomesdia'], first['hh']

def register_partition(anomesdia: str, hh: str):
    """Registra partição (dia,hora). Ignora se já existe."""
    location = f"s3://{BUCKET}/{S3_PREFIX}/anomesdia={anomesdia}/hh={hh}/"
    try:
        glue.batch_create_partition(
            DatabaseName=GLUE_DB,
            TableName=GLUE_TABLE,
            PartitionInputList=[{
                "Values": [anomesdia, hh],
                "StorageDescriptor": {
                    "Columns": [
                        {"Name": "id_evento", "Type": "string"},
                        {"Name": "tipo", "Type": "string"},
                        {"Name": "ts_evento", "Type": "timestamp"},
                        {"Name": "sns_message_id", "Type": "string"},
                    ],
                    "Location": location,
                    "InputFormat":  "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
                    "OutputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
                    "SerdeInfo": {
                      "SerializationLibrary":"org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
                    }
                }
            }]
        )
        logger.info(f"Partição registrada: {anomesdia}/{hh}")
    except glue.exceptions.AlreadyExistsException:
        pass
    except Exception as e:
        logger.error(f"Erro ao registrar partição {anomesdia}/{hh}: {e}")

# --- Handler ---

def handler(event, context):
    records_in = event.get("Records", [])
    processed = []
    failures  = []
    partitions = set()

    for rec in records_in:
        mid = rec["messageId"]
        try:
            payload = parse_envelope(rec["body"])
            if payload is None:
                raise ValueError("JSON inválido")
            norm, dt = normalize(payload)
            processed.append(norm)
            partitions.add((norm["anomesdia"], norm["hh"]))
        except Exception as e:
            failures.append({"itemIdentifier": mid})
            logger.warning(f"Falha mensagem {mid}: {e}")

    parquet_key = None
    if processed:
        parquet_key, day, hour = write_parquet(processed)

    # Registro de partições (opcional)
    if REGISTER_PART:
        for (d, h) in partitions:
            register_partition(d, h)

    logger.info({
        "batch_size_received": len(records_in),
        "processed": len(processed),
        "failed": len(failures),
        "parquet_key": parquet_key,
        "partitions": list(partitions)
    })

    # Partial batch response
    return {"batchItemFailures": failures}
