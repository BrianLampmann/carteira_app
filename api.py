"""
Busca cotação atual de ações e FIIs da B3 via Yahoo Finance (yfinance).
Usa yf.download() para buscar TODOS os tickers em uma única requisição em lote,
em vez de uma requisição separada por ticker - isso evita disparar limites de
requisições por rajada do Yahoo Finance.
"""
import pandas as pd
import yfinance as yf
import streamlit as st


@st.cache_data(ttl=900, show_spinner=False)
def get_prices(tickers: list):
    """Busca vários tickers de uma vez (uma única requisição em lote). Retorna dict {ticker: preco}."""
    if not tickers:
        return {}

    tickers_upper = [t.upper() for t in tickers]
    yf_symbols = [f"{t}.SA" for t in tickers_upper]

    try:
        dados = yf.download(
            yf_symbols,
            period="5d",
            interval="1d",
            progress=False,
            group_by="ticker",
            threads=False,
            auto_adjust=True,
        )
    except Exception:
        return {}

    if dados is None or dados.empty:
        return {}

    result = {}
    for ticker, symbol in zip(tickers_upper, yf_symbols):
        try:
            if len(yf_symbols) == 1:
                serie = dados["Close"].dropna()
            else:
                serie = dados[symbol]["Close"].dropna()
            if not serie.empty:
                result[ticker] = float(serie.iloc[-1])
        except Exception:
            continue

    return result


@st.cache_data(ttl=1800, show_spinner=False)
def get_news(ticker: str, limit: int = 5):
    """Busca notícias/fatos relevantes recentes de um ticker via Yahoo Finance.
    Retorna lista de dicts: {titulo, publisher, link, data, imagem, ticker}."""
    try:
        raw = yf.Ticker(f"{ticker.upper()}.SA").news or []
    except Exception:
        return []

    noticias = []
    for item in raw[:limit]:
        content = item.get("content", item) if isinstance(item, dict) else {}

        titulo = content.get("title") or item.get("title") or "Sem título"

        publisher = "—"
        provider = content.get("provider")
        if isinstance(provider, dict):
            publisher = provider.get("displayName") or publisher
        elif item.get("publisher"):
            publisher = item.get("publisher")

        link = ""
        for chave in ("canonicalUrl", "clickThroughUrl"):
            url_obj = content.get(chave)
            if isinstance(url_obj, dict) and url_obj.get("url"):
                link = url_obj["url"]
                break
        if not link:
            link = item.get("link", "")

        data_pub = content.get("pubDate") or item.get("providerPublishTime")

        thumbnail_url = ""
        thumb = content.get("thumbnail") or item.get("thumbnail")
        if isinstance(thumb, dict):
            resolucoes = thumb.get("resolutions") or []
            if resolucoes:
                resolucoes_ordenadas = sorted(resolucoes, key=lambda r: r.get("width", 0))
                thumbnail_url = resolucoes_ordenadas[0].get("url", "")
            elif thumb.get("originalUrl"):
                thumbnail_url = thumb["originalUrl"]

        noticias.append({
            "titulo": titulo, "publisher": publisher, "link": link,
            "data": data_pub, "imagem": thumbnail_url, "ticker": ticker.upper(),
        })

    return noticias


@st.cache_data(ttl=900, show_spinner=False)
def get_price(ticker: str):
    """Retorna o preço atual de um único ticker ou None se falhar."""
    precos = get_prices([ticker])
    return precos.get(ticker.upper())