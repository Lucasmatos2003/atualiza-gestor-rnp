import os
from dotenv import load_dotenv


class FabricConnector:
    def __init__(self):
        load_dotenv(".env")

        self.connection = None

        self.driver = self.get_config("DB_DRIVER", "ODBC Driver 18 for SQL Server")
        self.server = self.get_config("DB_SERVER")
        self.database = self.get_config("DB_DATABASE")
        self.uid = self.get_config("DB_UID")
        self.pwd = self.get_config("DB_PWD")
        self.authentication = self.get_config("DB_AUTHENTICATION", "ActiveDirectoryServicePrincipal")
        self.encrypt = self.get_config("DB_ENCRYPT", "yes")
        self.trust_server_certificate = self.get_config("DB_TRUST_SERVER_CERTIFICATE", "no")
        self.connection_timeout = self.get_config("DB_CONNECTION_TIMEOUT", "30")

        self.validate_config()

    def get_config(self, key, default=None):
        value = os.getenv(key)

        if value:
            return value

        try:
            import streamlit as st

            if key in st.secrets:
                return st.secrets[key]

        except Exception:
            pass

        return default

    def validate_config(self):
        obrigatorios = {
            "DB_DRIVER": self.driver,
            "DB_SERVER": self.server,
            "DB_DATABASE": self.database,
            "DB_UID": self.uid,
            "DB_PWD": self.pwd,
            "DB_AUTHENTICATION": self.authentication
        }

        faltando = [
            chave
            for chave, valor in obrigatorios.items()
            if not valor
        ]

        if faltando:
            raise ValueError(
                "Configurações ausentes para conexão com Fabric: "
                + ", ".join(faltando)
            )

    def build_connection_string(self):
        connection_string = (
            f"Driver={{{self.driver}}};"
            f"Server={self.server};"
            f"Database={self.database};"
            f"Uid={self.uid};"
            f"Pwd={self.pwd};"
            f"Encrypt={self.encrypt};"
            f"TrustServerCertificate={self.trust_server_certificate};"
            f"Connection Timeout={self.connection_timeout};"
            f"Authentication={self.authentication};"
        )

        return connection_string

    def connect(self):
        try:
            import pyodbc
        except ImportError as erro:
            raise ImportError(
                "O pacote pyodbc não está instalado. "
                "Adicione pyodbc no requirements.txt e unixodbc-dev no packages.txt."
            ) from erro

        connection_string = self.build_connection_string()

        self.connection = pyodbc.connect(connection_string)

        return self.connection

    def execute_query(self, query):
        if self.connection is None:
            self.connect()

        cursor = self.connection.cursor()
        cursor.execute(query)

        colunas = [
            coluna[0]
            for coluna in cursor.description
        ]

        resultados = []

        for linha in cursor.fetchall():
            item = {}

            for coluna, valor in zip(colunas, linha):
                if hasattr(valor, "isoformat"):
                    item[coluna] = valor.isoformat()
                else:
                    item[coluna] = valor

            resultados.append(item)

        cursor.close()

        return resultados

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()