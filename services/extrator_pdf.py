import re
import unicodedata
import pandas as pd
import pdfplumber


def normalizar_texto(texto):
    if texto is None or pd.isna(texto):
        return ""

    texto = str(texto).strip()

    texto = unicodedata.normalize("NFD", texto)
    texto = texto.encode("ascii", "ignore")
    texto = texto.decode("utf-8")

    texto = texto.replace("\n", " ")
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


def normalizar_minusculo(texto):
    return normalizar_texto(texto).lower()


def normalizar_maiusculo(texto):
    return normalizar_texto(texto).upper()


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
        "não possui",
        "nao possui",
        "não informado",
        "nao informado",
        "n/a"
    ]:
        return None

    return valor


def limpar_inep(valor):
    if valor is None or pd.isna(valor):
        return None

    valor = str(valor)

    match = re.search(r"\b\d{7,8}\b", valor)

    if match:
        return match.group(0)

    valor = re.sub(r"\D", "", valor)

    if len(valor) >= 7:
        return valor

    return None


def corrigir_texto_email(valor):
    if valor is None or pd.isna(valor):
        return ""

    valor = str(valor)
    valor = valor.replace("\n", " ")
    valor = re.sub(r"\s+", " ", valor)

    valor = re.sub(r"\s*@\s*", "@", valor)
    valor = re.sub(r"\s*\.\s*", ".", valor)

    return valor


def limpar_email(valor):
    if valor is None or pd.isna(valor):
        return None

    valor = corrigir_texto_email(valor)

    emails = re.findall(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        valor
    )

    if emails:
        return emails[0].lower()

    return None


def extrair_todos_emails(valor):
    if valor is None or pd.isna(valor):
        return []

    valor = corrigir_texto_email(valor)

    emails = re.findall(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        valor
    )

    emails_limpos = []

    for email in emails:
        email = email.lower()

        if email not in emails_limpos:
            emails_limpos.append(email)

    return emails_limpos


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

        if numero.startswith("0") and len(numero) in [11, 12]:
            numero = numero[1:]

        if len(numero) in [8, 9, 10, 11]:
            candidatos.append(numero)

    if candidatos:
        return candidatos[0]

    numero = re.sub(r"\D", "", valor)

    if numero.startswith("55") and len(numero) in [12, 13]:
        numero = numero[2:]

    if numero.startswith("0") and len(numero) in [11, 12]:
        numero = numero[1:]

    if len(numero) in [8, 9, 10, 11]:
        return numero

    return None


def extrair_todos_telefones(valor):
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

        if telefone and telefone not in telefones:
            telefones.append(telefone)

    if not telefones:
        telefone = limpar_telefone(valor)

        if telefone and telefone not in telefones:
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

        if telefone.startswith("0") and len(telefone) in [11, 12]:
            telefone = telefone[1:]

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


def remover_emails(texto):
    if texto is None:
        return None

    texto = corrigir_texto_email(texto)

    texto = re.sub(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        " ",
        texto
    )

    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


def remover_telefones(texto):
    if texto is None:
        return None

    texto = str(texto)

    texto = re.sub(
        r"(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?\d?\s?\d{4,5}[-\s]?\d{4}",
        " ",
        texto
    )

    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


def limpar_nome_gestor(valor):
    if valor is None or pd.isna(valor):
        return None

    texto = str(valor).replace("\n", " ").strip()

    texto = remover_emails(texto)
    texto = remover_telefones(texto)

    texto = texto.replace('"', " ")
    texto = texto.replace("'", " ")
    texto = texto.strip(" -()")

    texto = re.sub(r"\s+", " ", texto)

    if texto.lower() in [
        "",
        "nan",
        "none",
        "-",
        "não informado",
        "nao informado",
        "não possui",
        "nao possui",
        "reforma"
    ]:
        return None

    return texto


def linha_vazia(linha):
    if not linha:
        return True

    for valor in linha:
        if valor is not None and str(valor).strip() != "":
            return False

    return True


def limpar_linha(linha):
    nova_linha = []

    for valor in linha:
        if valor is None:
            nova_linha.append("")
        else:
            texto = str(valor).replace("\xa0", " ").strip()
            texto = re.sub(r"\s+", " ", texto)
            nova_linha.append(texto)

    return nova_linha


def montar_dataframe(dados):
    if not dados:
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

    df = pd.DataFrame(dados)

    colunas = [
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

    for coluna in colunas:
        if coluna not in df.columns:
            df[coluna] = None

    df = df[colunas]

    df = df.drop_duplicates(
        subset=[
            "inep",
            "escola",
            "gestor",
            "telefone",
            "email"
        ],
        keep="first"
    )

    df = df.reset_index(drop=True)

    return df


def extrair_texto_pdf(arquivo):
    arquivo.seek(0)

    texto_completo = ""

    with pdfplumber.open(arquivo) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text() or ""
            texto_completo += "\n" + texto

    return texto_completo


def extrair_tabelas_pdf(arquivo):
    arquivo.seek(0)

    tabelas_extraidas = []

    with pdfplumber.open(arquivo) as pdf:
        for numero_pagina, pagina in enumerate(pdf.pages, start=1):
            tabelas = []

            try:
                tabelas = pagina.extract_tables({
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                    "intersection_tolerance": 5
                })
            except Exception:
                tabelas = []

            if not tabelas:
                try:
                    tabelas = pagina.extract_tables({
                        "vertical_strategy": "text",
                        "horizontal_strategy": "text",
                        "intersection_tolerance": 5
                    })
                except Exception:
                    tabelas = []

            for tabela in tabelas:
                tabelas_extraidas.append({
                    "pagina": numero_pagina,
                    "tabela": tabela
                })

    return tabelas_extraidas


def detectar_pdf_caruaru_municipal(texto_completo, nome_arquivo=""):
    texto = normalizar_minusculo(texto_completo)
    nome_arquivo = normalizar_minusculo(nome_arquivo)

    if "caruaru" in nome_arquivo and "municipal" in nome_arquivo:
        return True

    condicoes = [
        "unidade escolar" in texto,
        "nome do gestor" in texto,
        "telefone 1 do gestor" in texto,
        "e-mail do gestor" in texto or "email do gestor" in texto,
        "nucleacao" in texto or "nucleação" in texto
    ]

    return all(condicoes)


def detectar_pdf_campina_municipal(texto_completo):
    texto = normalizar_minusculo(texto_completo)

    condicoes = [
        "secretaria de educacao de campina grande" in texto
        or "secretaria de educação de campina grande" in texto,
        "diretoria de apoio as escolas" in texto
        or "diretoria de apoio às escolas" in texto,
        "gestor adjunto" in texto,
        "horario de funcionamento" in texto
        or "horário de funcionamento" in texto
    ]

    return all(condicoes)


def detectar_pdf_campina_estadual(texto_completo):
    texto = normalizar_minusculo(texto_completo)

    condicoes = [
        "relacao das escolas da 3" in texto
        or "relação das escolas da 3" in texto,
        "email alternativo da escola" in texto
        or "e-mail alternativo da escola" in texto,
        "quantidade computadores" in texto
        or "quantidade pc" in texto
    ]

    return all(condicoes)


def encontrar_indice_coluna(cabecalho, opcoes):
    for i, coluna in enumerate(cabecalho):
        coluna_norm = normalizar_minusculo(coluna)

        for opcao in opcoes:
            opcao_norm = normalizar_minusculo(opcao)

            if coluna_norm == opcao_norm:
                return i

    for i, coluna in enumerate(cabecalho):
        coluna_norm = normalizar_minusculo(coluna)

        for opcao in opcoes:
            opcao_norm = normalizar_minusculo(opcao)

            if opcao_norm in coluna_norm:
                return i

    return None


def expandir_linha_por_inep(linha):
    """
    Alguns PDFs do Caruaru vêm com várias escolas dentro da mesma célula.
    Quando isso acontece, a coluna INEP vem com vários códigos separados por quebra de linha.
    Esta função transforma isso em uma linha por escola.
    """

    if not linha:
        return []

    partes_por_coluna = []

    for valor in linha:
        if valor is None:
            partes_por_coluna.append([""])
        else:
            partes = str(valor).split("\n")
            partes = [p.strip() for p in partes]
            partes_por_coluna.append(partes)

    maior = max(len(partes) for partes in partes_por_coluna)

    if maior <= 1:
        return [linha]

    novas_linhas = []

    for i in range(maior):
        nova_linha = []

        for partes in partes_por_coluna:
            if len(partes) == maior:
                nova_linha.append(partes[i])
            elif len(partes) == 1:
                nova_linha.append(partes[0])
            elif i < len(partes):
                nova_linha.append(partes[i])
            else:
                nova_linha.append("")

        novas_linhas.append(nova_linha)

    return novas_linhas


def extrair_caruaru_municipal(arquivo):
    dados = []

    tabelas = extrair_tabelas_pdf(arquivo)

    for item in tabelas:
        pagina = item["pagina"]
        tabela = item["tabela"]

        if not tabela:
            continue

        indice_cabecalho = None

        for i, linha in enumerate(tabela[:20]):
            if linha_vazia(linha):
                continue

            linha_limpa = limpar_linha(linha)
            texto_linha = normalizar_minusculo(" ".join(linha_limpa))

            if (
                "inep" in texto_linha
                and "unidade escolar" in texto_linha
                and "nome do gestor" in texto_linha
                and "telefone 1 do gestor" in texto_linha
            ):
                indice_cabecalho = i
                break

        if indice_cabecalho is None:
            continue

        cabecalho = limpar_linha(tabela[indice_cabecalho])

        idx_inep = encontrar_indice_coluna(cabecalho, [
            "inep"
        ])

        idx_escola = encontrar_indice_coluna(cabecalho, [
            "unidade escolar",
            "escola"
        ])

        idx_gestor = encontrar_indice_coluna(cabecalho, [
            "nome do gestor",
            "gestor"
        ])

        idx_telefone_1 = encontrar_indice_coluna(cabecalho, [
            "telefone 1 do gestor",
            "telefone do gestor",
            "telefone gestor"
        ])

        idx_telefone_2 = encontrar_indice_coluna(cabecalho, [
            "telefone 2 do gestor"
        ])

        idx_email = encontrar_indice_coluna(cabecalho, [
            "e-mail do gestor",
            "email do gestor",
            "e mail do gestor"
        ])

        if idx_inep is None or idx_escola is None or idx_gestor is None:
            continue

        for linha_original in tabela[indice_cabecalho + 1:]:
            if linha_vazia(linha_original):
                continue

            linhas_expandidas = expandir_linha_por_inep(linha_original)

            for linha in linhas_expandidas:
                linha = limpar_linha(linha)

                if len(linha) <= max(idx_inep, idx_escola, idx_gestor):
                    continue

                inep = linha[idx_inep] if idx_inep < len(linha) else None
                escola = linha[idx_escola] if idx_escola < len(linha) else None
                gestor = linha[idx_gestor] if idx_gestor < len(linha) else None

                telefone_1_bruto = linha[idx_telefone_1] if idx_telefone_1 is not None and idx_telefone_1 < len(linha) else None
                telefone_2_bruto = linha[idx_telefone_2] if idx_telefone_2 is not None and idx_telefone_2 < len(linha) else None
                email_bruto = linha[idx_email] if idx_email is not None and idx_email < len(linha) else None

                inep = limpar_inep(inep)
                escola = limpar_valor(escola)
                gestor = limpar_nome_gestor(gestor)
                email = limpar_email(email_bruto)

                telefones = []
                telefones.extend(extrair_todos_telefones(telefone_1_bruto))
                telefones.extend(extrair_todos_telefones(telefone_2_bruto))

                telefones = ordenar_telefones(telefones)

                telefone_1 = telefones[0] if len(telefones) >= 1 else None
                telefone_2 = telefones[1] if len(telefones) >= 2 else None
                telefone_3 = telefones[2] if len(telefones) >= 3 else None
                outros_telefones = "; ".join(telefones[3:]) if len(telefones) > 3 else None

                if not escola:
                    continue

                if not inep and not gestor and not telefone_1 and not email:
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
                    "municipio": "Caruaru",
                    "origem": f"Caruaru Municipal 2026 - página {pagina}",
                    "fonte_contato": "Caruaru Municipal 2026"
                })

    return montar_dataframe(dados)


def parece_linha_estadual_campina(linha):
    if len(linha) < 8:
        return False

    cidade = normalizar_maiusculo(linha[0])
    escola = normalizar_maiusculo(linha[1])
    inep = limpar_inep(linha[2])
    gestor = limpar_valor(linha[6])
    contato = limpar_valor(linha[7])

    if "CAMPINA" not in cidade:
        return False

    if not escola:
        return False

    if not inep:
        return False

    if not gestor and not contato:
        return False

    return True


def parece_linha_municipal_campina(linha):
    if len(linha) < 10:
        return False

    ordem = limpar_valor(linha[0])
    escola = limpar_valor(linha[1])
    inep = limpar_inep(linha[6])
    gestor = limpar_valor(linha[8])

    if not ordem or not re.fullmatch(r"\d+", str(ordem)):
        return False

    if not escola:
        return False

    if not inep:
        return False

    if not gestor:
        return False

    return True


def extrair_campina_municipal(arquivo):
    dados = []

    tabelas = extrair_tabelas_pdf(arquivo)

    for item in tabelas:
        pagina = item["pagina"]
        tabela = item["tabela"]

        if not tabela:
            continue

        indice_cabecalho = None

        for i, linha in enumerate(tabela[:20]):
            if linha_vazia(linha):
                continue

            linha_limpa = limpar_linha(linha)
            texto_linha = normalizar_minusculo(" ".join(linha_limpa))

            if (
                "ordem" in texto_linha
                and "unidade" in texto_linha
                and "inep" in texto_linha
                and "gestor" in texto_linha
                and "contato" in texto_linha
            ):
                indice_cabecalho = i
                break

        if indice_cabecalho is not None:
            linhas_dados = tabela[indice_cabecalho + 1:]
        else:
            linhas_dados = tabela

        for linha in linhas_dados:
            if linha_vazia(linha):
                continue

            linha = limpar_linha(linha)

            if not parece_linha_municipal_campina(linha):
                continue

            escola = linha[1] if len(linha) > 1 else None
            inep = linha[6] if len(linha) > 6 else None
            gestor_bruto = linha[8] if len(linha) > 8 else None
            contato_gestor = linha[9] if len(linha) > 9 else None
            gestor_adjunto_bruto = linha[10] if len(linha) > 10 else None
            contato_adjunto = linha[11] if len(linha) > 11 else None

            escola = limpar_valor(escola)

            if not escola:
                continue

            inep = limpar_inep(inep)

            gestor = limpar_nome_gestor(gestor_bruto)
            email_gestor = limpar_email(gestor_bruto)

            emails_adjunto = extrair_todos_emails(gestor_adjunto_bruto)

            telefones = []
            telefones.extend(extrair_todos_telefones(contato_gestor))
            telefones.extend(extrair_todos_telefones(contato_adjunto))

            telefones = ordenar_telefones(telefones)

            telefone_1 = telefones[0] if len(telefones) >= 1 else None
            telefone_2 = telefones[1] if len(telefones) >= 2 else None
            telefone_3 = telefones[2] if len(telefones) >= 3 else None
            outros_telefones = "; ".join(telefones[3:]) if len(telefones) > 3 else None

            email = email_gestor

            if not email and emails_adjunto:
                email = emails_adjunto[0]

            dados.append({
                "inep": inep,
                "escola": escola,
                "gestor": gestor,
                "telefone": telefone_1,
                "telefone_2": telefone_2,
                "telefone_3": telefone_3,
                "outros_telefones": outros_telefones,
                "email": email,
                "municipio": "Campina Grande",
                "origem": f"Campina Grande Municipal 2026 - página {pagina}",
                "fonte_contato": "Campina Grande Municipal 2026"
            })

    return montar_dataframe(dados)


def extrair_campina_estadual(arquivo):
    dados = []

    tabelas = extrair_tabelas_pdf(arquivo)

    for item in tabelas:
        pagina = item["pagina"]
        tabela = item["tabela"]

        if not tabela:
            continue

        indice_cabecalho = None

        for i, linha in enumerate(tabela[:15]):
            if linha_vazia(linha):
                continue

            linha_limpa = limpar_linha(linha)
            texto_linha = normalizar_minusculo(" ".join(linha_limpa))

            if (
                "cidade" in texto_linha
                and "escola" in texto_linha
                and "inep" in texto_linha
                and "gestor" in texto_linha
                and "contato" in texto_linha
            ):
                indice_cabecalho = i
                break

        if indice_cabecalho is not None:
            linhas_dados = tabela[indice_cabecalho + 1:]
        else:
            linhas_dados = tabela

        for linha in linhas_dados:
            if linha_vazia(linha):
                continue

            linha = limpar_linha(linha)

            if not parece_linha_estadual_campina(linha):
                continue

            cidade = linha[0]
            escola = linha[1]
            inep = linha[2]
            email_escola = linha[4]
            gestor = linha[6]
            contato = linha[7]

            cidade = limpar_valor(cidade)
            escola = limpar_valor(escola)
            inep = limpar_inep(inep)
            gestor = limpar_nome_gestor(gestor)
            email = limpar_email(email_escola)

            telefones = ordenar_telefones(
                extrair_todos_telefones(contato)
            )

            telefone_1 = telefones[0] if len(telefones) >= 1 else None
            telefone_2 = telefones[1] if len(telefones) >= 2 else None
            telefone_3 = telefones[2] if len(telefones) >= 3 else None
            outros_telefones = "; ".join(telefones[3:]) if len(telefones) > 3 else None

            if not escola:
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
                "municipio": cidade or "Campina Grande",
                "origem": f"Campina Grande Estadual 2026 - página {pagina}",
                "fonte_contato": "Campina Grande Estadual 2026"
            })

    return montar_dataframe(dados)


def extrair_pdf_generico_tabelas(arquivo):
    dados = []

    tabelas = extrair_tabelas_pdf(arquivo)

    for item in tabelas:
        pagina = item["pagina"]
        tabela = item["tabela"]

        if not tabela:
            continue

        indice_cabecalho = None

        for i, linha in enumerate(tabela[:15]):
            if linha_vazia(linha):
                continue

            linha_limpa = limpar_linha(linha)
            texto_linha = normalizar_minusculo(" ".join(linha_limpa))

            tem_cabecalho = (
                "escola" in texto_linha
                or "unidade" in texto_linha
            ) and (
                "gestor" in texto_linha
                or "diretor" in texto_linha
                or "direcao" in texto_linha
                or "direção" in texto_linha
            )

            if tem_cabecalho:
                indice_cabecalho = i
                break

        if indice_cabecalho is None:
            continue

        cabecalho = limpar_linha(tabela[indice_cabecalho])

        idx_inep = encontrar_indice_coluna(cabecalho, [
            "inep",
            "codigo inep",
            "código inep"
        ])

        idx_escola = encontrar_indice_coluna(cabecalho, [
            "escola",
            "unidade",
            "unidade escolar",
            "nome da escola"
        ])

        idx_gestor = encontrar_indice_coluna(cabecalho, [
            "gestor",
            "nome do gestor",
            "diretor",
            "diretor(a)",
            "diretora",
            "direção",
            "direcao"
        ])

        idx_email = encontrar_indice_coluna(cabecalho, [
            "email",
            "e-mail",
            "e mail",
            "email do gestor",
            "e-mail do gestor",
            "e-mail alternativo da escola",
            "email alternativo da escola"
        ])

        idx_municipio = encontrar_indice_coluna(cabecalho, [
            "municipio",
            "município",
            "cidade"
        ])

        indices_contato = []

        for i, coluna in enumerate(cabecalho):
            coluna_norm = normalizar_minusculo(coluna)

            if (
                "contato" in coluna_norm
                or "telefone" in coluna_norm
                or "celular" in coluna_norm
            ):
                indices_contato.append(i)

        for linha in tabela[indice_cabecalho + 1:]:
            if linha_vazia(linha):
                continue

            linha = limpar_linha(linha)

            escola = linha[idx_escola] if idx_escola is not None and idx_escola < len(linha) else None
            gestor_bruto = linha[idx_gestor] if idx_gestor is not None and idx_gestor < len(linha) else None
            email_bruto = linha[idx_email] if idx_email is not None and idx_email < len(linha) else None
            municipio = linha[idx_municipio] if idx_municipio is not None and idx_municipio < len(linha) else None
            inep = linha[idx_inep] if idx_inep is not None and idx_inep < len(linha) else None

            telefones = []

            for idx_contato in indices_contato:
                if idx_contato < len(linha):
                    telefones.extend(
                        extrair_todos_telefones(linha[idx_contato])
                    )

            telefones = ordenar_telefones(telefones)

            telefone_1 = telefones[0] if len(telefones) >= 1 else None
            telefone_2 = telefones[1] if len(telefones) >= 2 else None
            telefone_3 = telefones[2] if len(telefones) >= 3 else None
            outros_telefones = "; ".join(telefones[3:]) if len(telefones) > 3 else None

            escola = limpar_valor(escola)
            inep = limpar_inep(inep)
            gestor = limpar_nome_gestor(gestor_bruto)

            email = limpar_email(email_bruto)

            if not email:
                email = limpar_email(gestor_bruto)

            municipio = limpar_valor(municipio)

            if not escola:
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
                "municipio": municipio,
                "origem": f"PDF genérico - página {pagina}",
                "fonte_contato": "PDF genérico"
            })

    return montar_dataframe(dados)


def extrair_pdf_por_texto(arquivo):
    texto_completo = extrair_texto_pdf(arquivo)

    dados = []

    linhas = texto_completo.splitlines()

    for linha in linhas:
        linha_limpa = limpar_valor(linha)

        if not linha_limpa:
            continue

        telefones = ordenar_telefones(
            extrair_todos_telefones(linha_limpa)
        )

        email = limpar_email(linha_limpa)
        inep = limpar_inep(linha_limpa)

        tem_escola = re.search(
            r"\b(EMEF|EMEIF|EMEI|CMEI|CM|EEEF|EEEM|EEEFM|ECI|ECIT|CAIC|ESCOLA|EM|ETI|CMEI)\b",
            linha_limpa,
            flags=re.IGNORECASE
        )

        if not tem_escola:
            continue

        if not telefones and not email:
            continue

        telefone_1 = telefones[0] if len(telefones) >= 1 else None
        telefone_2 = telefones[1] if len(telefones) >= 2 else None
        telefone_3 = telefones[2] if len(telefones) >= 3 else None
        outros_telefones = "; ".join(telefones[3:]) if len(telefones) > 3 else None

        dados.append({
            "inep": inep,
            "escola": linha_limpa,
            "gestor": None,
            "telefone": telefone_1,
            "telefone_2": telefone_2,
            "telefone_3": telefone_3,
            "outros_telefones": outros_telefones,
            "email": email,
            "municipio": None,
            "origem": "PDF texto",
            "fonte_contato": "PDF texto"
        })

    return montar_dataframe(dados)


def extrair_pdf(arquivo):
    nome_arquivo = getattr(arquivo, "name", "")

    texto_completo = extrair_texto_pdf(arquivo)

    if detectar_pdf_caruaru_municipal(texto_completo, nome_arquivo):
        df_caruaru = extrair_caruaru_municipal(arquivo)

        if not df_caruaru.empty:
            return df_caruaru

    df_municipal = extrair_campina_municipal(arquivo)

    if not df_municipal.empty:
        if detectar_pdf_campina_municipal(texto_completo) or len(df_municipal) >= 20:
            return df_municipal

    df_estadual = extrair_campina_estadual(arquivo)

    if not df_estadual.empty:
        if detectar_pdf_campina_estadual(texto_completo) or len(df_estadual) >= 10:
            return df_estadual

    df_generico = extrair_pdf_generico_tabelas(arquivo)

    if not df_generico.empty:
        return df_generico

    df_texto = extrair_pdf_por_texto(arquivo)

    if not df_texto.empty:
        return df_texto

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