import re

def limpar_espacos(texto):
    if texto is None:
        return ""

    texto = str(texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()