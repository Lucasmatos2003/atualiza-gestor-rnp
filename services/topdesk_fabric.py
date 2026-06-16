import pandas as pd
from fabric_connector import FabricConnector


def buscar_chamados_topdesk(fila_escolhida=None):
    if fila_escolhida and fila_escolhida != "Todas":
        filtro_fila = f"AND operatorGroups = 'Educação Conectada::{fila_escolhida}'"
    else:
        filtro_fila = "AND operatorGroups LIKE 'Educação Conectada%'"

    query = f"""
        SELECT
            incidentNumber,
            creationDate,
            closureDate,
            statusName,
            operatorGroups,
            categoryName,
            subCategoryName,
            priority,
            Resumo,
            reporterName,
            reporterEmail,
            branchesName,
            COALESCE(closureDate, creationDate) AS dataReferencia
        FROM dbo.Topdesk_Incidents_Full
        WHERE branchesName IS NOT NULL
        {filtro_fila}
        ORDER BY dataReferencia DESC
    """

    with FabricConnector() as connector:
        resultados = connector.execute_query(query)

    df = pd.DataFrame(resultados)

    if df.empty:
        return df

    df = df.rename(columns={
        "incidentNumber": "numero_chamado",
        "creationDate": "data_abertura",
        "closureDate": "data_fechamento",
        "statusName": "status_chamado",
        "operatorGroups": "fila",
        "categoryName": "categoria",
        "subCategoryName": "subcategoria",
        "priority": "prioridade",
        "Resumo": "resumo",
        "reporterName": "gestor_atual",
        "reporterEmail": "email_atual",
        "branchesName": "escola",
        "dataReferencia": "data_referencia"
    })

    df["data_abertura"] = pd.to_datetime(
        df["data_abertura"],
        errors="coerce"
    )

    df["data_fechamento"] = pd.to_datetime(
        df["data_fechamento"],
        errors="coerce"
    )

    df["data_referencia"] = pd.to_datetime(
        df["data_referencia"],
        errors="coerce"
    )

    df = df.sort_values(
        "data_referencia",
        ascending=False
    )

    df_ultimo_por_escola = df.drop_duplicates(
        subset=["escola"],
        keep="first"
    )

    return df_ultimo_por_escola.reset_index(drop=True)