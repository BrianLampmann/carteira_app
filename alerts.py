"""
Lógica de avaliação dos alertas configurados pelo usuário. Não acessa banco nem
rede diretamente - recebe os dados já carregados e retorna quais alertas
dispararam. Isso facilita testar a lógica isolada.
"""

TIPOS_LABEL = {
    "preco_teto": "Preço teto",
    "preco_chao": "Preço chão",
    "variacao_pct_dia": "Variação no dia",
    "yoc_minimo": "YoC mínimo",
    "concentracao_maxima": "Concentração máxima",
    "meta_patrimonio": "Meta de patrimônio",
}

TIPOS_PRECISA_TICKER = {"preco_teto", "preco_chao", "variacao_pct_dia", "yoc_minimo", "concentracao_maxima"}


def calcular_alertas_disparados(alertas_config, ativos, precos, variacoes, total_geral):
    """Retorna lista de dicts {alerta_id, tipo, ticker, valor_atual, limite} para
    cada alerta ativo cuja condição foi atingida."""
    ativos_por_ticker = {a["ticker"].upper(): a for a in ativos}
    disparados = []

    for al in alertas_config:
        if not al.get("ativo"):
            continue

        tipo = al["tipo"]
        ticker = (al.get("ticker") or "").upper() or None
        limite = al["valor_limite"]

        if tipo == "preco_teto":
            preco_atual = precos.get(ticker) if ticker else None
            if preco_atual is not None and preco_atual >= limite:
                disparados.append({"alerta_id": al["id"], "tipo": tipo, "ticker": ticker,
                                    "valor_atual": preco_atual, "limite": limite})

        elif tipo == "preco_chao":
            preco_atual = precos.get(ticker) if ticker else None
            if preco_atual is not None and preco_atual <= limite:
                disparados.append({"alerta_id": al["id"], "tipo": tipo, "ticker": ticker,
                                    "valor_atual": preco_atual, "limite": limite})

        elif tipo == "variacao_pct_dia":
            variacao = variacoes.get(ticker) if ticker else None
            if variacao is not None and abs(variacao) >= limite:
                disparados.append({"alerta_id": al["id"], "tipo": tipo, "ticker": ticker,
                                    "valor_atual": variacao, "limite": limite})

        elif tipo == "yoc_minimo":
            a = ativos_por_ticker.get(ticker) if ticker else None
            if a and a.get("preco_medio") and a.get("dividendo_anual"):
                yoc = a["dividendo_anual"] / a["preco_medio"] * 100
                if yoc < limite:
                    disparados.append({"alerta_id": al["id"], "tipo": tipo, "ticker": ticker,
                                        "valor_atual": yoc, "limite": limite})

        elif tipo == "concentracao_maxima":
            a = ativos_por_ticker.get(ticker) if ticker else None
            preco_atual = precos.get(ticker) if ticker else None
            if a and total_geral:
                preco_ref = preco_atual or a.get("preco_medio")
                if preco_ref:
                    valor_atual_ativo = a["quantidade"] * preco_ref
                    pct = valor_atual_ativo / total_geral * 100
                    if pct >= limite:
                        disparados.append({"alerta_id": al["id"], "tipo": tipo, "ticker": ticker,
                                            "valor_atual": pct, "limite": limite})

        elif tipo == "meta_patrimonio":
            if total_geral is not None and total_geral >= limite:
                disparados.append({"alerta_id": al["id"], "tipo": tipo, "ticker": None,
                                    "valor_atual": total_geral, "limite": limite})

    return disparados