import datetime
from collections import defaultdict

def parse_date(date_str):
    # Converte a string no formato 'YYYY-MM-DD' para um objeto date
    return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()

def merge_intervals(intervals):
    """
    Mescla intervalos de datas.
    Se um intervalo estiver completamente contido no anterior, ele é ignorado.
    Se os intervalos se sobrepõem, é calculado o mínimo data_inicio e o máximo data_fim.
    """
    # Ordena os intervalos pela data de início
    intervals.sort(key=lambda x: x[0])
    merged = []
    
    for interval in intervals:
        if not merged:
            merged.append(interval)
        else:
            last_start, last_end = merged[-1]
            current_start, current_end = interval
            # Se o intervalo atual está completamente contido no último, ignora-o
            if current_start >= last_start and current_end <= last_end:
                continue
            # Se há sobreposição (ou continuidade), atualiza a data fim
            elif current_start <= last_end:
                merged[-1] = (last_start, max(last_end, current_end))
            else:
                # Caso não haja sobreposição, adiciona como novo intervalo
                merged.append(interval)
    return merged

# Exemplo de dados (lista de dicionários)
records = [
    {
        "codigo_identificacao_pessoa": "685cb284-9c75-4e4e-8500-bd3b3aef91de",
        "data_inicio_vinculo": "1995-10-01",
        "data_fim_vinculo": "2007-06-06"
    },
    {
        "codigo_identificacao_pessoa": "685cb284-9c75-4e4e-8500-bd3b3aef91de",
        "data_inicio_vinculo": "2001-02-17",
        "data_fim_vinculo": "2003-10-07"
    },
    {
        "codigo_identificacao_pessoa": "685cb284-9c75-4e4e-8500-bd3b3aef91de",
        "data_inicio_vinculo": "2001-02-17",
        "data_fim_vinculo": "2009-10-07"
    }
]

# Agrupa os registros pela identificação
grupos = defaultdict(list)
for rec in records:
    id_pessoa = rec["codigo_identificacao_pessoa"]
    data_inicio = parse_date(rec["data_inicio_vinculo"])
    data_fim = parse_date(rec["data_fim_vinculo"])
    grupos[id_pessoa].append((data_inicio, data_fim))

# Para cada grupo, mescla os intervalos
resultado = {}
for id_pessoa, intervalos in grupos.items():
    intervalos_mesclados = merge_intervals(intervalos)
    # Se houver mais de um intervalo após a mesclagem, você pode optar por tratá-los separadamente.
    # Aqui, assumimos que os intervalos se fundem em um único intervalo.
    if intervalos_mesclados:
        inicio, fim = intervalos_mesclados[0]
        resultado[id_pessoa] = {"data_inicio": inicio, "data_fim": fim}

# Exibe o resultado final
for id_pessoa, datas in resultado.items():
    print(f"ID: {id_pessoa}, Data Início: {datas['data_inicio']}, Data Fim: {datas['data_fim']}")
