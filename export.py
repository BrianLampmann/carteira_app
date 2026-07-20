"""
Utilitário de exportação de dados para Excel (.xlsx), usado nas diversas
páginas do app para o usuário baixar seus próprios dados.
"""
import io
import pandas as pd


def dataframes_to_excel_bytes(dataframes: dict):
    """Recebe um dict {nome_da_aba: DataFrame} e retorna os bytes de um .xlsx
    com uma aba por DataFrame. Nomes de aba são truncados em 31 caracteres
    (limite do Excel)."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        algo_escrito = False
        for nome_aba, df in dataframes.items():
            if df is None or df.empty:
                continue
            df.to_excel(writer, sheet_name=str(nome_aba)[:31], index=False)
            algo_escrito = True
        if not algo_escrito:
            pd.DataFrame({"Aviso": ["Nenhum dado para exportar ainda."]}).to_excel(
                writer, sheet_name="Aviso", index=False
            )
    return buffer.getvalue()