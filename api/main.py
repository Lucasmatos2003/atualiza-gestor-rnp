from typing import List, Dict, Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from fabric_connector import FabricConnector
from services.topdesk_fabric import buscar_chamados_topdesk
from services.comparador_topdesk import comparar_com_topdesk


app = FastAPI(
    title="AtualizaGestor API",
    description="API para comunicação entre o Streamlit e o Fabric/TopDesk",
    version="1.0.0"
)


class ComparacaoRequest(BaseModel):
    cidade: str = "Todas"
    dados_extraidos: List[Dict[str, Any]]


def dataframe_para_json(df):
    if df is None or df.empty:
        return []

    df = df.copy()

    for coluna in df.columns:
        df[coluna] = df[coluna].apply(
            lambda valor: valor.isoformat() if hasattr(valor, "isoformat") else valor
        )

    df = df.where(df.notna(), None)

    return df.to_dict(orient="records")


def montar_metricas_comparacao(df_comparacao):
    if df_comparacao is None or df_comparacao.empty:
        return {
            "total": 0,
            "atualizar": 0,
            "dados_iguais": 0,
            "revisar": 0,
            "nao_encontradas": 0
        }

    total = len(df_comparacao)

    atualizar = df_comparacao[
        df_comparacao["status_comparacao"].astype(str).str.contains(
            "Atualizar",
            case=False,
            na=False
        )
    ].shape[0]

    dados_iguais = df_comparacao[
        df_comparacao["status_comparacao"].astype(str).str.contains(
            "Dados iguais",
            case=False,
            na=False
        )
    ].shape[0]

    revisar = df_comparacao[
        df_comparacao["status_comparacao"].astype(str).str.contains(
            "revisar",
            case=False,
            na=False
        )
    ].shape[0]

    nao_encontradas = df_comparacao[
        df_comparacao["status_comparacao"].astype(str).str.contains(
            "Não encontrada",
            case=False,
            na=False
        )
    ].shape[0]

    return {
        "total": total,
        "atualizar": atualizar,
        "dados_iguais": dados_iguais,
        "revisar": revisar,
        "nao_encontradas": nao_encontradas
    }


@app.get("/")
def home():
    return {
        "mensagem": "AtualizaGestor API está online"
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "servico": "AtualizaGestor API"
    }


@app.get("/fabric/health")
def fabric_health():
    try:
        query = """
            SELECT 1 AS conectado
        """

        with FabricConnector() as connector:
            resultado = connector.execute_query(query)

        return {
            "status": "ok",
            "mensagem": "Conexão com Fabric realizada com sucesso",
            "resultado": resultado
        }

    except Exception as erro:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao conectar no Fabric: {str(erro)}"
        )


@app.get("/topdesk/escolas")
def topdesk_escolas(
    cidade: str = Query(default="Todas"),
    limite: int = Query(default=20)
):
    try:
        df_topdesk = buscar_chamados_topdesk(cidade)

        total_encontrado = len(df_topdesk)

        if limite and limite > 0:
            df_retorno = df_topdesk.head(limite)
        else:
            df_retorno = df_topdesk

        dados = dataframe_para_json(df_retorno)

        return {
            "status": "ok",
            "cidade": cidade,
            "total_encontrado": total_encontrado,
            "total_retorno": len(dados),
            "dados": dados
        }

    except Exception as erro:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar dados do TopDesk/Fabric: {str(erro)}"
        )


@app.post("/topdesk/comparar")
def topdesk_comparar(payload: ComparacaoRequest):
    try:
        if not payload.dados_extraidos:
            raise HTTPException(
                status_code=400,
                detail="Nenhum dado extraído foi enviado para comparação."
            )

        df_extraido = pd.DataFrame(payload.dados_extraidos)

        df_topdesk = buscar_chamados_topdesk(payload.cidade)

        if df_topdesk is None or df_topdesk.empty:
            return {
                "status": "ok",
                "cidade": payload.cidade,
                "mensagem": "Nenhum dado encontrado no TopDesk/Fabric para a cidade informada.",
                "total_topdesk": 0,
                "total_extraido": len(df_extraido),
                "metricas": montar_metricas_comparacao(pd.DataFrame()),
                "dados": []
            }

        df_comparacao = comparar_com_topdesk(
            df_extraido,
            df_topdesk
        )

        metricas = montar_metricas_comparacao(df_comparacao)

        dados = dataframe_para_json(df_comparacao)

        return {
            "status": "ok",
            "cidade": payload.cidade,
            "total_topdesk": len(df_topdesk),
            "total_extraido": len(df_extraido),
            "metricas": metricas,
            "dados": dados
        }

    except HTTPException:
        raise

    except Exception as erro:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao comparar dados com TopDesk/Fabric: {str(erro)}"
        )