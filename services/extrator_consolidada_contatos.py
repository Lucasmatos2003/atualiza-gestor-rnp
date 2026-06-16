import re
import unicodedata
import pandas as pd


def normalizar_texto(texto):
    if texto is None or pd.isna(texto):
        return ""

    texto = str(texto).strip().upper()

    texto = unicodedata.normalize("NFD", texto)
    texto = texto.encode("ascii", "ignore")
    texto = texto.decode("utf-8")

    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


def normalizar_coluna(coluna):
    texto = normalizar_texto(coluna).lower()

    texto = texto.replace(".", " ")
    texto = texto.replace("-", " ")
    texto = texto.replace("_", " ")
    texto = texto.replace("/", " ")

    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


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


def limpar_telefone(valor):
    if valor is None or pd.isna(valor):
        return None

    valor = str(valor)

    telefones = re.findall(
        r"(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?\d?\s?\d{4,5}[-\s]?\d{4}",
        valor
    )

    candidatos = []

    for telefone in telefones:
        numero = re.sub(r"\D", "", telefone)

        if numero.startswith("55") and len(numero) in [12, 13]:
            numero = numero[2:]

        if len(numero) in [8, 9, 10, 11]:
            candidatos.append(numero)

    if candidatos:
        return candidatos[0]

    numero = re.sub(r"\D", "", valor)

    if numero.startswith("55") and len(numero) in [12, 13]:
        numero = numero[2:]

    if len(numero) in [8, 9, 10, 11]:
        return numero

    return None


def coletar_telefones_de_valor(valor):
    if valor is None or pd.isna(valor):
        return []

    valor = str(valor)

    encontrados = re.findall(
        r"(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?\d?\s?\d{4,5}[-\s]?\d{4}",
        valor
    )

    telefones = []

    for item in encontrados:
        telefone = limpar_telefone(item)

        if telefone:
            telefones.append(telefone)

    if not telefones:
        telefone = limpar_telefone(valor)

        if telefone:
            telefones.append(telefone)

    return telefones


def ordenar_telefones(telefones):
    telefones_unicos = []

    for telefone in telefones:
        if not telefone:
            continue

        telefone = re.sub(r"\D", "", str(telefone))

        if telefone.startswith("55") and len(telefone) in [12, 13]:
            telefone = telefone[2:]

        if len(telefone) < 8:
            continue

        if telefone not in telefones_unicos:
            telefones_unicos.append(telefone)

    def prioridade(telefone):
        # Prioriza celular com DDD e nono dígito.
        if len(telefone) == 11 and telefone[2] == "9":
            return 4

        if len(telefone) == 11:
            return 3

        if len(telefone) == 10:
            return 2

        if len(telefone) == 9:
            return 1

        return 0

    telefones_unicos = sorted(
        telefones_unicos,
        key=prioridade,
        reverse=True
    )

    return telefones_unicos


def encontrar_coluna(df, opcoes):
    mapa_colunas = {
        normalizar_coluna(coluna): coluna
        for coluna in df.columns
    }

    for opcao in opcoes:
        opcao_norm = normalizar_coluna(opcao)

        if opcao_norm in mapa_colunas:
            return mapa_colunas[opcao_norm]

    for coluna_norm, coluna_original in mapa_colunas.items():
        for opcao in opcoes:
            opcao_norm = normalizar_coluna(opcao)

            if opcao_norm in coluna_norm:
                return coluna_original

    return None


def extrair_de_aba_ctts_mesma_linha(df, nome_aba):
    dados = []

    coluna_inep = encontrar_coluna(df, [
        "Cod. INEP",
        "Cod INEP",
        "INEP"
    ])

    coluna_escola = encontrar_coluna(df, [
        "Escola",
        "Unidade Escolar"
    ])

    coluna_email = encontrar_coluna(df, [
        "E-mail",
        "Email",
        "E mail"
    ])

    coluna_gestor = encontrar_coluna(df, [
        "Gestor",
        "Diretor",
        "Responsável"
    ])

    coluna_procedencia = encontrar_coluna(df, [
        "Procedência",
        "Procedencia",
        "Origem"
    ])

    colunas_contato = []

    for coluna in df.columns:
        coluna_norm = normalizar_coluna(coluna)

        if coluna_norm.startswith("contato"):
            colunas_contato.append(coluna)

    colunas_contato = sorted(
        colunas_contato,
        key=lambda c: int(re.sub(r"\D", "", str(c)) or 0)
    )

    if not coluna_inep or not coluna_escola or not colunas_contato:
        return pd.DataFrame()

    for _, linha in df.iterrows():
        inep = limpar_inep(linha.get(coluna_inep))
        escola = limpar_valor(linha.get(coluna_escola))
        gestor = limpar_valor(linha.get(coluna_gestor)) if coluna_gestor else None
        email = limpar_email(linha.get(coluna_email)) if coluna_email else None
        procedencia = limpar_valor(linha.get(coluna_procedencia)) if coluna_procedencia else None

        telefones = []

        for coluna_contato in colunas_contato:
            telefones.extend(
                coletar_telefones_de_valor(
                    linha.get(coluna_contato)
                )
            )

        telefones = ordenar_telefones(telefones)

        telefone_1 = telefones[0] if len(telefones) >= 1 else None
        telefone_2 = telefones[1] if len(telefones) >= 2 else None
        telefone_3 = telefones[2] if len(telefones) >= 3 else None
        outros_telefones = "; ".join(telefones[3:]) if len(telefones) > 3 else None

        if not escola and not inep:
            continue

        dados.append({
            "inep": inep,
            "escola": escola,
            "gestor": gestor,
            "telefone": telefone_1,
            "telefone_2": telefone_2,
            "telefone_3": telefone_3,
            "outros_telefones": outros_telefones,
            "email": email,
            "municipio": None,
            "origem": f"Consolidada contatos - {procedencia or nome_aba}",
            "fonte_contato": procedencia
        })

    return pd.DataFrame(dados)


def extrair_de_aba_um_ctt_por_linha(df, nome_aba):
    coluna_inep = encontrar_coluna(df, [
        "Cod. INEP",
        "Cod INEP",
        "INEP"
    ])

    coluna_escola = encontrar_coluna(df, [
        "Escola",
        "Unidade Escolar"
    ])

    coluna_email = encontrar_coluna(df, [
        "E-mail",
        "Email",
        "E mail"
    ])

    coluna_gestor = encontrar_coluna(df, [
        "Gestor",
        "Diretor",
        "Responsável"
    ])

    coluna_numero = encontrar_coluna(df, [
        "Número",
        "Numero",
        "Contato",
        "Telefone"
    ])

    coluna_procedencia = encontrar_coluna(df, [
        "Procedência",
        "Procedencia",
        "Origem"
    ])

    if not coluna_inep or not coluna_escola or not coluna_numero:
        return pd.DataFrame()

    registros = []

    for _, linha in df.iterrows():
        inep = limpar_inep(linha.get(coluna_inep))
        escola = limpar_valor(linha.get(coluna_escola))
        gestor = limpar_valor(linha.get(coluna_gestor)) if coluna_gestor else None
        email = limpar_email(linha.get(coluna_email)) if coluna_email else None
        telefone = limpar_telefone(linha.get(coluna_numero))
        procedencia = limpar_valor(linha.get(coluna_procedencia)) if coluna_procedencia else None

        if not inep and not escola:
            continue

        registros.append({
            "inep": inep,
            "escola": escola,
            "gestor": gestor,
            "email": email,
            "telefone": telefone,
            "procedencia": procedencia
        })

    df_registros = pd.DataFrame(registros)

    if df_registros.empty:
        return pd.DataFrame()

    dados = []

    grupos = df_registros.groupby(
        ["inep", "escola"],
        dropna=False
    )

    for (inep, escola), grupo in grupos:
        gestores = [
            limpar_valor(valor)
            for valor in grupo["gestor"].tolist()
            if limpar_valor(valor)
        ]

        emails = [
            limpar_email(valor)
            for valor in grupo["email"].tolist()
            if limpar_email(valor)
        ]

        telefones = [
            limpar_telefone(valor)
            for valor in grupo["telefone"].tolist()
            if limpar_telefone(valor)
        ]

        procedencias = [
            limpar_valor(valor)
            for valor in grupo["procedencia"].tolist()
            if limpar_valor(valor)
        ]

        telefones = ordenar_telefones(telefones)

        telefone_1 = telefones[0] if len(telefones) >= 1 else None
        telefone_2 = telefones[1] if len(telefones) >= 2 else None
        telefone_3 = telefones[2] if len(telefones) >= 3 else None
        outros_telefones = "; ".join(telefones[3:]) if len(telefones) > 3 else None

        gestor = gestores[0] if gestores else None
        email = emails[0] if emails else None
        procedencia = procedencias[0] if procedencias else None

        dados.append({
            "inep": inep,
            "escola": escola,
            "gestor": gestor,
            "telefone": telefone_1,
            "telefone_2": telefone_2,
            "telefone_3": telefone_3,
            "outros_telefones": outros_telefones,
            "email": email,
            "municipio": None,
            "origem": f"Consolidada contatos - {procedencia or nome_aba}",
            "fonte_contato": procedencia
        })

    return pd.DataFrame(dados)


def extrair_consolidada_contatos(arquivo):
    arquivo.seek(0)

    try:
        planilhas = pd.read_excel(
            arquivo,
            sheet_name=None,
            dtype=str
        )
    except Exception:
        return pd.DataFrame()

    if not planilhas:
        return pd.DataFrame()

    # Prioriza a aba em que os contatos estão na mesma linha,
    # porque ela representa melhor uma escola por linha.
    for nome_aba, df in planilhas.items():
        if normalizar_coluna(nome_aba) == "ctts na mesma linha":
            df_resultado = extrair_de_aba_ctts_mesma_linha(
                df,
                nome_aba
            )

            if not df_resultado.empty:
                return df_resultado

    # Fallback para a aba de um contato por linha.
    for nome_aba, df in planilhas.items():
        if "um ctt por linha" in normalizar_coluna(nome_aba):
            df_resultado = extrair_de_aba_um_ctt_por_linha(
                df,
                nome_aba
            )

            if not df_resultado.empty:
                return df_resultado

    # Última tentativa: procura qualquer aba compatível.
    for nome_aba, df in planilhas.items():
        df_resultado = extrair_de_aba_ctts_mesma_linha(
            df,
            nome_aba
        )

        if not df_resultado.empty:
            return df_resultado

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