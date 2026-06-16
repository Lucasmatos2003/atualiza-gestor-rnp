import pandas as pd
import re
import unicodedata


def normalizar_texto(texto):
    if pd.isna(texto):
        return ""

    texto = str(texto).strip()

    texto = unicodedata.normalize("NFD", texto)
    texto = texto.encode("ascii", "ignore")
    texto = texto.decode("utf-8")

    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


def normalizar_coluna(coluna):
    texto = normalizar_texto(coluna).lower()

    texto = texto.replace("_", " ")
    texto = texto.replace("-", " ")
    texto = texto.replace("/", " ")
    texto = texto.replace("(", " ")
    texto = texto.replace(")", " ")

    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


def limpar_valor(valor):
    if pd.isna(valor):
        return None

    valor = str(valor).strip()
    valor = re.sub(r"\s+", " ", valor)

    if valor.lower() in [
        "",
        "nan",
        "none",
        "-",
        "não possui",
        "nao possui",
        "não informado",
        "nao informado"
    ]:
        return None

    return valor


def limpar_inep(valor):
    if pd.isna(valor):
        return None

    valor = re.sub(r"\D", "", str(valor))

    if valor:
        return valor

    return None


def limpar_telefone(telefone):
    if pd.isna(telefone):
        return None

    telefone = str(telefone)

    telefones = re.findall(
        r"(?:\(?\d{2}\)?\s*)?\d?\s?\d{4,5}[-\s]?\d{4}",
        telefone
    )

    if telefones:
        return re.sub(r"\D", "", telefones[0])

    telefone_limpo = re.sub(r"\D", "", telefone)

    if len(telefone_limpo) >= 8:
        return telefone_limpo

    return None


def limpar_email(email):
    if pd.isna(email):
        return None

    email = str(email).strip()

    emails = re.findall(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        email
    )

    if emails:
        return emails[0].lower()

    return None


def limpar_dataframe_bruto(df):
    df = df.copy()

    df = df.dropna(how="all")
    df = df.dropna(axis=1, how="all")

    novas_colunas = []
    contador = {}

    for i, coluna in enumerate(df.columns):
        nome = str(coluna).strip()

        if nome == "" or nome.lower().startswith("unnamed") or nome.lower() == "nan":
            nome = f"Coluna {i + 1}"

        if nome in contador:
            contador[nome] += 1
            nome = f"{nome}_{contador[nome]}"
        else:
            contador[nome] = 1

        novas_colunas.append(nome)

    df.columns = novas_colunas

    return df.reset_index(drop=True)


def listar_abas_excel(arquivo):
    arquivo.seek(0)

    excel = pd.ExcelFile(arquivo)

    return excel.sheet_names


def ler_excel_bruto(
    arquivo,
    aba,
    linha_cabecalho=0,
    sem_cabecalho=False
):
    arquivo.seek(0)

    if sem_cabecalho:
        df = pd.read_excel(
            arquivo,
            sheet_name=aba,
            header=None,
            dtype=str
        )

        df = limpar_dataframe_bruto(df)

        df.columns = [
            f"Coluna {i + 1}"
            for i in range(len(df.columns))
        ]

        return df

    df = pd.read_excel(
        arquivo,
        sheet_name=aba,
        header=linha_cabecalho,
        dtype=str
    )

    return limpar_dataframe_bruto(df)


def ler_csv_bruto(arquivo):
    codificacoes = [
        "utf-8-sig",
        "utf-8",
        "latin1",
        "cp1252",
        "iso-8859-1"
    ]

    separadores = [
        ";",
        ",",
        "\t",
        "|"
    ]

    for encoding in codificacoes:
        for sep in separadores:
            try:
                arquivo.seek(0)

                df = pd.read_csv(
                    arquivo,
                    encoding=encoding,
                    sep=sep,
                    dtype=str
                )

                if df is not None and not df.empty and len(df.columns) > 1:
                    return limpar_dataframe_bruto(df)

            except Exception:
                continue

    arquivo.seek(0)

    df = pd.read_csv(
        arquivo,
        encoding="latin1",
        sep=None,
        engine="python",
        dtype=str
    )

    return limpar_dataframe_bruto(df)


def sugerir_coluna(df, tipo_campo):
    palavras = {
        "inep": [
            "inep",
            "codigo inep",
            "código inep",
            "codigo mec",
            "código mec",
            "mec"
        ],
        "escola": [
            "escola",
            "unidade escolar",
            "unidade",
            "instituicao",
            "instituição",
            "nome da escola"
        ],
        "gestor": [
            "gestor",
            "gestao",
            "gestão",
            "diretor",
            "diretora",
            "direcao",
            "direção",
            "responsavel",
            "responsável",
            "nome do gestor",
            "nome diretor"
        ],
        "telefone": [
            "telefone",
            "contato",
            "celular",
            "whatsapp",
            "fone",
            "telefone da gestao",
            "telefone da gestão"
        ],
        "email": [
            "email",
            "e-mail",
            "e mail",
            "correio",
            "email gestor",
            "email da gestao",
            "e-mail da gestão"
        ],
        "municipio": [
            "municipio",
            "município",
            "cidade"
        ]
    }

    opcoes = palavras.get(tipo_campo, [])

    for coluna in df.columns:
        coluna_norm = normalizar_coluna(coluna)

        for palavra in opcoes:
            palavra_norm = normalizar_coluna(palavra)

            if palavra_norm in coluna_norm:
                return coluna

    return "Não usar"


def padronizar_por_mapeamento(
    df,
    coluna_escola,
    coluna_gestor,
    coluna_telefone,
    coluna_email,
    coluna_inep=None,
    coluna_municipio=None,
    origem="Mapeamento manual"
):
    dados = []

    for _, linha in df.iterrows():
        inep = None

        if coluna_inep and coluna_inep != "Não usar":
            inep = linha.get(coluna_inep)

        escola = linha.get(coluna_escola) if coluna_escola != "Não usar" else None
        gestor = linha.get(coluna_gestor) if coluna_gestor != "Não usar" else None
        telefone = linha.get(coluna_telefone) if coluna_telefone != "Não usar" else None
        email = linha.get(coluna_email) if coluna_email != "Não usar" else None

        municipio = None

        if coluna_municipio and coluna_municipio != "Não usar":
            municipio = linha.get(coluna_municipio)

        inep = limpar_inep(inep)
        escola = limpar_valor(escola)
        gestor = limpar_valor(gestor)
        telefone = limpar_telefone(telefone)
        email = limpar_email(email)
        municipio = limpar_valor(municipio)

        if escola or gestor or telefone or email:
            dados.append({
                "inep": inep,
                "escola": escola,
                "gestor": gestor,
                "telefone": telefone,
                "email": email,
                "municipio": municipio,
                "origem": origem
            })

    df_final = pd.DataFrame(dados)

    if df_final.empty:
        return pd.DataFrame(columns=[
            "inep",
            "escola",
            "gestor",
            "telefone",
            "email",
            "municipio",
            "origem"
        ])

    df_final = df_final.drop_duplicates(
        subset=["inep", "escola", "gestor", "telefone", "email"],
        keep="first"
    )

    return df_final.reset_index(drop=True)