import pandas as pd
import re
import unicodedata

from rapidfuzz import process, fuzz


LIMITE_ENCONTRADA = 90
LIMITE_REVISAR = 80


def normalizar_texto(texto):
    if pd.isna(texto):
        return ""

    texto = str(texto).strip().upper()

    texto = unicodedata.normalize("NFD", texto)
    texto = texto.encode("ascii", "ignore")
    texto = texto.decode("utf-8")

    texto = texto.replace(".", " ")
    texto = texto.replace("-", " ")
    texto = texto.replace("_", " ")
    texto = texto.replace("/", " ")

    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


def limpar_nome_escola(nome):
    nome = normalizar_texto(nome)

    termos_remover = [
        r"\bUNIDADE DE ACOLHIMENTO A CRIANCA DO PROGRAMA NOVA SEMENTE\b",
        r"\bUNIDADE DE ACOLHIMENTO A CRIANCA\b",
        r"\bPROGRAMA NOVA SEMENTE\b",
        r"\bNOVA SEMENTE\b",

        r"\bESCOLA MUNICIPAL DE ENSINO FUNDAMENTAL E EDUCACAO INFANTIL\b",
        r"\bESCOLA MUNICIPAL DE ENSINO FUNDAMENTAL\b",
        r"\bESCOLA MUNICIPAL DE EDUCACAO INFANTIL\b",
        r"\bESCOLA ESTADUAL DE ENSINO FUNDAMENTAL E MEDIO\b",
        r"\bESCOLA ESTADUAL DE ENSINO FUNDAMENTAL\b",
        r"\bESCOLA ESTADUAL DE ENSINO MEDIO\b",
        r"\bESCOLA MUNICIPAL\b",
        r"\bESCOLA ESTADUAL\b",
        r"\bESCOLA\b",

        r"\bCENTRO MUNICIPAL DE EDUCACAO INFANTIL\b",
        r"\bCENTRO DE EDUCACAO INFANTIL\b",

        r"\bEMEIEF\b",
        r"\bEMEIF\b",
        r"\bEMEITI\b",
        r"\bEMEF\b",
        r"\bEMEI\b",
        r"\bEEEFM\b",
        r"\bEEEF\b",
        r"\bEEEM\b",
        r"\bEEM\b",
        r"\bEE\b",
        r"\bEM\b",
        r"\bCMEI\b",
        r"\bCM\b",
        r"\bUEI\b",
        r"\bUAC\b",
        r"\bEREM\b"
    ]

    for termo in termos_remover:
        nome = re.sub(termo, " ", nome)

    nome = re.sub(r"\s+", " ", nome)

    return nome.strip()


def preparar_documento(df_novo):
    df = df_novo.copy()

    colunas_necessarias = [
        "escola",
        "gestor",
        "telefone",
        "email",
        "municipio",
        "origem"
    ]

    for coluna in colunas_necessarias:
        if coluna not in df.columns:
            df[coluna] = None

    df["escola_limpa"] = df["escola"].apply(limpar_nome_escola)

    df = df[df["escola_limpa"].notna()]
    df = df[df["escola_limpa"].astype(str).str.strip() != ""]

    return df


def preparar_base_topdesk(df_topdesk):
    df = df_topdesk.copy()

    colunas_necessarias = [
        "escola",
        "gestor_atual",
        "email_atual",
        "numero_chamado",
        "data_abertura",
        "data_fechamento",
        "data_referencia",
        "status_chamado",
        "fila",
        "resumo"
    ]

    for coluna in colunas_necessarias:
        if coluna not in df.columns:
            df[coluna] = None

    df["escola_limpa"] = df["escola"].apply(limpar_nome_escola)

    df = df[df["escola_limpa"].notna()]
    df = df[df["escola_limpa"].astype(str).str.strip() != ""]

    return df


def definir_status_dados(
    similaridade,
    gestor_novo,
    gestor_topdesk,
    email_novo,
    email_topdesk
):
    if similaridade < LIMITE_REVISAR:
        return "Não encontrada no documento"

    if similaridade < LIMITE_ENCONTRADA:
        return "Possível correspondência - revisar manualmente"

    gestor_novo_norm = normalizar_texto(gestor_novo)
    gestor_topdesk_norm = normalizar_texto(gestor_topdesk)

    email_novo_norm = normalizar_texto(email_novo)
    email_topdesk_norm = normalizar_texto(email_topdesk)

    diferencas = []

    if gestor_novo_norm and gestor_topdesk_norm:
        if gestor_novo_norm != gestor_topdesk_norm:
            diferencas.append("gestor")
    elif gestor_novo_norm and not gestor_topdesk_norm:
        diferencas.append("gestor não encontrado no TopDesk")
    elif gestor_topdesk_norm and not gestor_novo_norm:
        diferencas.append("gestor não encontrado no documento")

    if email_novo_norm and email_topdesk_norm:
        if email_novo_norm != email_topdesk_norm:
            diferencas.append("e-mail")
    elif email_novo_norm and not email_topdesk_norm:
        diferencas.append("e-mail não encontrado no TopDesk")
    elif email_topdesk_norm and not email_novo_norm:
        diferencas.append("e-mail não encontrado no documento")

    if len(diferencas) == 0:
        return "Dados iguais - não precisa atualizar"

    return "Atualizar/Revisar no TopDesk: " + ", ".join(diferencas)


def comparar_com_topdesk(df_novo, df_topdesk):
    """
    Regra correta:
    - TopDesk/Fabric é a base oficial das escolas do projeto.
    - O documento pode conter escolas fora do projeto.
    - Então a comparação percorre as escolas do TopDesk e tenta encontrar no documento.
    """

    df_documento = preparar_documento(df_novo)
    df_topdesk = preparar_base_topdesk(df_topdesk)

    resultados = []

    escolas_documento_limpa = df_documento["escola_limpa"].dropna().tolist()

    for _, linha_topdesk in df_topdesk.iterrows():
        escola_topdesk = linha_topdesk.get("escola")
        escola_topdesk_limpa = linha_topdesk.get("escola_limpa")

        melhor_match = process.extractOne(
            escola_topdesk_limpa,
            escolas_documento_limpa,
            scorer=fuzz.token_set_ratio
        )

        if not melhor_match:
            resultados.append({
                "escola_topdesk": escola_topdesk,
                "chave_topdesk": escola_topdesk_limpa,
                "escola_documento": None,
                "chave_documento": None,
                "similaridade": 0,
                "gestor_documento": None,
                "gestor_topdesk": linha_topdesk.get("gestor_atual"),
                "email_documento": None,
                "email_topdesk": linha_topdesk.get("email_atual"),
                "telefone_documento": None,
                "numero_chamado": linha_topdesk.get("numero_chamado"),
                "data_abertura": linha_topdesk.get("data_abertura"),
                "data_fechamento": linha_topdesk.get("data_fechamento"),
                "data_referencia": linha_topdesk.get("data_referencia"),
                "status_chamado": linha_topdesk.get("status_chamado"),
                "fila": linha_topdesk.get("fila"),
                "status_comparacao": "Não encontrada no documento"
            })
            continue

        escola_documento_limpa, similaridade, indice = melhor_match

        if similaridade < LIMITE_REVISAR:
            resultados.append({
                "escola_topdesk": escola_topdesk,
                "chave_topdesk": escola_topdesk_limpa,
                "escola_documento": None,
                "chave_documento": None,
                "similaridade": similaridade,
                "gestor_documento": None,
                "gestor_topdesk": linha_topdesk.get("gestor_atual"),
                "email_documento": None,
                "email_topdesk": linha_topdesk.get("email_atual"),
                "telefone_documento": None,
                "numero_chamado": linha_topdesk.get("numero_chamado"),
                "data_abertura": linha_topdesk.get("data_abertura"),
                "data_fechamento": linha_topdesk.get("data_fechamento"),
                "data_referencia": linha_topdesk.get("data_referencia"),
                "status_chamado": linha_topdesk.get("status_chamado"),
                "fila": linha_topdesk.get("fila"),
                "status_comparacao": "Não encontrada no documento"
            })
            continue

        linha_documento = df_documento.iloc[indice]

        status_comparacao = definir_status_dados(
            similaridade=similaridade,
            gestor_novo=linha_documento.get("gestor"),
            gestor_topdesk=linha_topdesk.get("gestor_atual"),
            email_novo=linha_documento.get("email"),
            email_topdesk=linha_topdesk.get("email_atual")
        )

        resultados.append({
            "escola_topdesk": escola_topdesk,
            "chave_topdesk": escola_topdesk_limpa,
            "escola_documento": linha_documento.get("escola"),
            "chave_documento": linha_documento.get("escola_limpa"),
            "similaridade": similaridade,
            "gestor_documento": linha_documento.get("gestor"),
            "gestor_topdesk": linha_topdesk.get("gestor_atual"),
            "email_documento": linha_documento.get("email"),
            "email_topdesk": linha_topdesk.get("email_atual"),
            "telefone_documento": linha_documento.get("telefone"),
            "numero_chamado": linha_topdesk.get("numero_chamado"),
            "data_abertura": linha_topdesk.get("data_abertura"),
            "data_fechamento": linha_topdesk.get("data_fechamento"),
            "data_referencia": linha_topdesk.get("data_referencia"),
            "status_chamado": linha_topdesk.get("status_chamado"),
            "fila": linha_topdesk.get("fila"),
            "status_comparacao": status_comparacao
        })

    return pd.DataFrame(resultados)