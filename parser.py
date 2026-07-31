import logging

import pandas as pd

logger = logging.getLogger("extractor_powerbi")


def _decodificar_dm0(dm0, num_cols):
    """
    Decodifica as linhas do DM0 respeitando a compressão do Power BI:
    - 'R' (bitmask): coluna repete o valor da linha anterior.
    - 'Ø' (bitmask): coluna é nula nesta linha.
    - Valores que não caem em nenhum dos dois casos vêm em ordem em 'C'.
    """
    linhas = []
    last_row = [None] * num_cols

    for item in dm0:
        c_vals = item.get("C", [])
        c_iter = iter(c_vals)
        r_mask = item.get("R", 0)
        o_mask = item.get("Ø", 0)

        linha = []
        for col in range(num_cols):
            bit = 1 << col
            if r_mask & bit:
                linha.append(last_row[col])
            elif o_mask & bit:
                linha.append(None)
            else:
                val = next(c_iter, None)
                if isinstance(val, dict):
                    val = val.get("R", str(val))
                linha.append(val)

        linhas.append(linha)
        last_row = linha

    return linhas


def _nomes_colunas(resposta_json, num_cols):
    """
    Tenta nomear as colunas usando descriptor.Select (nomes reais dos campos
    do Power BI). Só aplica se o número de campos bater exatamente com o
    número de colunas do DM0 — senão a correspondência é incerta e mantemos
    os nomes genéricos (0, 1, 2...) em vez de arriscar nomear errado.
    """
    try:
        select = (
            resposta_json.get("results", [{}])[0]
            .get("result", {})
            .get("data", {})
            .get("descriptor", {})
            .get("Select", [])
        )
    except Exception:
        return None

    if not select or len(select) != num_cols:
        return None

    nomes = []
    vistos = {}
    for item in select:
        nome = (item.get("Name") or "").strip()
        nome = nome.split(".", 1)[-1] if "." in nome else nome
        nome = nome or "coluna"

        if nome in vistos:
            vistos[nome] += 1
            nome = f"{nome}_{vistos[nome]}"
        else:
            vistos[nome] = 0

        nomes.append(nome)

    return nomes


def parser(resposta_json, nome_visual=""):
    """
    Decodifica o JSON de resposta da API do Power BI.
    Suporta tabelas complexas (DM0, com compressão R/Ø) e cartões de valores simples.

    df.attrs["colunas_identificadas"] indica se os nomes reais das colunas
    (vindos de descriptor.Select) puderam ser aplicados, ou se o DataFrame
    ficou com nomes genéricos (0, 1, 2...).
    """
    if not resposta_json or not isinstance(resposta_json, dict):
        return None

    try:
        # Acessa o nó de dados da resposta
        results = (
            resposta_json.get("results", [{}])[0]
            .get("result", {})
            .get("data", {})
            .get("dsr", {})
            .get("DS", [{}])[0]
        )

        value_dicts = results.get("ValueDicts", {})
        ph_list = results.get("PH", [{}])

        if not ph_list:
            return None

        ph0 = ph_list[0]
        dm0 = ph0.get("DM0", [])

        # --- CASO 1: Tabela padrão / Gráfico (DM0) ---
        if dm0:
            # Número de colunas: schema (S) da primeira linha, com fallback
            # para o tamanho do primeiro C (linhas comprimidas costumam
            # ter menos colunas em C do que o total real).
            num_cols = len(dm0[0].get("S", [])) or len(dm0[0].get("C", []))

            if num_cols:
                linhas = _decodificar_dm0(dm0, num_cols)

                if linhas:
                    df = pd.DataFrame(linhas)

                    # Mapeamento de ValueDicts (D0, D1, etc.) — precisa ser
                    # feito ANTES de renomear, pois usa o índice numérico
                    # original da coluna.
                    for col_idx in df.columns:
                        col_key = f"D{col_idx}"
                        if col_key in value_dicts:
                            dict_val = value_dicts[col_key]
                            df[col_idx] = df[col_idx].apply(
                                lambda x: dict_val[x]
                                if isinstance(x, int) and 0 <= x < len(dict_val)
                                else x
                            )

                    novos_nomes = _nomes_colunas(resposta_json, num_cols)
                    if novos_nomes:
                        df.columns = novos_nomes
                        df.attrs["colunas_identificadas"] = True
                    else:
                        df.attrs["colunas_identificadas"] = False

                    return df

        # --- CASO 2: Cartão de Valor Único / KPI ---
        # Tenta buscar valores diretos em PH / S
        if "S" in ph0:
            valores_s = ph0["S"]
            linhas_s = []
            for item in valores_s:
                if "C" in item:
                    linhas_s.append(item["C"])
            if linhas_s:
                df_s = pd.DataFrame(linhas_s)
                df_s.attrs["colunas_identificadas"] = False  # cartões não usam descriptor.Select
                return df_s

        return None

    except Exception as e:
        logger.warning("Aviso no parser (%s): %s", nome_visual, e)
        return None