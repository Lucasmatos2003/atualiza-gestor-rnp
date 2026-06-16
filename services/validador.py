import pandas as pd
import re


def limpar_valor(valor):
    if valor is None or pd.isna(valor):
        return None

    valor = str(valor).replace("\xa0", " ").strip()
    valor = re.sub(r"\s+", " ", valor)

    if valor.lower() in [
        "",
        "nan",
        "none",
        "-",
        "não informado",
        "nao informado",
        "não possui",
        "nao possui",
        "n/a"
    ]:
        return None

    return valor


def limpar_inep(valor):
    if valor is None or pd.isna(valor):
        return None

    valor = re.sub(r"\D", "", str(valor))

    if valor:
        return valor

    return None


def limpar_telefone(valor):
    if valor is None or pd.isna(valor):
        return None

    valor = str(valor)

    telefones = re.findall(
        r"(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?\d?\s?\d{4,5}[-\s]?\d{4}",
        valor
    )

    if telefones:
        telefone = re.sub(r"\D", "", telefones[0])

        if telefone.startswith("55") and len(telefone) in [12, 13]:
            telefone = telefone[2:]

        if len(telefone) >= 8:
            return telefone

    telefone = re.sub(r"\D", "", valor)

    if telefone.startswith("55") and len(telefone) in [12, 13]:
        telefone = telefone[2:]

    if len(telefone) >= 8:
        return telefone

    return None


def limpar_email(valor):
    if valor is None or pd.isna(valor):
        return None

    valor = str(valor).strip()

    emails = re.findall(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        valor
    )

    if emails:
        return emails[0].lower()

    return None


def validar_campos_obrigatorios(df):
    if df is None or df.empty:
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
            "fonte_contato",
            "status_validacao"
        ])

    df = df.copy()

    colunas_padrao = [
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
    ]

    for coluna in colunas_padrao:
        if coluna not in df.columns:
            df[coluna] = None

    df["inep"] = df["inep"].apply(limpar_inep)
    df["escola"] = df["escola"].apply(limpar_valor)
    df["gestor"] = df["gestor"].apply(limpar_valor)
    df["telefone"] = df["telefone"].apply(limpar_telefone)
    df["telefone_2"] = df["telefone_2"].apply(limpar_telefone)
    df["telefone_3"] = df["telefone_3"].apply(limpar_telefone)
    df["email"] = df["email"].apply(limpar_email)
    df["municipio"] = df["municipio"].apply(limpar_valor)
    df["origem"] = df["origem"].apply(limpar_valor)
    df["fonte_contato"] = df["fonte_contato"].apply(limpar_valor)

    status = []

    for _, linha in df.iterrows():
        faltando = []

        if not linha.get("escola"):
            faltando.append("escola")

        if not linha.get("gestor"):
            faltando.append("gestor")

        if not linha.get("telefone"):
            faltando.append("telefone")

        if not linha.get("email"):
            faltando.append("e-mail")

        if faltando:
            status.append(
                "Faltando: " + ", ".join(faltando)
            )
        else:
            status.append(
                "Completo para atualizar no TopDesk"
            )

    df["status_validacao"] = status

    return df