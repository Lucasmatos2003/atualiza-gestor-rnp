import pandas as pd

from services.extrator_excel import extrair_excel
from services.extrator_pdf import extrair_pdf
from services.extrator_word import extrair_word
from services.extrator_consolidada_contatos import extrair_consolidada_contatos
from services.mapeador_colunas import ler_csv_bruto


def ler_csv(arquivo):
    return ler_csv_bruto(arquivo)


def ler_arquivo(arquivo, municipio_filtro=None):
    nome = arquivo.name.lower()

    if nome.endswith(".xlsx") or nome.endswith(".xls"):
        try:
            df_consolidada = extrair_consolidada_contatos(arquivo)

            if df_consolidada is not None and not df_consolidada.empty:
                return df_consolidada

        except Exception:
            pass

        arquivo.seek(0)

        return extrair_excel(
            arquivo,
            municipio_filtro=municipio_filtro
        )

    elif nome.endswith(".csv"):
        return ler_csv(arquivo)

    elif nome.endswith(".pdf"):
        return extrair_pdf(arquivo)

    elif nome.endswith(".docx"):
        return extrair_word(arquivo)

    else:
        return pd.DataFrame(columns=[
            "inep",
            "escola",
            "gestor",
            "telefone",
            "telefone_2",
            "telefone_3",
            "outros_telefones",
            "email",
            "municipio",
            "origem",
            "fonte_contato"
        ])