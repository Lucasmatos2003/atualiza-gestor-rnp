import os
import tempfile
from datetime import datetime

import pandas as pd
import streamlit as st

from services.leitor_arquivos import ler_arquivo
from services.validador import validar_campos_obrigatorios
from services.atualizador_planilha_mestre import atualizar_planilha_mestre

from services.mapeador_colunas import (
    listar_abas_excel,
    ler_excel_bruto,
    ler_csv_bruto,
    sugerir_coluna,
    padronizar_por_mapeamento
)


st.set_page_config(
    page_title="AtualizaGestor RNP",
    page_icon="📘",
    layout="wide"
)


st.markdown(
    """
    <style>
        .main-title {
            font-size: 38px;
            font-weight: 800;
            color: #1f2937;
            margin-bottom: 0px;
        }

        .subtitle {
            font-size: 18px;
            color: #4b5563;
            margin-top: 4px;
            margin-bottom: 24px;
        }

        .step-card {
            background-color: #f8fafc;
            border: 1px solid #e5e7eb;
            border-radius: 14px;
            padding: 18px;
            margin-bottom: 14px;
        }

        .step-title {
            font-size: 20px;
            font-weight: 700;
            color: #111827;
            margin-bottom: 6px;
        }

        .step-description {
            font-size: 15px;
            color: #4b5563;
        }

        .success-box {
            background-color: #ecfdf5;
            border: 1px solid #10b981;
            color: #065f46;
            border-radius: 12px;
            padding: 14px;
            font-weight: 600;
        }

        .warning-box {
            background-color: #fffbeb;
            border: 1px solid #f59e0b;
            color: #92400e;
            border-radius: 12px;
            padding: 14px;
            font-weight: 600;
        }

        .info-box {
            background-color: #eff6ff;
            border: 1px solid #3b82f6;
            color: #1e40af;
            border-radius: 12px;
            padding: 14px;
            font-weight: 600;
        }

        .small-text {
            font-size: 13px;
            color: #6b7280;
        }
    </style>
    """,
    unsafe_allow_html=True
)


CIDADES_PROJETO = [
    "Todas",
    "Alenquer",
    "Almeirim",
    "Caicó",
    "Campina Grande",
    "Caruaru",
    "Juazeiro",
    "Macapá",
    "Monte Alegre",
    "Mossoró",
    "Petrolina",
    "Santarém",
    "Starlink"
]


COLUNAS_PADRAO = [
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


def inicializar_estado():
    if "df_extraido" not in st.session_state:
        st.session_state.df_extraido = None

    if "df_validado" not in st.session_state:
        st.session_state.df_validado = None

    if "relatorio_atualizacao" not in st.session_state:
        st.session_state.relatorio_atualizacao = None

    if "planilha_atualizada_bytes" not in st.session_state:
        st.session_state.planilha_atualizada_bytes = None

    if "nome_planilha_atualizada" not in st.session_state:
        st.session_state.nome_planilha_atualizada = None

    if "df_comparacao_topdesk" not in st.session_state:
        st.session_state.df_comparacao_topdesk = None

    if "df_topdesk" not in st.session_state:
        st.session_state.df_topdesk = None


def limpar_resultados():
    st.session_state.df_extraido = None
    st.session_state.df_validado = None
    st.session_state.relatorio_atualizacao = None
    st.session_state.planilha_atualizada_bytes = None
    st.session_state.nome_planilha_atualizada = None
    st.session_state.df_comparacao_topdesk = None
    st.session_state.df_topdesk = None


def normalizar_dataframe(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=COLUNAS_PADRAO)

    df = df.copy()

    for coluna in COLUNAS_PADRAO:
        if coluna not in df.columns:
            df[coluna] = None

    return df[COLUNAS_PADRAO]


def exibir_cabecalho():
    st.markdown(
        """
        <div class="main-title">AtualizaGestor RNP</div>
        <div class="subtitle">
            Atualização de contatos de gestores escolares a partir de arquivos enviados pelos pontos de apoio.
        </div>
        """,
        unsafe_allow_html=True
    )


def card_etapa(numero, titulo, descricao):
    st.markdown(
        f"""
        <div class="step-card">
            <div class="step-title">Etapa {numero} — {titulo}</div>
            <div class="step-description">{descricao}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def exibir_metricas_validacao(df_validado):
    total = len(df_validado)

    com_gestor = df_validado[
        df_validado["gestor"].notna()
        & (df_validado["gestor"].astype(str).str.strip() != "")
    ].shape[0]

    com_telefone = df_validado[
        df_validado["telefone"].notna()
        & (df_validado["telefone"].astype(str).str.strip() != "")
    ].shape[0]

    com_email = df_validado[
        df_validado["email"].notna()
        & (df_validado["email"].astype(str).str.strip() != "")
    ].shape[0]

    completos = df_validado[
        df_validado["status_validacao"] == "Completo para atualizar no TopDesk"
    ].shape[0]

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Registros encontrados", total)
    c2.metric("Com gestor", com_gestor)
    c3.metric("Com telefone", com_telefone)
    c4.metric("Com e-mail", com_email)
    c5.metric("Completos", completos)


def exibir_metricas_atualizacao(relatorio):
    if relatorio is None or relatorio.empty:
        return

    atualizados = relatorio[
        relatorio["status"].astype(str).str.contains(
            "Atualizado",
            case=False,
            na=False
        )
    ].shape[0]

    revisar = relatorio[
        relatorio["status"].astype(str).str.contains(
            "Revisar",
            case=False,
            na=False
        )
    ].shape[0]

    nao_encontrados = relatorio[
        relatorio["status"].astype(str).str.contains(
            "Não encontrado",
            case=False,
            na=False
        )
    ].shape[0]

    total = len(relatorio)

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total processado", total)
    c2.metric("Atualizados", atualizados)
    c3.metric("Revisar", revisar)
    c4.metric("Não encontrados", nao_encontrados)


def exibir_metricas_topdesk(df_comparacao):
    if df_comparacao is None or df_comparacao.empty:
        return

    total = len(df_comparacao)

    atualizar = df_comparacao[
        df_comparacao["status_comparacao"].astype(str).str.contains(
            "Atualizar",
            case=False,
            na=False
        )
    ].shape[0]

    iguais = df_comparacao[
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

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Escolas TopDesk", total)
    c2.metric("Precisam atualizar", atualizar)
    c3.metric("Dados iguais", iguais)
    c4.metric("Revisar", revisar)
    c5.metric("Não encontradas", nao_encontradas)


def tela_mapeamento_manual(arquivo_ponto_apoio):
    nome = arquivo_ponto_apoio.name.lower()

    st.subheader("Mapeamento manual de colunas")

    st.markdown(
        """
        <div class="info-box">
            Use esta opção quando o arquivo vier em um modelo novo.
            Você escolhe qual coluna representa INEP, Escola, Gestor, Telefone e E-mail.
        </div>
        """,
        unsafe_allow_html=True
    )

    df_bruto = None
    origem = "Mapeamento manual"

    if nome.endswith(".xlsx") or nome.endswith(".xls"):
        abas = listar_abas_excel(arquivo_ponto_apoio)

        aba_escolhida = st.selectbox(
            "Selecione a aba da planilha",
            abas
        )

        sem_cabecalho = st.checkbox(
            "Este arquivo não tem cabeçalho",
            value=False
        )

        if sem_cabecalho:
            df_bruto = ler_excel_bruto(
                arquivo_ponto_apoio,
                aba=aba_escolhida,
                sem_cabecalho=True
            )
        else:
            linha_cabecalho_visual = st.number_input(
                "Linha do cabeçalho",
                min_value=1,
                max_value=50,
                value=1,
                step=1,
                help="Se o cabeçalho estiver na primeira linha, deixe 1. Se estiver na quinta linha, coloque 5."
            )

            df_bruto = ler_excel_bruto(
                arquivo_ponto_apoio,
                aba=aba_escolhida,
                linha_cabecalho=int(linha_cabecalho_visual) - 1,
                sem_cabecalho=False
            )

        origem = f"Mapeamento manual - {aba_escolhida}"

    elif nome.endswith(".csv"):
        df_bruto = ler_csv_bruto(arquivo_ponto_apoio)
        origem = "Mapeamento manual - CSV"

    else:
        st.warning(
            "O mapeamento manual por colunas funciona apenas com Excel ou CSV. "
            "Para PDF e Word, use a leitura automática."
        )
        return None

    if df_bruto is None or df_bruto.empty:
        st.warning("Não foi possível carregar a tabela para mapeamento.")
        return None

    st.write("Prévia da tabela original:")

    st.dataframe(
        df_bruto.head(20),
        use_container_width=True,
        hide_index=True
    )

    opcoes_colunas = ["Não usar"] + list(df_bruto.columns)

    sugestao_inep = sugerir_coluna(df_bruto, "inep")
    sugestao_escola = sugerir_coluna(df_bruto, "escola")
    sugestao_gestor = sugerir_coluna(df_bruto, "gestor")
    sugestao_telefone = sugerir_coluna(df_bruto, "telefone")
    sugestao_email = sugerir_coluna(df_bruto, "email")
    sugestao_municipio = sugerir_coluna(df_bruto, "municipio")

    col1, col2 = st.columns(2)

    with col1:
        coluna_inep = st.selectbox(
            "Coluna do INEP, se existir",
            opcoes_colunas,
            index=opcoes_colunas.index(sugestao_inep) if sugestao_inep in opcoes_colunas else 0
        )

        coluna_escola = st.selectbox(
            "Coluna da Escola",
            opcoes_colunas,
            index=opcoes_colunas.index(sugestao_escola) if sugestao_escola in opcoes_colunas else 0
        )

        coluna_gestor = st.selectbox(
            "Coluna do Gestor",
            opcoes_colunas,
            index=opcoes_colunas.index(sugestao_gestor) if sugestao_gestor in opcoes_colunas else 0
        )

    with col2:
        coluna_telefone = st.selectbox(
            "Coluna do Telefone",
            opcoes_colunas,
            index=opcoes_colunas.index(sugestao_telefone) if sugestao_telefone in opcoes_colunas else 0
        )

        coluna_email = st.selectbox(
            "Coluna do E-mail",
            opcoes_colunas,
            index=opcoes_colunas.index(sugestao_email) if sugestao_email in opcoes_colunas else 0
        )

        coluna_municipio = st.selectbox(
            "Coluna do Município/Cidade, se existir",
            opcoes_colunas,
            index=opcoes_colunas.index(sugestao_municipio) if sugestao_municipio in opcoes_colunas else 0
        )

    campos_obrigatorios = [
        coluna_escola,
        coluna_gestor,
        coluna_telefone,
        coluna_email
    ]

    if "Não usar" in campos_obrigatorios:
        st.info(
            "Selecione pelo menos Escola, Gestor, Telefone e E-mail para aplicar o mapeamento."
        )
        return None

    df_mapeado = padronizar_por_mapeamento(
        df=df_bruto,
        coluna_inep=coluna_inep,
        coluna_escola=coluna_escola,
        coluna_gestor=coluna_gestor,
        coluna_telefone=coluna_telefone,
        coluna_email=coluna_email,
        coluna_municipio=coluna_municipio,
        origem=origem
    )

    df_mapeado = normalizar_dataframe(df_mapeado)

    st.subheader("Prévia após mapeamento")

    st.dataframe(
        df_mapeado.head(20),
        use_container_width=True,
        hide_index=True
    )

    return df_mapeado


def processar_leitura_arquivo(arquivo_ponto_apoio, cidade_escolhida, modo_leitura):
    if modo_leitura == "Leitura automática":
        with st.spinner("Lendo o arquivo recebido do ponto de apoio..."):
            df_extraido = ler_arquivo(
                arquivo_ponto_apoio,
                municipio_filtro=cidade_escolhida
            )

            df_extraido = normalizar_dataframe(df_extraido)

            return df_extraido

    return tela_mapeamento_manual(arquivo_ponto_apoio)


def salvar_upload_em_arquivo_temporario(uploaded_file, sufixo=".xlsx"):
    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=sufixo
    ) as tmp:
        tmp.write(uploaded_file.getvalue())
        return tmp.name


def atualizar_planilha_web(
    arquivo_planilha_mestre,
    df_validado,
    cidade_escolhida
):
    caminho_temporario = salvar_upload_em_arquivo_temporario(
        arquivo_planilha_mestre,
        sufixo=".xlsx"
    )

    try:
        relatorio = atualizar_planilha_mestre(
            caminho_planilha_mestre=caminho_temporario,
            df_contatos=df_validado,
            cidade_filtro=cidade_escolhida
        )

        with open(caminho_temporario, "rb") as arquivo_atualizado:
            planilha_bytes = arquivo_atualizado.read()

        data_nome = datetime.now().strftime("%Y%m%d_%H%M%S")

        nome_saida = f"LISTA_DE_GESTORES_ATUALIZADA_{data_nome}.xlsx"

        return relatorio, planilha_bytes, nome_saida

    finally:
        try:
            os.remove(caminho_temporario)
        except Exception:
            pass


def obter_config_api():
    api_url = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    api_token = os.getenv("API_TOKEN", "")

    try:
        if "API_BASE_URL" in st.secrets:
            api_url = st.secrets["API_BASE_URL"]

        if "API_TOKEN" in st.secrets:
            api_token = st.secrets["API_TOKEN"]
    except Exception:
        pass

    api_url = str(api_url).strip().rstrip("/")
    api_token = str(api_token).strip()

    return api_url, api_token


def limpar_valor_json(valor):
    if valor is None:
        return None

    try:
        if pd.isna(valor):
            return None
    except Exception:
        pass

    try:
        import math

        if isinstance(valor, float):
            if math.isnan(valor) or math.isinf(valor):
                return None
    except Exception:
        pass

    try:
        import numpy as np

        if isinstance(valor, np.generic):
            valor = valor.item()

            if isinstance(valor, float):
                import math

                if math.isnan(valor) or math.isinf(valor):
                    return None
    except Exception:
        pass

    if hasattr(valor, "isoformat"):
        try:
            return valor.isoformat()
        except Exception:
            return str(valor)

    return valor


def dataframe_para_payload(df):
    if df is None or df.empty:
        return []

    registros = df.to_dict(orient="records")
    registros_limpos = []

    for registro in registros:
        registro_limpo = {}

        for chave, valor in registro.items():
            registro_limpo[chave] = limpar_valor_json(valor)

        registros_limpos.append(registro_limpo)

    return registros_limpos


def comparar_com_topdesk_web(df_validado, cidade_escolhida):
    import requests

    api_url, api_token = obter_config_api()
    endpoint = f"{api_url}/topdesk/comparar"

    payload = {
        "cidade": cidade_escolhida,
        "dados_extraidos": dataframe_para_payload(df_validado)
    }

    headers = {
        "Content-Type": "application/json"
    }

    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"

    resposta = requests.post(
        endpoint,
        json=payload,
        headers=headers,
        timeout=300
    )

    if not resposta.ok:
        raise Exception(
            f"Erro na API TopDesk/Fabric: {resposta.status_code} - {resposta.text}"
        )

    resultado = resposta.json()

    total_topdesk = resultado.get("total_topdesk", 0)
    dados_comparacao = (
        resultado.get("dados")
        or resultado.get("comparacao")
        or resultado.get("df_comparacao")
        or []
    )

    df_topdesk_resumo = pd.DataFrame()

    if total_topdesk and total_topdesk > 0:
        df_topdesk_resumo = pd.DataFrame([
            {
                "total_topdesk": total_topdesk,
                "cidade": cidade_escolhida,
                "api_url": api_url
            }
        ])

    df_comparacao = pd.DataFrame(dados_comparacao)

    return df_topdesk_resumo, df_comparacao


def aba_inicio():
    st.markdown(
        """
        <div class="step-card">
            <div class="step-title">O que este sistema faz?</div>
            <div class="step-description">
                O AtualizaGestor RNP ajuda a atualizar a planilha oficial de gestores escolares
                a partir de arquivos enviados pelos pontos de apoio e comparar com dados do TopDesk/Fabric.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            <div class="step-card">
                <div class="step-title">1. Envie a planilha mestre</div>
                <div class="step-description">
                    Use a LISTA DE GESTORES.xlsx oficial como base.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            """
            <div class="step-card">
                <div class="step-title">2. Envie o arquivo recebido</div>
                <div class="step-description">
                    Pode ser PDF, Excel, Word ou CSV enviado pelo ponto de apoio.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            """
            <div class="step-card">
                <div class="step-title">3. Baixe o resultado</div>
                <div class="step-description">
                    O sistema gera uma nova planilha atualizada para download.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.info(
        "Na versão web, o sistema não altera diretamente o SharePoint. "
        "Ele gera uma nova planilha atualizada para você baixar e substituir no local correto."
    )


def aba_atualizar():
    st.markdown(
        """
        <div class="info-box">
            Siga as etapas abaixo. O sistema vai ler o arquivo recebido, atualizar a planilha mestre
            e liberar o download da versão atualizada.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    card_etapa(
        "1",
        "Enviar a planilha mestre",
        "Envie a LISTA DE GESTORES.xlsx oficial que será usada como base da atualização."
    )

    arquivo_planilha_mestre = st.file_uploader(
        "Planilha mestre",
        type=["xlsx"],
        key="upload_planilha_mestre",
        help="Envie a LISTA DE GESTORES.xlsx oficial."
    )

    if arquivo_planilha_mestre:
        st.success("Planilha mestre enviada com sucesso.")

    st.divider()

    card_etapa(
        "2",
        "Selecionar a cidade",
        "Escolha a cidade/fila do projeto para evitar atualizações fora do escopo."
    )

    cidade_escolhida = st.selectbox(
        "Cidade/Fila do projeto",
        CIDADES_PROJETO,
        index=0
    )

    st.divider()

    card_etapa(
        "3",
        "Enviar o arquivo do ponto de apoio",
        "Envie o arquivo recebido com os contatos dos gestores."
    )

    arquivo_ponto_apoio = st.file_uploader(
        "Arquivo recebido do ponto de apoio",
        type=["xlsx", "xls", "csv", "pdf", "docx"],
        key="upload_ponto_apoio"
    )

    if arquivo_ponto_apoio:
        st.success("Arquivo do ponto de apoio enviado com sucesso.")

    st.divider()

    card_etapa(
        "4",
        "Escolher o modo de leitura",
        "Use leitura automática na maioria dos casos. Use mapeamento manual quando o Excel/CSV vier em modelo novo."
    )

    modo_leitura = st.radio(
        "Modo de leitura",
        [
            "Leitura automática",
            "Mapeamento manual de colunas"
        ],
        horizontal=True
    )

    pode_ler = arquivo_ponto_apoio is not None

    if not pode_ler:
        st.warning("Envie o arquivo do ponto de apoio para continuar.")
        return

    if st.button("Ler arquivo recebido", type="primary"):
        limpar_resultados()

        try:
            df_extraido = processar_leitura_arquivo(
                arquivo_ponto_apoio=arquivo_ponto_apoio,
                cidade_escolhida=cidade_escolhida,
                modo_leitura=modo_leitura
            )

            if df_extraido is None or df_extraido.empty:
                st.warning(
                    "Não foi possível extrair dados do arquivo. "
                    "Se for Excel ou CSV, tente usar o mapeamento manual."
                )
            else:
                st.session_state.df_extraido = df_extraido
                st.session_state.df_validado = validar_campos_obrigatorios(df_extraido)

                st.success("Arquivo lido com sucesso.")

        except Exception as erro:
            st.error("Erro ao ler o arquivo recebido.")
            st.exception(erro)

    if st.session_state.df_validado is not None:
        st.divider()

        card_etapa(
            "5",
            "Revisar os dados encontrados",
            "Confira se o sistema encontrou escola, gestor, telefone e e-mail corretamente."
        )

        df_validado = st.session_state.df_validado

        exibir_metricas_validacao(df_validado)

        with st.expander("Ver dados extraídos", expanded=True):
            st.dataframe(
                df_validado,
                use_container_width=True,
                hide_index=True
            )

        csv_validacao = df_validado.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            label="Baixar relatório da leitura",
            data=csv_validacao,
            file_name="relatorio_leitura_arquivo.csv",
            mime="text/csv"
        )

        st.divider()

        card_etapa(
            "6",
            "Comparar com TopDesk/Fabric",
            "Opcional: consulta o Fabric e compara as escolas do TopDesk com os dados encontrados no arquivo."
        )

        st.markdown(
            """
            <div class="warning-box">
                Esta etapa usa a API local publicada via Cloudflare Tunnel.
                Configure API_BASE_URL no Streamlit Secrets.
            </div>
            """,
            unsafe_allow_html=True
        )

        if st.button("Buscar na API e comparar com TopDesk"):
            with st.spinner("Chamando a API local e buscando dados do TopDesk/Fabric..."):
                try:
                    df_topdesk, df_comparacao = comparar_com_topdesk_web(
                        df_validado=df_validado,
                        cidade_escolhida=cidade_escolhida
                    )

                    if df_topdesk.empty:
                        st.warning("Nenhum registro foi encontrado no TopDesk/Fabric para a cidade selecionada.")
                    else:
                        st.session_state.df_topdesk = df_topdesk
                        st.session_state.df_comparacao_topdesk = df_comparacao

                        st.success(
                            f"Comparação realizada com sucesso. Total retornado pela API: {int(df_topdesk.iloc[0]['total_topdesk']) if not df_topdesk.empty and 'total_topdesk' in df_topdesk.columns else len(df_topdesk)}."
                        )

                except Exception as erro:
                    st.error("Erro ao conectar ou comparar com o TopDesk/Fabric.")
                    st.exception(erro)

        if st.session_state.df_comparacao_topdesk is not None:
            df_comparacao = st.session_state.df_comparacao_topdesk

            st.subheader("Resultado da comparação com TopDesk/Fabric")

            exibir_metricas_topdesk(df_comparacao)

            st.dataframe(
                df_comparacao,
                use_container_width=True,
                hide_index=True
            )

            csv_comparacao = df_comparacao.to_csv(index=False).encode("utf-8-sig")

            st.download_button(
                label="Baixar relatório TopDesk/Fabric",
                data=csv_comparacao,
                file_name="relatorio_comparacao_topdesk_fabric.csv",
                mime="text/csv"
            )

        st.divider()

        card_etapa(
            "7",
            "Atualizar a planilha mestre",
            "Clique para aplicar os dados encontrados na LISTA DE GESTORES.xlsx."
        )

        if arquivo_planilha_mestre is None:
            st.warning("Envie a planilha mestre antes de atualizar.")
            return

        st.markdown(
            """
            <div class="warning-box">
                Atenção: a versão web não altera o SharePoint automaticamente.
                Ao final, baixe a planilha atualizada e substitua no local correto.
            </div>
            """,
            unsafe_allow_html=True
        )

        if st.button("Atualizar planilha mestre", type="primary"):
            with st.spinner("Atualizando a planilha mestre..."):
                try:
                    relatorio, planilha_bytes, nome_saida = atualizar_planilha_web(
                        arquivo_planilha_mestre=arquivo_planilha_mestre,
                        df_validado=df_validado,
                        cidade_escolhida=cidade_escolhida
                    )

                    st.session_state.relatorio_atualizacao = relatorio
                    st.session_state.planilha_atualizada_bytes = planilha_bytes
                    st.session_state.nome_planilha_atualizada = nome_saida

                    st.success("Planilha mestre atualizada com sucesso.")

                except PermissionError:
                    st.error(
                        "Não foi possível atualizar a planilha. "
                        "Feche o arquivo se ele estiver aberto e tente novamente."
                    )

                except Exception as erro:
                    st.error("Erro ao atualizar a planilha mestre.")
                    st.exception(erro)

    if st.session_state.relatorio_atualizacao is not None:
        st.divider()

        card_etapa(
            "8",
            "Baixar resultado",
            "Baixe a planilha atualizada e o relatório da atualização."
        )

        relatorio = st.session_state.relatorio_atualizacao

        exibir_metricas_atualizacao(relatorio)

        with st.expander("Ver relatório da atualização", expanded=True):
            st.dataframe(
                relatorio,
                use_container_width=True,
                hide_index=True
            )

        csv_relatorio = relatorio.to_csv(index=False).encode("utf-8-sig")

        col1, col2 = st.columns(2)

        with col1:
            st.download_button(
                label="Baixar LISTA DE GESTORES atualizada",
                data=st.session_state.planilha_atualizada_bytes,
                file_name=st.session_state.nome_planilha_atualizada,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )

        with col2:
            st.download_button(
                label="Baixar relatório da atualização",
                data=csv_relatorio,
                file_name="relatorio_atualizacao_planilha_mestre.csv",
                mime="text/csv"
            )


def aba_orientacoes():
    st.subheader("Como usar corretamente")

    st.markdown(
        """
        1. Sempre envie primeiro a planilha oficial `LISTA DE GESTORES.xlsx`.
        2. Depois selecione a cidade do projeto.
        3. Envie o arquivo recebido do ponto de apoio.
        4. Confira a prévia da leitura.
        5. Opcionalmente, compare com TopDesk/Fabric.
        6. Atualize a planilha.
        7. Baixe a versão atualizada.
        """
    )

    st.subheader("Configuração do TopDesk/Fabric")

    st.write(
        "Para usar a comparação com TopDesk/Fabric na versão web, configure as credenciais no Streamlit Secrets."
    )

    st.code(
        """
DB_DRIVER = "ODBC Driver 18 for SQL Server"
DB_SERVER = "seu-servidor.database.windows.net"
DB_DATABASE = "seu-banco"
DB_UID = "seu-usuario-ou-client-id"
DB_PWD = "sua-senha-ou-secret"
DB_AUTHENTICATION = "ActiveDirectoryServicePrincipal"
DB_ENCRYPT = "yes"
DB_TRUST_SERVER_CERTIFICATE = "no"
DB_CONNECTION_TIMEOUT = "30"
        """,
        language="toml"
    )

    st.subheader("Limitações da versão web")

    st.warning(
        "A versão web ainda não atualiza diretamente o SharePoint. "
        "Ela gera uma nova planilha para download."
    )

    st.subheader("Próximas melhorias")

    st.markdown(
        """
        - Atualizar direto no SharePoint.
        - Melhorar conexão Fabric em ambiente web.
        - Gerar relatório de escolas sem informação.
        - Melhorar leitura de PDFs escaneados.
        - Criar histórico de atualizações.
        """
    )


def main():
    inicializar_estado()
    exibir_cabecalho()

    aba1, aba2, aba3 = st.tabs([
        "Início",
        "Atualizar Gestores",
        "Orientações"
    ])

    with aba1:
        aba_inicio()

    with aba2:
        aba_atualizar()

    with aba3:
        aba_orientacoes()

    st.markdown("---")
    st.markdown(
        """
        <div class="small-text">
            AtualizaGestor RNP — versão web com atualização da planilha e comparação TopDesk/Fabric.
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()