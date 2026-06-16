import pandas as pd
import re
import unicodedata


def normalizar_coluna(coluna):
    coluna = str(coluna).strip().lower()

    coluna = unicodedata.normalize("NFD", coluna)
    coluna = coluna.encode("ascii", "ignore")
    coluna = coluna.decode("utf-8")

    coluna = coluna.replace("\n", " ")
    coluna = coluna.replace("_", " ")
    coluna = coluna.replace("-", " ")
    coluna = coluna.replace("/", " ")
    coluna = coluna.replace("(", " ")
    coluna = coluna.replace(")", " ")

    coluna = re.sub(r"\s+", " ", coluna)

    return coluna.strip()


def normalizar_texto(texto):
    if pd.isna(texto):
        return ""

    texto = str(texto).strip().upper()

    texto = unicodedata.normalize("NFD", texto)
    texto = texto.encode("ascii", "ignore")
    texto = texto.decode("utf-8")

    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


def limpar_valor(valor):
    if pd.isna(valor):
        return None

    valor = str(valor).replace("\xa0", " ").strip()
    valor = re.sub(r"\s+", " ", valor)

    if valor.lower() in [
        "",
        "nan",
        "none",
        "-",
        "não possui",
        "nao possui",
        "não informado",
        "nao informado",
        "n/a"
    ]:
        return None

    return valor


def limpar_inep(valor):
    if pd.isna(valor):
        return None

    valor = str(valor)

    match = re.search(r"\b\d{7,8}\b", valor)

    if match:
        return match.group(0)

    valor = re.sub(r"\D", "", valor)

    if len(valor) >= 7:
        return valor

    return None


def limpar_telefone(telefone):
    if pd.isna(telefone):
        return None

    telefone = str(telefone)

    telefones = re.findall(
        r"(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?\d?\s?\d{4,5}[-\s]?\d{4}",
        telefone
    )

    candidatos = []

    for item in telefones:
        numero = re.sub(r"\D", "", item)

        if numero.startswith("55") and len(numero) in [12, 13]:
            numero = numero[2:]

        if len(numero) in [8, 9, 10, 11]:
            candidatos.append(numero)

    if candidatos:
        return candidatos[0]

    telefone_limpo = re.sub(r"\D", "", telefone)

    if telefone_limpo.startswith("55") and len(telefone_limpo) in [12, 13]:
        telefone_limpo = telefone_limpo[2:]

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


def extrair_todos_emails(valor):
    if pd.isna(valor):
        return []

    valor = str(valor)

    emails = re.findall(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        valor
    )

    return [email.lower() for email in emails]


def extrair_todos_telefones(valor):
    if pd.isna(valor):
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


def encontrar_valor(linha, opcoes):
    for opcao in opcoes:
        opcao = normalizar_coluna(opcao)

        if opcao in linha.index:
            valor = limpar_valor(linha.get(opcao))

            if valor:
                return valor

    return None


def linha_tem_cabecalho(texto_linha):
    encontrou_escola = (
        "unidade escolar" in texto_linha
        or "escola" in texto_linha
        or "nome da escola" in texto_linha
    )

    encontrou_contato = (
        "contato" in texto_linha
        or "telefone" in texto_linha
        or "e mail" in texto_linha
        or "email" in texto_linha
    )

    encontrou_gestor = (
        "gestor" in texto_linha
        or "gestao" in texto_linha
        or "diretor" in texto_linha
        or "articulador" in texto_linha
        or "coordenador" in texto_linha
        or "nome diretor" in texto_linha
    )

    return encontrou_escola and encontrou_contato and encontrou_gestor


def filtrar_por_municipio(df, municipio_filtro):
    if not municipio_filtro or municipio_filtro == "Todas":
        return df

    if "municipio" not in df.columns:
        return df

    df = df.copy()

    municipios_validos = df["municipio"].dropna().astype(str).str.strip()

    if municipios_validos.empty:
        return df

    if municipios_validos.eq("").all():
        return df

    municipio_filtro_norm = normalizar_texto(municipio_filtro)

    df["municipio_norm"] = df["municipio"].apply(normalizar_texto)

    df = df[
        df["municipio_norm"].str.contains(
            municipio_filtro_norm,
            na=False
        )
    ]

    df = df.drop(columns=["municipio_norm"])

    return df


def escolher_abas_para_processar(planilhas_brutas):
    nomes_abas = list(planilhas_brutas.keys())

    prioridades = [
        "completa",
        "base geral de escolas 2025",
        "dados gerais2023",
        "base geral",
        "lista telefonica",
        "planilha1"
    ]

    for prioridade in prioridades:
        for nome in nomes_abas:
            nome_norm = normalizar_coluna(nome)

            if prioridade in nome_norm:
                return [nome]

    return nomes_abas


def detectar_modelo_petrolina_2026(planilhas_brutas):
    for nome_aba, df_original in planilhas_brutas.items():
        texto_amostra = ""

        for i in range(min(30, len(df_original))):
            valores = [
                str(valor)
                for valor in df_original.iloc[i].tolist()
                if pd.notna(valor)
            ]

            texto_amostra += " ".join(valores) + " "

        texto_norm = normalizar_texto(texto_amostra)

        condicoes = [
            "RELACAO DAS ESCOLAS ESTADUAIS" in texto_norm
            or "RELAÇÃO DAS ESCOLAS ESTADUAIS" in texto_norm,
            "GRE SERTAO DO MEDIO SAO FRANCISCO" in texto_norm
            or "GRE SERTÃO DO MÉDIO SÃO FRANCISCO" in texto_norm,
            "PETROLINA" in texto_norm
        ]

        if all(condicoes):
            return nome_aba

    return None


def extrair_municipio_secao(secao):
    if not secao:
        return None

    secao = str(secao).strip()

    partes = secao.split("-")

    if partes:
        municipio = partes[0].strip()
        return municipio.title()

    return secao.title()


def remover_inep_do_nome_escola(nome):
    if not nome:
        return None

    nome = str(nome)

    nome = re.sub(r"INEP\s*:?\s*\d{7,8}", "", nome, flags=re.IGNORECASE)
    nome = re.sub(r"\s+", " ", nome)

    return nome.strip(" -")


def extrair_petrolina_2026(planilhas_brutas, nome_aba):
    df = planilhas_brutas[nome_aba]

    dados = []

    secao_atual = None

    for i in range(len(df)):
        linha = df.iloc[i]

        col0 = limpar_valor(linha.get(0))
        col1 = limpar_valor(linha.get(1))

        if col0 and normalizar_texto(col0) in ["NO", "Nº", "N"]:
            secao_atual = col1
            continue

        if not col0:
            continue

        if not re.fullmatch(r"\d+", str(col0).strip()):
            continue

        escola_bruta = limpar_valor(linha.get(1))
        diretor = limpar_valor(linha.get(2))
        adjunto = limpar_valor(linha.get(3))
        secretario = limpar_valor(linha.get(4))

        if not escola_bruta:
            continue

        municipio = extrair_municipio_secao(secao_atual)

        inep = limpar_inep(escola_bruta)

        proxima_linha = df.iloc[i + 1] if i + 1 < len(df) else None
        linha_telefones = df.iloc[i + 2] if i + 2 < len(df) else None
        linha_emails = df.iloc[i + 3] if i + 3 < len(df) else None
        linha_institucional = df.iloc[i + 4] if i + 4 < len(df) else None

        if not inep and proxima_linha is not None:
            inep = limpar_inep(proxima_linha.get(1))

        escola = remover_inep_do_nome_escola(escola_bruta)

        telefone_diretor = None
        telefone_adjunto = None
        telefone_secretario = None

        if linha_telefones is not None:
            telefone_diretor = limpar_telefone(linha_telefones.get(2))
            telefone_adjunto = limpar_telefone(linha_telefones.get(3))
            telefone_secretario = limpar_telefone(linha_telefones.get(4))

        email_escola = None
        email_diretor = None
        email_adjunto = None
        email_secretario = None

        if linha_emails is not None:
            emails_escola = extrair_todos_emails(linha_emails.get(1))
            emails_diretor = extrair_todos_emails(linha_emails.get(2))
            emails_adjunto = extrair_todos_emails(linha_emails.get(3))
            emails_secretario = extrair_todos_emails(linha_emails.get(4))

            email_escola = emails_escola[0] if emails_escola else None
            email_diretor = emails_diretor[0] if emails_diretor else None
            email_adjunto = emails_adjunto[0] if emails_adjunto else None
            email_secretario = emails_secretario[0] if emails_secretario else None

        telefone_institucional = None

        if linha_institucional is not None:
            telefone_institucional = limpar_telefone(linha_institucional.get(1))

        telefones = ordenar_telefones([
            telefone_diretor,
            telefone_adjunto,
            telefone_secretario,
            telefone_institucional
        ])

        telefone_1 = telefones[0] if len(telefones) >= 1 else None
        telefone_2 = telefones[1] if len(telefones) >= 2 else None
        telefone_3 = telefones[2] if len(telefones) >= 3 else None
        outros_telefones = "; ".join(telefones[3:]) if len(telefones) > 3 else None

        email_principal = email_diretor or email_escola or email_adjunto or email_secretario

        gestor_principal = diretor or adjunto or secretario

        if not escola:
            continue

        dados.append({
            "inep": inep,
            "escola": escola,
            "gestor": gestor_principal,
            "telefone": telefone_1,
            "telefone_2": telefone_2,
            "telefone_3": telefone_3,
            "outros_telefones": outros_telefones,
            "email": email_principal,
            "municipio": municipio,
            "origem": "Petrolina 2026 - GRE Sertão do Médio São Francisco",
            "fonte_contato": "Petrolina 2026"
        })

    df_final = pd.DataFrame(dados)

    if df_final.empty:
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

    df_final = df_final.drop_duplicates(
        subset=["inep", "escola"],
        keep="first"
    )

    return df_final.reset_index(drop=True)


def detectar_modelo_gre_sem_cabecalho(df_original):
    if df_original.shape[1] < 8:
        return False

    encontrados = 0

    for _, linha in df_original.head(15).iterrows():
        col0 = limpar_valor(linha.get(0))
        col1 = limpar_valor(linha.get(1))
        col3 = limpar_valor(linha.get(3))
        col4 = limpar_valor(linha.get(4))
        col5 = limpar_valor(linha.get(5))

        if not col0 or not col1 or not col4 or not col5:
            continue

        cond_gre = "GRE" in str(col0).upper()
        cond_inep = bool(re.search(r"\d{6,8}", str(col3))) if col3 else False
        cond_escola = (
            "ESCOLA" in str(col4).upper()
            or "CENTRO" in str(col4).upper()
        )

        if cond_gre and cond_inep and cond_escola:
            encontrados += 1

    return encontrados >= 1


def extrair_modelo_gre_sem_cabecalho(df_original, nome_aba):
    dados = []

    for _, linha in df_original.iterrows():
        gre = limpar_valor(linha.get(0))
        municipio = limpar_valor(linha.get(1))
        inep = limpar_inep(linha.get(3))
        escola = limpar_valor(linha.get(4))
        gestor = limpar_valor(linha.get(5))
        telefone = limpar_telefone(linha.get(6))
        email = limpar_email(linha.get(7))

        if not escola and not gestor and not telefone and not email:
            continue

        if escola:
            escola_upper = escola.upper()

            if escola_upper.startswith("GRE "):
                continue

        if not gre or "GRE" not in str(gre).upper():
            continue

        if not inep:
            continue

        dados.append({
            "inep": inep,
            "escola": escola,
            "gestor": gestor,
            "telefone": telefone,
            "telefone_2": None,
            "telefone_3": None,
            "outros_telefones": None,
            "email": email,
            "municipio": municipio,
            "origem": nome_aba,
            "fonte_contato": nome_aba
        })

    return dados


def extrair_modelo_com_cabecalho(arquivo, nome_aba, df_original):
    dados = []

    linha_cabecalho = None

    for i in range(min(40, len(df_original))):
        valores_linha = [
            normalizar_coluna(valor)
            for valor in df_original.iloc[i].tolist()
            if pd.notna(valor)
        ]

        texto_linha = " ".join(valores_linha)

        if linha_tem_cabecalho(texto_linha):
            linha_cabecalho = i
            break

    if linha_cabecalho is None:
        return dados

    arquivo.seek(0)

    df = pd.read_excel(
        arquivo,
        sheet_name=nome_aba,
        header=linha_cabecalho,
        dtype=str
    )

    df.columns = [
        normalizar_coluna(col)
        for col in df.columns
    ]

    for _, linha in df.iterrows():
        inep = encontrar_valor(linha, [
            "inep",
            "codigo inep",
            "código inep",
            "cod inep",
            "cod. inep"
        ])

        escola = encontrar_valor(linha, [
            "unidade escolar",
            "escola",
            "nome da escola",
            "instituicao",
            "instituição"
        ])

        gestor = encontrar_valor(linha, [
            "gestao",
            "gestão",
            "gestor",
            "gestor a",
            "gestor escolar",
            "gestor a escolar",
            "gestora",
            "diretor",
            "diretor a",
            "diretora",
            "diretor escolar",
            "nome do gestor",
            "nome da gestora",
            "nome diretor",
            "nome do diretor",
            "nome_diretor",
            "articulador a de gestao",
            "articulador de gestao",
            "coordenador",
            "coordenador a"
        ])

        telefone = encontrar_valor(linha, [
            "telefone da gestao",
            "telefone da gestão",
            "telefone gestor",
            "telefone do gestor",
            "telefone 1 do gestor",
            "telefone 2 do gestor",
            "contato",
            "telefone",
            "celular",
            "numero",
            "número",
            "whatsapp",
            "whats",
            "fone"
        ])

        email = encontrar_valor(linha, [
            "e mail da gestao apenas adm",
            "e mail da gestão apenas adm",
            "e-mail da gestão apenas @adm",
            "email da gestao apenas adm",
            "e mail da gestao",
            "email da gestao",
            "email institucional",
            "e mail institucional",
            "email instituicional",
            "email do gestor",
            "e mail do gestor",
            "email gestor",
            "email",
            "e mail",
            "email da escola",
            "e mail da escola"
        ])

        municipio = encontrar_valor(linha, [
            "municipio",
            "município",
            "cidade"
        ])

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
                "telefone_2": None,
                "telefone_3": None,
                "outros_telefones": None,
                "email": email,
                "municipio": municipio,
                "origem": nome_aba,
                "fonte_contato": nome_aba
            })

    return dados


def extrair_excel(arquivo, municipio_filtro=None):
    arquivo.seek(0)

    planilhas_brutas = pd.read_excel(
        arquivo,
        sheet_name=None,
        header=None,
        dtype=str
    )

    nome_aba_petrolina_2026 = detectar_modelo_petrolina_2026(
        planilhas_brutas
    )

    if nome_aba_petrolina_2026:
        df_petrolina = extrair_petrolina_2026(
            planilhas_brutas,
            nome_aba_petrolina_2026
        )

        df_petrolina = filtrar_por_municipio(
            df_petrolina,
            municipio_filtro
        )

        return df_petrolina.reset_index(drop=True)

    abas_para_processar = escolher_abas_para_processar(
        planilhas_brutas
    )

    dados = []

    for nome_aba in abas_para_processar:
        df_original = planilhas_brutas[nome_aba]

        if detectar_modelo_gre_sem_cabecalho(df_original):
            dados.extend(
                extrair_modelo_gre_sem_cabecalho(
                    df_original,
                    nome_aba
                )
            )
        else:
            dados.extend(
                extrair_modelo_com_cabecalho(
                    arquivo,
                    nome_aba,
                    df_original
                )
            )

    df_final = pd.DataFrame(dados)

    if df_final.empty:
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

    df_final = filtrar_por_municipio(
        df_final,
        municipio_filtro
    )

    df_final = df_final.drop_duplicates(
        subset=[
            "inep",
            "escola",
            "gestor",
            "telefone",
            "email"
        ],
        keep="first"
    )

    return df_final.reset_index(drop=True)