import os
import re
import tempfile
import unicodedata
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
        :root {
            --bg-start: #eef2ff;
            --bg-mid: #f8fafc;
            --bg-end: #ecfeff;
            --primary: #4f46e5;
            --primary-2: #7c3aed;
            --accent: #06b6d4;
            --accent-2: #22c55e;
            --danger: #f97316;
            --card: rgba(255, 255, 255, 0.86);
            --card-solid: #ffffff;
            --text: #0f172a;
            --muted: #64748b;
            --border: rgba(148, 163, 184, 0.28);
            --shadow: 0 18px 45px rgba(15, 23, 42, 0.10);
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(79, 70, 229, 0.14), transparent 34%),
                radial-gradient(circle at top right, rgba(6, 182, 212, 0.16), transparent 30%),
                linear-gradient(135deg, var(--bg-start) 0%, var(--bg-mid) 45%, var(--bg-end) 100%);
        }

        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 2rem;
            max-width: 1280px;
        }

        .hero-card {
            position: relative;
            overflow: hidden;
            background:
                linear-gradient(135deg, rgba(15, 23, 42, 0.96) 0%, rgba(49, 46, 129, 0.96) 48%, rgba(14, 116, 144, 0.94) 100%);
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 30px;
            padding: 32px 34px;
            margin-bottom: 24px;
            box-shadow: 0 24px 60px rgba(15, 23, 42, 0.24);
        }

        .hero-card:before {
            content: "";
            position: absolute;
            width: 260px;
            height: 260px;
            border-radius: 50%;
            right: -80px;
            top: -90px;
            background: linear-gradient(135deg, rgba(34, 197, 94, 0.36), rgba(6, 182, 212, 0.12));
            filter: blur(3px);
        }

        .hero-card:after {
            content: "";
            position: absolute;
            width: 180px;
            height: 180px;
            border-radius: 50%;
            left: 50%;
            bottom: -120px;
            background: rgba(124, 58, 237, 0.34);
            filter: blur(8px);
        }

        .hero-content {
            position: relative;
            z-index: 2;
        }

        .hero-badge {
            display: inline-flex;
            gap: 8px;
            align-items: center;
            background: rgba(255, 255, 255, 0.13);
            color: #e0f2fe;
            border: 1px solid rgba(255, 255, 255, 0.22);
            border-radius: 999px;
            padding: 7px 13px;
            font-size: 13px;
            font-weight: 800;
            margin-bottom: 14px;
            backdrop-filter: blur(10px);
        }

        .main-title {
            font-size: 46px;
            line-height: 1.02;
            font-weight: 950;
            letter-spacing: -0.045em;
            color: #ffffff;
            margin-bottom: 10px;
        }

        .subtitle {
            font-size: 17px;
            line-height: 1.6;
            color: #c7d2fe;
            max-width: 900px;
            margin: 0;
        }

        .step-card, .search-box {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 22px;
            padding: 20px;
            margin-bottom: 16px;
            box-shadow: var(--shadow);
            backdrop-filter: blur(14px);
        }

        .step-card {
            border-left: 5px solid var(--primary);
        }

        .step-card:hover, .search-box:hover {
            transform: translateY(-1px);
            border-color: rgba(79, 70, 229, 0.30);
            box-shadow: 0 22px 52px rgba(15, 23, 42, 0.14);
        }

        .step-title {
            font-size: 18px;
            font-weight: 900;
            color: var(--text);
            margin-bottom: 7px;
            letter-spacing: -0.015em;
        }

        .step-description {
            font-size: 14.5px;
            color: var(--muted);
            line-height: 1.58;
        }

        .step-pill {
            display: inline-block;
            background: linear-gradient(135deg, var(--primary), var(--accent));
            color: white;
            border-radius: 999px;
            padding: 3px 10px;
            font-size: 12px;
            font-weight: 900;
            margin-right: 8px;
        }

        .info-box, .success-box, .warning-box {
            border-radius: 18px;
            padding: 16px 18px;
            font-weight: 800;
            margin-bottom: 14px;
            box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
        }

        .info-box {
            background: linear-gradient(135deg, rgba(239, 246, 255, 0.98), rgba(224, 242, 254, 0.95));
            border: 1px solid rgba(59, 130, 246, 0.25);
            color: #1e3a8a;
        }

        .success-box {
            background: linear-gradient(135deg, rgba(236, 253, 245, 0.98), rgba(220, 252, 231, 0.95));
            border: 1px solid rgba(16, 185, 129, 0.28);
            color: #065f46;
        }

        .warning-box {
            background: linear-gradient(135deg, rgba(255, 251, 235, 0.98), rgba(255, 237, 213, 0.95));
            border: 1px solid rgba(249, 115, 22, 0.25);
            color: #9a3412;
        }

        .section-title {
            font-size: 22px;
            font-weight: 950;
            color: var(--text);
            margin-bottom: 4px;
            letter-spacing: -0.025em;
        }

        .section-subtitle {
            font-size: 14px;
            color: var(--muted);
            margin-bottom: 12px;
        }

        .top-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 14px;
            background: rgba(255, 255, 255, 0.78);
            border: 1px solid rgba(148, 163, 184, 0.28);
            border-radius: 22px;
            padding: 12px 16px;
            margin-bottom: 16px;
            box-shadow: 0 12px 32px rgba(15, 23, 42, 0.07);
            backdrop-filter: blur(16px);
        }

        .brand-area {
            display: flex;
            align-items: center;
            gap: 11px;
            min-width: 230px;
        }

        .brand-logo {
            width: 42px;
            height: 42px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 14px;
            background: linear-gradient(135deg, var(--primary), var(--accent));
            color: white;
            font-size: 22px;
            box-shadow: 0 10px 24px rgba(79, 70, 229, 0.24);
        }

        .brand-title {
            font-size: 17px;
            font-weight: 950;
            color: var(--text);
            line-height: 1.1;
        }

        .brand-subtitle {
            font-size: 12px;
            font-weight: 750;
            color: var(--muted);
        }

        .header-actions {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            justify-content: flex-end;
        }

        .header-pill {
            background: #eef2ff;
            color: #3730a3;
            border: 1px solid #c7d2fe;
            border-radius: 999px;
            padding: 7px 11px;
            font-size: 12px;
            font-weight: 900;
            white-space: nowrap;
        }

        .header-pill-green {
            background: #ecfdf5;
            color: #047857;
            border-color: #a7f3d0;
        }

        .footer-card {
            margin-top: 26px;
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.96), rgba(30, 27, 75, 0.96));
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-radius: 24px;
            padding: 20px 22px;
            color: #e5e7eb;
            box-shadow: 0 18px 42px rgba(15, 23, 42, 0.18);
        }

        .footer-grid {
            display: grid;
            grid-template-columns: 1.4fr 1fr 1fr;
            gap: 18px;
            align-items: start;
        }

        .footer-title {
            font-size: 17px;
            font-weight: 950;
            color: #ffffff;
            margin-bottom: 6px;
        }

        .footer-text {
            font-size: 13px;
            color: #cbd5e1;
            line-height: 1.55;
        }

        .footer-label {
            font-size: 12px;
            color: #93c5fd;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: .05em;
            margin-bottom: 6px;
        }

        @media (max-width: 850px) {
            .top-header {
                flex-direction: column;
                align-items: flex-start;
            }

            .header-actions {
                justify-content: flex-start;
            }

            .footer-grid {
                grid-template-columns: 1fr;
            }
        }

        .small-text {
            font-size: 13px;
            color: #64748b;
        }

        div[data-testid="stMetric"] {
            background: var(--card-solid);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 13px 15px;
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
        }

        div[data-testid="stMetricValue"] {
            color: var(--primary);
            font-weight: 950;
        }

        div[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a 0%, #1e1b4b 52%, #164e63 100%);
        }

        div[data-testid="stSidebar"] * {
            color: #e5e7eb;
        }

        div[data-testid="stSidebar"] code {
            color: #0f172a !important;
        }

        .stButton > button, .stDownloadButton > button {
            border-radius: 14px !important;
            border: 1px solid rgba(79, 70, 229, 0.20) !important;
            font-weight: 850 !important;
            box-shadow: 0 8px 22px rgba(79, 70, 229, 0.12);
        }

        .stButton > button:hover, .stDownloadButton > button:hover {
            transform: translateY(-1px);
            border-color: rgba(6, 182, 212, 0.70) !important;
        }

        div[data-testid="stTabs"] button {
            font-weight: 850;
            border-radius: 999px;
        }

        /* Header limpo - versão ajustada */
        .top-header {
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
            gap: 14px !important;
            background: transparent !important;
            border: none !important;
            border-radius: 0 !important;
            padding: 6px 2px 14px 2px !important;
            margin-bottom: 10px !important;
            box-shadow: none !important;
            backdrop-filter: none !important;
        }

        .brand-area {
            display: flex !important;
            align-items: center !important;
            gap: 10px !important;
            min-width: auto !important;
        }

        .brand-logo {
            width: 36px !important;
            height: 36px !important;
            border-radius: 12px !important;
            font-size: 18px !important;
            box-shadow: 0 8px 18px rgba(79, 70, 229, 0.18) !important;
        }

        .brand-title {
            font-size: 16px !important;
            font-weight: 950 !important;
            color: var(--text) !important;
        }

        .brand-subtitle {
            font-size: 12px !important;
            color: #64748b !important;
        }

        .header-actions {
            display: flex !important;
            justify-content: flex-end !important;
            gap: 8px !important;
        }

        .header-pill {
            background: rgba(255, 255, 255, 0.72) !important;
            color: #0f766e !important;
            border: 1px solid rgba(45, 212, 191, 0.35) !important;
            border-radius: 999px !important;
            padding: 6px 10px !important;
            font-size: 12px !important;
            font-weight: 850 !important;
            box-shadow: 0 6px 16px rgba(15, 23, 42, 0.05) !important;
        }


        /* Remove barra padrão do Streamlit: Share, editar, GitHub e menu */
        header[data-testid="stHeader"] {
            display: none !important;
            height: 0px !important;
        }

        div[data-testid="stToolbar"] {
            display: none !important;
            visibility: hidden !important;
            height: 0px !important;
        }

        div[data-testid="stDecoration"] {
            display: none !important;
            height: 0px !important;
        }

        div[data-testid="stStatusWidget"] {
            display: none !important;
        }

        .stDeployButton {
            display: none !important;
        }

        #MainMenu {
            visibility: hidden !important;
            display: none !important;
        }

        footer {
            visibility: hidden !important;
            display: none !important;
        }

        .block-container {
            padding-top: 1.1rem !important;
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

    if "relatorio_arquivos_processados" not in st.session_state:
        st.session_state.relatorio_arquivos_processados = []

    if "modo_acessivel" not in st.session_state:
        st.session_state.modo_acessivel = True


def limpar_resultados():
    st.session_state.df_extraido = None
    st.session_state.df_validado = None
    st.session_state.relatorio_atualizacao = None
    st.session_state.planilha_atualizada_bytes = None
    st.session_state.nome_planilha_atualizada = None
    st.session_state.df_comparacao_topdesk = None
    st.session_state.df_topdesk = None
    st.session_state.relatorio_arquivos_processados = []


def normalizar_dataframe(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=COLUNAS_PADRAO)

    df = df.copy()

    for coluna in COLUNAS_PADRAO:
        if coluna not in df.columns:
            df[coluna] = None

    return df[COLUNAS_PADRAO]




def normalizar_busca(valor):
    if valor is None or pd.isna(valor):
        return ""

    texto = str(valor).lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = texto.encode("ascii", "ignore").decode("utf-8")
    texto = re.sub(r"\s+", " ", texto)

    return texto


def ordenar_colunas_exibicao(df):
    colunas_prioritarias = [
        "inep",
        "escola",
        "gestor",
        "telefone",
        "telefone_2",
        "telefone_3",
        "outros_telefones",
        "email",
        "municipio",
        "status_validacao",
        "status_topdesk",
        "acao_sugerida",
        "origem",
        "fonte_contato"
    ]

    colunas = [coluna for coluna in colunas_prioritarias if coluna in df.columns]
    colunas += [coluna for coluna in df.columns if coluna not in colunas]

    return df[colunas]


def filtrar_por_escola(df, termo):
    if df is None or df.empty:
        return pd.DataFrame()

    termo_normalizado = normalizar_busca(termo)

    if not termo_normalizado:
        return df.copy()

    colunas_busca = [
        coluna
        for coluna in [
            "inep",
            "escola",
            "gestor",
            "telefone",
            "telefone_2",
            "telefone_3",
            "email",
            "municipio",
            "origem",
            "fonte_contato"
        ]
        if coluna in df.columns
    ]

    if not colunas_busca:
        colunas_busca = list(df.columns)

    texto_linhas = df[colunas_busca].fillna("").astype(str).agg(" ".join, axis=1)
    mascara = texto_linhas.apply(lambda valor: termo_normalizado in normalizar_busca(valor))

    return df[mascara].copy()


def painel_pesquisa_escola(df, titulo, key_prefix, expandido=True):
    if df is None or df.empty:
        st.info("Nenhum dado disponível para pesquisa ainda.")
        return

    with st.container():
        st.markdown(
            f"""
            <div class="search-box">
                <div class="section-title">🔎 {titulo}</div>
                <div class="section-subtitle">
                    Pesquise por nome da escola, INEP, gestor, telefone, e-mail ou município.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        termo = st.text_input(
            "Pesquisar escola",
            placeholder="Exemplo: Vanda Guerra, 29476615, Juazeiro, Maria...",
            key=f"pesquisa_{key_prefix}"
        )

        df_filtrado = filtrar_por_escola(df, termo)

        col1, col2 = st.columns(2)
        col1.metric("Total na base", len(df))
        col2.metric("Resultado da pesquisa", len(df_filtrado))

        if termo and df_filtrado.empty:
            st.warning("Nenhuma escola encontrada com esse termo.")
            return

        with st.expander("Ver resultado da pesquisa", expanded=expandido):
            st.dataframe(
                ordenar_colunas_exibicao(df_filtrado),
                use_container_width=True,
                hide_index=True
            )

        csv_pesquisa = df_filtrado.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            label="Baixar resultado da pesquisa",
            data=csv_pesquisa,
            file_name=f"pesquisa_escola_{key_prefix}.csv",
            mime="text/csv",
            key=f"download_pesquisa_{key_prefix}"
        )


def exibir_status_lateral():
    api_url, _ = obter_config_api()

    with st.sidebar:
        st.markdown("### 📘 AtualizaGestor")
        st.caption("Painel rápido da sessão")

        st.session_state.modo_acessivel = st.checkbox(
            "Modo acessível",
            value=st.session_state.get("modo_acessivel", True),
            help="Aumenta áreas clicáveis e deixa a leitura mais confortável."
        )

        st.markdown("---")
        st.markdown("**Status**")
        st.write("Arquivo lido:", "✅ Sim" if st.session_state.df_validado is not None else "⏳ Não")
        st.write("Comparação:", "✅ Sim" if st.session_state.df_comparacao_topdesk is not None else "⏳ Não")
        st.write("Planilha atualizada:", "✅ Sim" if st.session_state.planilha_atualizada_bytes is not None else "⏳ Não")

        st.markdown("---")
        st.markdown("**API usada**")
        st.code(api_url or "API_BASE_URL não configurada", language="text")

        if st.button("Limpar sessão", key="botao_limpar_sessao"):
            limpar_resultados()
            st.rerun()



def exibir_css_acessibilidade():
    if not st.session_state.get("modo_acessivel", True):
        return

    st.markdown(
        """
        <style>
            label, .stMarkdown, .stTextInput, .stSelectbox, .stRadio, .stFileUploader {
                font-size: 1.02rem !important;
            }

            .stButton > button, .stDownloadButton > button {
                min-height: 44px !important;
                padding: 0.6rem 1rem !important;
            }

            input, textarea {
                min-height: 42px !important;
            }

            div[data-testid="stFileUploader"] {
                background: rgba(255, 255, 255, 0.72);
                border-radius: 18px;
                padding: 10px;
            }
    
        /* Header limpo - versão ajustada */
        .top-header {
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
            gap: 14px !important;
            background: transparent !important;
            border: none !important;
            border-radius: 0 !important;
            padding: 6px 2px 14px 2px !important;
            margin-bottom: 10px !important;
            box-shadow: none !important;
            backdrop-filter: none !important;
        }

        .brand-area {
            display: flex !important;
            align-items: center !important;
            gap: 10px !important;
            min-width: auto !important;
        }

        .brand-logo {
            width: 36px !important;
            height: 36px !important;
            border-radius: 12px !important;
            font-size: 18px !important;
            box-shadow: 0 8px 18px rgba(79, 70, 229, 0.18) !important;
        }

        .brand-title {
            font-size: 16px !important;
            font-weight: 950 !important;
            color: var(--text) !important;
        }

        .brand-subtitle {
            font-size: 12px !important;
            color: #64748b !important;
        }

        .header-actions {
            display: flex !important;
            justify-content: flex-end !important;
            gap: 8px !important;
        }

        .header-pill {
            background: rgba(255, 255, 255, 0.72) !important;
            color: #0f766e !important;
            border: 1px solid rgba(45, 212, 191, 0.35) !important;
            border-radius: 999px !important;
            padding: 6px 10px !important;
            font-size: 12px !important;
            font-weight: 850 !important;
            box-shadow: 0 6px 16px rgba(15, 23, 42, 0.05) !important;
        }


        /* Remove barra padrão do Streamlit: Share, editar, GitHub e menu */
        header[data-testid="stHeader"] {
            display: none !important;
            height: 0px !important;
        }

        div[data-testid="stToolbar"] {
            display: none !important;
            visibility: hidden !important;
            height: 0px !important;
        }

        div[data-testid="stDecoration"] {
            display: none !important;
            height: 0px !important;
        }

        div[data-testid="stStatusWidget"] {
            display: none !important;
        }

        .stDeployButton {
            display: none !important;
        }

        #MainMenu {
            visibility: hidden !important;
            display: none !important;
        }

        footer {
            visibility: hidden !important;
            display: none !important;
        }

        .block-container {
            padding-top: 1.1rem !important;
        }

    </style>
        """,
        unsafe_allow_html=True
    )


def exibir_checklist_fluxo(arquivo_planilha_mestre, cidade_escolhida, arquivos_ponto_apoio, modo_leitura):
    total_arquivos = len(arquivos_ponto_apoio) if arquivos_ponto_apoio else 0

    st.markdown("### Conferência rápida")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Planilha mestre",
        "OK" if arquivo_planilha_mestre is not None else "Pendente"
    )

    col2.metric(
        "Cidade",
        cidade_escolhida
    )

    col3.metric(
        "Arquivos enviados",
        total_arquivos
    )

    col4.metric(
        "Modo",
        "Auto" if modo_leitura == "Leitura automática" else "Manual"
    )

    if total_arquivos > 1 and modo_leitura == "Mapeamento manual de colunas":
        st.warning(
            "O mapeamento manual só funciona com 1 arquivo por vez. "
            "Para vários arquivos juntos, use Leitura automática."
        )

def exibir_cabecalho():
    st.markdown(
        """
        <div class="top-header">
            <div class="brand-area">
                <div class="brand-logo">📘</div>
                <div>
                    <div class="brand-title">AtualizaGestor RNP</div>
                    <div class="brand-subtitle">Educação Conectada • Gestão de contatos escolares</div>
                </div>
            </div>
            <div class="header-actions">
                <div class="header-pill">API Local conectada</div>
            </div>
        </div>

        <div class="hero-card">
            <div class="hero-content">
                <div class="hero-badge">✨ Plataforma de apoio operacional</div>
                <div class="main-title">Atualize gestores com mais rapidez</div>
                <div class="subtitle">
                    Envie um ou vários arquivos, valide os contatos, pesquise escolas e compare informações com TopDesk/Fabric em um fluxo simples e visual.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def card_etapa(numero, titulo, descricao):
    st.markdown(
        f"""
        <div class="step-card">
            <div class="step-title"><span class="step-pill">{numero}</span>{titulo}</div>
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




def marcar_origem_arquivo(df, nome_arquivo):
    if df is None or df.empty:
        return normalizar_dataframe(df)

    df = normalizar_dataframe(df)
    df = df.copy()

    nome_arquivo = str(nome_arquivo or "Arquivo enviado")

    def montar_origem(valor):
        valor = str(valor or "").strip()
        if not valor or valor.lower() in ["none", "nan"]:
            return nome_arquivo
        if nome_arquivo.lower() in valor.lower():
            return valor
        return f"{valor} | {nome_arquivo}"

    df["origem"] = df["origem"].apply(montar_origem)

    if "fonte_contato" in df.columns:
        df["fonte_contato"] = df["fonte_contato"].fillna(nome_arquivo)
        df.loc[df["fonte_contato"].astype(str).str.strip().isin(["", "None", "nan"]), "fonte_contato"] = nome_arquivo

    return df


def processar_multiplos_arquivos(arquivos_ponto_apoio, cidade_escolhida, modo_leitura):
    if not arquivos_ponto_apoio:
        return pd.DataFrame(columns=COLUNAS_PADRAO), []

    # No modo manual, mantemos um arquivo por vez para evitar confusão no mapeamento.
    if modo_leitura == "Mapeamento manual de colunas":
        arquivo = arquivos_ponto_apoio[0]
        df = processar_leitura_arquivo(
            arquivo_ponto_apoio=arquivo,
            cidade_escolhida=cidade_escolhida,
            modo_leitura=modo_leitura
        )
        df = marcar_origem_arquivo(df, arquivo.name)

        relatorio = [
            {
                "arquivo": arquivo.name,
                "status": "Lido",
                "registros": len(df),
                "observacao": "Mapeamento manual aplicado"
            }
        ]

        return df, relatorio

    dfs = []
    relatorio = []
    progresso = st.progress(0, text="Preparando leitura dos arquivos...")
    total = len(arquivos_ponto_apoio)

    for indice, arquivo in enumerate(arquivos_ponto_apoio, start=1):
        progresso.progress(
            indice / total,
            text=f"Lendo {indice}/{total}: {arquivo.name}"
        )

        try:
            arquivo.seek(0)

            df = processar_leitura_arquivo(
                arquivo_ponto_apoio=arquivo,
                cidade_escolhida=cidade_escolhida,
                modo_leitura=modo_leitura
            )

            df = marcar_origem_arquivo(df, arquivo.name)

            if df is not None and not df.empty:
                dfs.append(df)

            relatorio.append({
                "arquivo": arquivo.name,
                "status": "Lido" if df is not None and not df.empty else "Sem dados encontrados",
                "registros": 0 if df is None else len(df),
                "observacao": ""
            })

        except Exception as erro:
            relatorio.append({
                "arquivo": arquivo.name,
                "status": "Erro",
                "registros": 0,
                "observacao": str(erro)
            })

    progresso.empty()

    if not dfs:
        return pd.DataFrame(columns=COLUNAS_PADRAO), relatorio

    df_final = pd.concat(dfs, ignore_index=True)
    df_final = normalizar_dataframe(df_final)

    df_final = df_final.drop_duplicates(
        subset=["inep", "escola", "gestor", "telefone", "email"],
        keep="first"
    ).reset_index(drop=True)

    return df_final, relatorio

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
                    Pode enviar um ou vários arquivos: PDF, Excel, Word ou CSV.
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
        "Enviar arquivos do ponto de apoio",
        "Envie um ou mais arquivos recebidos com os contatos dos gestores. Pode misturar PDF, Excel, Word e CSV."
    )

    arquivos_ponto_apoio = st.file_uploader(
        "Arquivos recebidos do ponto de apoio",
        type=["xlsx", "xls", "csv", "pdf", "docx"],
        key="upload_ponto_apoio",
        accept_multiple_files=True,
        help="Você pode enviar mais de um arquivo ao mesmo tempo. Exemplo: Juazeiro Municipal.pdf e Juazeiro Estadual.docx."
    )

    if arquivos_ponto_apoio:
        nomes_arquivos = ", ".join([arquivo.name for arquivo in arquivos_ponto_apoio])
        st.success(f"{len(arquivos_ponto_apoio)} arquivo(s) enviado(s): {nomes_arquivos}")

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
        horizontal=True,
        help="Use Leitura automática para vários arquivos. Use mapeamento manual quando for apenas um Excel/CSV com colunas fora do padrão."
    )

    exibir_checklist_fluxo(
        arquivo_planilha_mestre=arquivo_planilha_mestre,
        cidade_escolhida=cidade_escolhida,
        arquivos_ponto_apoio=arquivos_ponto_apoio,
        modo_leitura=modo_leitura
    )

    pode_ler = arquivos_ponto_apoio is not None and len(arquivos_ponto_apoio) > 0

    if not pode_ler:
        st.warning("Envie pelo menos um arquivo do ponto de apoio para continuar.")
        return

    if len(arquivos_ponto_apoio) > 1 and modo_leitura == "Mapeamento manual de colunas":
        st.info("Para mapear manualmente, envie apenas um arquivo por vez ou altere para Leitura automática.")
        return

    texto_botao_ler = "Ler arquivos recebidos" if len(arquivos_ponto_apoio) > 1 else "Ler arquivo recebido"

    if st.button(texto_botao_ler, type="primary"):
        limpar_resultados()

        try:
            df_extraido, relatorio_arquivos = processar_multiplos_arquivos(
                arquivos_ponto_apoio=arquivos_ponto_apoio,
                cidade_escolhida=cidade_escolhida,
                modo_leitura=modo_leitura
            )

            st.session_state.relatorio_arquivos_processados = relatorio_arquivos

            if df_extraido is None or df_extraido.empty:
                st.warning(
                    "Não foi possível extrair dados dos arquivos. "
                    "Se for Excel ou CSV, tente usar o mapeamento manual com um arquivo por vez."
                )
            else:
                st.session_state.df_extraido = df_extraido
                st.session_state.df_validado = validar_campos_obrigatorios(df_extraido)

                st.success(f"Leitura concluída com sucesso. {len(df_extraido)} registro(s) encontrado(s).")

        except Exception as erro:
            st.error("Erro ao ler os arquivos recebidos.")
            st.exception(erro)

    if st.session_state.df_validado is not None:
        st.divider()

        card_etapa(
            "5",
            "Revisar os dados encontrados",
            "Confira se o sistema encontrou escola, gestor, telefone e e-mail corretamente."
        )

        df_validado = st.session_state.df_validado

        if st.session_state.relatorio_arquivos_processados:
            with st.expander("Ver leitura por arquivo", expanded=False):
                st.dataframe(
                    pd.DataFrame(st.session_state.relatorio_arquivos_processados),
                    use_container_width=True,
                    hide_index=True
                )

        exibir_metricas_validacao(df_validado)

        painel_pesquisa_escola(
            df_validado,
            "Pesquisar no arquivo lido",
            "arquivo_lido",
            expandido=False
        )

        with st.expander("Ver todos os dados extraídos", expanded=True):
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




def aba_pesquisar_escola():
    st.markdown(
        """
        <div class="info-box">
            Use esta área para localizar rapidamente uma escola depois que o arquivo for lido.
            A pesquisa também funciona no relatório de comparação com TopDesk/Fabric, quando ele existir.
        </div>
        """,
        unsafe_allow_html=True
    )

    fontes = []

    if st.session_state.df_validado is not None and not st.session_state.df_validado.empty:
        fontes.append("Arquivo lido")

    if st.session_state.df_comparacao_topdesk is not None and not st.session_state.df_comparacao_topdesk.empty:
        fontes.append("Comparação TopDesk/Fabric")

    if st.session_state.relatorio_atualizacao is not None and not st.session_state.relatorio_atualizacao.empty:
        fontes.append("Relatório da atualização")

    if not fontes:
        st.warning("Primeiro vá na aba Atualizar Gestores e leia um arquivo para liberar a pesquisa.")
        return

    fonte_escolhida = st.radio(
        "Onde deseja pesquisar?",
        fontes,
        horizontal=True
    )

    if fonte_escolhida == "Arquivo lido":
        painel_pesquisa_escola(
            st.session_state.df_validado,
            "Pesquisar escola no arquivo lido",
            "aba_arquivo_lido",
            expandido=True
        )

    elif fonte_escolhida == "Comparação TopDesk/Fabric":
        painel_pesquisa_escola(
            st.session_state.df_comparacao_topdesk,
            "Pesquisar escola na comparação TopDesk/Fabric",
            "aba_topdesk",
            expandido=True
        )

    elif fonte_escolhida == "Relatório da atualização":
        painel_pesquisa_escola(
            st.session_state.relatorio_atualizacao,
            "Pesquisar escola no relatório da atualização",
            "aba_relatorio",
            expandido=True
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

    st.subheader("Configuração da API local")

    st.write(
        "Para usar a comparação com TopDesk/Fabric na versão web, o Streamlit Cloud chama a API local pela URL do Cloudflare Tunnel."
    )

    st.code(
        """
API_BASE_URL = "https://sua-url.trycloudflare.com"
API_TOKEN = ""
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




def exibir_rodape():
    ano_atual = datetime.now().year

    st.markdown(
        f"""
        <div class="footer-card">
            <div class="footer-grid">
                <div>
                    <div class="footer-title">AtualizaGestor RNP</div>
                    <div class="footer-text">
                        Ferramenta de apoio para leitura, validação, pesquisa e atualização de contatos de gestores escolares.
                    </div>
                </div>
                <div>
                    <div class="footer-label">Versão</div>
                    <div class="footer-text">Web • Multi-arquivos • API local</div>
                </div>
                <div>
                    <div class="footer-label">{ano_atual}</div>
                    <div class="footer-text">Educação Conectada • RNP</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def main():
    inicializar_estado()
    exibir_status_lateral()
    exibir_css_acessibilidade()
    exibir_cabecalho()

    aba1, aba2, aba3, aba4 = st.tabs([
        "🏠 Início",
        "📤 Atualizar Gestores",
        "🔎 Pesquisar Escola",
        "📘 Orientações"
    ])

    with aba1:
        aba_inicio()

    with aba2:
        aba_atualizar()

    with aba3:
        aba_pesquisar_escola()

    with aba4:
        aba_orientacoes()

    exibir_rodape()


if __name__ == "__main__":
    main()