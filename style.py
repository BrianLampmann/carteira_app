import streamlit as st


def apply_style():
    st.markdown(
        """
        <style>
        /* Cards de métricas */
        div[data-testid="stMetric"] {
            background-color: #1a1f2b;
            border: 1px solid #2b3346;
            border-radius: 10px;
            padding: 14px 16px;
        }
        div[data-testid="stMetricLabel"] { color: #9aa4b2; }

        /* Tabelas / data editor com cantos arredondados e menos "grid" */
        div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {
            border-radius: 10px;
            overflow: hidden;
            border: 1px solid #2b3346;
        }

        /* Abas maiores e mais destacadas */
        button[data-baseweb="tab"] {
            font-size: 15px;
            padding: 8px 18px;
        }

        /* Títulos das seções */
        h2, h3 { color: #e8ecf3; }

        /* Botões primários */
        button[kind="primary"] {
            border-radius: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def style_valor(val):
    """Colore positivo em verde e negativo em vermelho (usar com Styler.applymap)."""
    if val is None or val != val:  # NaN
        return ""
    color = "#3ddc84" if val >= 0 else "#ff6b6b"
    return f"color: {color}; font-weight: 600;"


def tabela_carteira(df, formatos):
    """Aplica formatação estilo planilha: gradiente verde/vermelho em Valorização e
    Margem (centrado em 0%) e gradiente verde em YoC. `formatos` é o dict passado
    para Styler.format()."""
    styled = df.style.format(formatos, na_rep="—")

    if "Valorização" in df.columns:
        lim = max(abs(df["Valorização"].min()), abs(df["Valorização"].max()), 1)
        styled = styled.background_gradient(cmap="RdYlGn", subset=["Valorização"], vmin=-lim, vmax=lim)
    if "Margem" in df.columns:
        col = df["Margem"].dropna()
        lim = max(abs(col.min()), abs(col.max()), 1) if not col.empty else 1
        styled = styled.background_gradient(cmap="RdYlGn", subset=["Margem"], vmin=-lim, vmax=lim)
    if "YoC" in df.columns:
        styled = styled.background_gradient(cmap="Greens", subset=["YoC"])

    return styled
