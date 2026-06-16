import pandas as pd
from docx import Document
import re
import unicodedata


def normalizar_texto(texto):
    if texto is None:
        return ""

    texto = str(texto).strip()

    texto = unicodedata.normalize("NFD", texto)
    texto = texto.encode("ascii", "ignore")
    texto = texto.decode("utf-8")

    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


def limpar_linha(texto):
    texto = str(texto).strip()
    texto = re.sub(r"\s+", " ", texto)
    texto = texto.strip("|").strip()
    return texto


def limpar_telefone(telefone):
    if telefone is None:
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


def limpar_email(texto):
    if texto is None:
        return None

    emails = re.findall(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        str(texto)
    )

    if emails:
        return emails[0].lower()

    return None


def buscar_campo_por_nome(registro, opcoes):
    for chave, valor in registro.items():
        chave_norm = normalizar_texto(chave).lower()

        for opcao in opcoes:
            opcao_norm = normalizar_texto(opcao).lower()

            if opcao_norm in chave_norm or chave_norm in opcao_norm:
                if valor is not None and str(valor).strip() != "":
                    return valor

    return None


def extrair_de_tabela_com_cabecalho(tabela):
    dados = []

    if len(tabela.rows) < 2:
        return dados

    cabecalho = [
        limpar_linha(celula.text)
        for celula in tabela.rows[0].cells
    ]

    texto_cabecalho = normalizar_texto(" ".join(cabecalho)).lower()

    tem_cabecalho = (
        "escola" in texto_cabecalho
        or "gestor" in texto_cabecalho
        or "diretor" in texto_cabecalho
        or "contato" in texto_cabecalho
        or "telefone" in texto_cabecalho
    )

    if not tem_cabecalho:
        return dados

    for row in tabela.rows[1:]:
        celulas = [
            limpar_linha(celula.text)
            for celula in row.cells
        ]

        registro = {}

        for i, nome_coluna in enumerate(cabecalho):
            valor = celulas[i] if i < len(celulas) else None
            registro[nome_coluna] = valor

        escola = buscar_campo_por_nome(registro, [
            "escola",
            "unidade escolar",
            "nome da escola",
            "instituição"
        ])

        gestor = buscar_campo_por_nome(registro, [
            "gestor",
            "gestor(a)",
            "diretor",
            "diretor(a)",
            "diretora",
            "nome do gestor",
            "nome diretor",
            "responsável"
        ])

        telefone = buscar_campo_por_nome(registro, [
            "telefone",
            "contato",
            "celular",
            "whatsapp",
            "fone"
        ])

        email = buscar_campo_por_nome(registro, [
            "email",
            "e-mail",
            "e mail"
        ])

        escola = limpar_linha(escola) if escola else None
        gestor = limpar_linha(gestor) if gestor else None
        telefone = limpar_telefone(telefone)
        email = limpar_email(email)

        if escola or gestor or telefone or email:
            dados.append({
                "escola": escola,
                "gestor": gestor,
                "telefone": telefone,
                "email": email,
                "municipio": None,
                "origem": "Word - tabela com cabeçalho"
            })

    return dados


def extrair_de_tabela_sem_cabecalho(tabela):
    dados = []

    for row in tabela.rows:
        celulas = [
            limpar_linha(celula.text)
            for celula in row.cells
            if limpar_linha(celula.text)
        ]

        if len(celulas) < 2:
            continue

        texto_linha = " | ".join(celulas)

        telefone = limpar_telefone(texto_linha)
        email = limpar_email(texto_linha)

        if not telefone and not email:
            continue

        escola = None
        gestor = None

        # Caso comum:
        # número | escola | telefone | gestor
        if len(celulas) >= 4:
            escola = celulas[1]
            gestor = celulas[3]

        # Caso:
        # escola | telefone | gestor
        elif len(celulas) == 3:
            escola = celulas[0]
            gestor = celulas[2]

        # Caso:
        # escola gestor telefone tudo misturado
        else:
            texto_sem_contato = re.sub(
                r"(?:\(?\d{2}\)?\s*)?\d?\s?\d{4,5}[-\s]?\d{4}",
                "",
                texto_linha
            )

            texto_sem_contato = re.sub(
                r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
                "",
                texto_sem_contato
            )

            partes = texto_sem_contato.split("|")

            if len(partes) >= 2:
                escola = limpar_linha(partes[0])
                gestor = limpar_linha(partes[1])

        if escola or gestor or telefone or email:
            dados.append({
                "escola": escola,
                "gestor": gestor,
                "telefone": telefone,
                "email": email,
                "municipio": None,
                "origem": "Word - tabela simples"
            })

    return dados


def extrair_de_texto_word(doc):
    linhas = []

    for paragrafo in doc.paragraphs:
        texto = limpar_linha(paragrafo.text)

        if texto:
            linhas.append(texto)

    dados = []

    padrao_telefone = r"(\d{2}[-\s]?\d{8,9})"

    for i, linha in enumerate(linhas):
        telefone_encontrado = re.search(padrao_telefone, linha)

        if not telefone_encontrado:
            continue

        telefone = telefone_encontrado.group(1)

        linha_sem_numero = re.sub(r"^\d+\s+", "", linha)
        partes = re.split(padrao_telefone, linha_sem_numero)

        escola = ""
        gestor = ""

        if len(partes) >= 1:
            escola = limpar_linha(partes[0])

        if len(partes) >= 3:
            gestor = limpar_linha(partes[2])

        # Quando o gestor vem na linha de baixo
        if gestor == "" and i + 1 < len(linhas):
            proxima_linha = limpar_linha(linhas[i + 1])

            if not re.search(padrao_telefone, proxima_linha):
                gestor = proxima_linha

        dados.append({
            "escola": escola,
            "gestor": gestor,
            "telefone": limpar_telefone(telefone),
            "email": limpar_email(linha),
            "municipio": None,
            "origem": "Word - texto"
        })

    return dados


def extrair_word(arquivo):
    """
    Função principal chamada pelo leitor_arquivos.py.
    Essa função precisa existir exatamente com este nome:
    extrair_word
    """

    arquivo.seek(0)

    doc = Document(arquivo)

    dados = []

    for tabela in doc.tables:
        dados_tabela_cabecalho = extrair_de_tabela_com_cabecalho(tabela)

        if dados_tabela_cabecalho:
            dados.extend(dados_tabela_cabecalho)
        else:
            dados.extend(extrair_de_tabela_sem_cabecalho(tabela))

    dados.extend(extrair_de_texto_word(doc))

    df = pd.DataFrame(dados)

    if df.empty:
        return pd.DataFrame(columns=[
            "escola",
            "gestor",
            "telefone",
            "email",
            "municipio",
            "origem"
        ])

    for coluna in ["escola", "gestor", "telefone", "email", "municipio", "origem"]:
        if coluna not in df.columns:
            df[coluna] = None

    df = df[df["escola"].notna()]
    df = df[df["escola"].astype(str).str.strip() != ""]

    df = df.drop_duplicates(
        subset=["escola", "gestor", "telefone", "email"],
        keep="first"
    )

    return df[[
        "escola",
        "gestor",
        "telefone",
        "email",
        "municipio",
        "origem"
    ]].reset_index(drop=True)