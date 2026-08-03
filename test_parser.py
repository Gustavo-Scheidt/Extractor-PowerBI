"""
Teste automatizado do parser.py usando uma resposta DSR simulada e fixa.

Objetivo: se o Power BI mudar o formato de resposta ou alguém alterar a
lógica de decodificação sem querer, esse teste falha na hora — em vez de
descobrir só quando o Excel final sair com dados errados.

Rodar com: python test_parser.py
"""

import pandas as pd

from capturador import _eh_requisicao_payload_powerbi
from parser import parser

# Resposta simulada de um visual com 3 colunas (Categoria, Ano, Valor).
# Linha 1: valores completos.
# Linha 2: repete a coluna 0 (bit 1) via bitmask "R".
# Linha 3: coluna 2 nula (bit 4) via bitmask "Ø".
# "Categoria" usa ValueDict (D0): índices 0/1 -> "Norte"/"Sul".
RESPOSTA_SIMULADA = {
    "results": [
        {
            "result": {
                "data": {
                    "descriptor": {
                        "Select": [
                            {"Name": "Tabela.Categoria"},
                            {"Name": "Tabela.Ano"},
                            {"Name": "Tabela.Valor"},
                        ]
                    },
                    "dsr": {
                        "DS": [
                            {
                                "ValueDicts": {
                                    "D0": ["Norte", "Sul"],
                                },
                                "PH": [
                                    {
                                        "DM0": [
                                            {"S": [{}, {}, {}], "C": [0, 2021, 100]},
                                            {"C": [2022, 150], "R": 1},   # repete coluna 0
                                            {"C": [1, 2023], "Ø": 4},     # coluna 2 nula
                                        ]
                                    }
                                ],
                            }
                        ]
                    },
                }
            }
        }
    ]
}


def test_decodifica_linhas_e_renomeia_colunas():
    df = parser(RESPOSTA_SIMULADA, "teste_visual")

    assert df is not None, "parser retornou None para uma resposta válida"
    assert df.shape == (3, 3), f"esperado 3 linhas x 3 colunas, veio {df.shape}"

    # Colunas devem ter sido renomeadas (descriptor.Select bateu com num_cols)
    assert list(df.columns) == ["Categoria", "Ano", "Valor"], f"colunas: {list(df.columns)}"
    assert df.attrs.get("colunas_identificadas") is True

    # Linha 1: ValueDict resolvido (0 -> "Norte")
    assert df.loc[0, "Categoria"] == "Norte"
    assert df.loc[0, "Ano"] == 2021
    assert df.loc[0, "Valor"] == 100

    # Linha 2: repetiu a Categoria da linha anterior (bitmask R)
    assert df.loc[1, "Categoria"] == "Norte"
    assert df.loc[1, "Ano"] == 2022
    assert df.loc[1, "Valor"] == 150

    # Linha 3: ValueDict resolvido (1 -> "Sul") e Valor nulo (bitmask Ø)
    assert df.loc[2, "Categoria"] == "Sul"
    assert df.loc[2, "Ano"] == 2023
    assert pd.isna(df.loc[2, "Valor"])  # pandas converte None -> NaN em coluna numérica

    print("✔ test_decodifica_linhas_e_renomeia_colunas passou")


def test_resposta_vazia_retorna_none():
    assert parser(None, "vazio") is None
    assert parser({}, "vazio") is None
    print("✔ test_resposta_vazia_retorna_none passou")


def test_reconhece_urls_de_payload_em_diferentes_formatos():
    class RequisicaoFake:
        def __init__(self, url, method):
            self.url = url
            self.method = method

    assert _eh_requisicao_payload_powerbi(RequisicaoFake("https://wabi-brazil-south-b-primary-api.analysis.windows.net/public/reports/querydata?synchronous=true", "POST"))
    assert _eh_requisicao_payload_powerbi(RequisicaoFake("https://wabi-brazil-south-b-primary-api.analysis.windows.net/public/reports/queryData?synchronous=true", "POST"))
    assert not _eh_requisicao_payload_powerbi(RequisicaoFake("https://app.powerbi.com/reportEmbed", "POST"))
    assert not _eh_requisicao_payload_powerbi(RequisicaoFake("https://wabi-brazil-south-b-primary-api.analysis.windows.net/public/reports/querydata?synchronous=true", "GET"))
    print("✔ test_reconhece_urls_de_payload_em_diferentes_formatos passou")


def test_colunas_nao_identificadas_quando_select_nao_bate():
    resposta = {
        "results": [
            {
                "result": {
                    "data": {
                        "descriptor": {"Select": [{"Name": "Tabela.Só_Uma_Coluna"}]},  # não bate com 3 colunas
                        "dsr": {
                            "DS": [
                                {
                                    "ValueDicts": {},
                                    "PH": [{"DM0": [{"S": [{}, {}, {}], "C": [1, 2, 3]}]}],
                                }
                            ]
                        },
                    }
                }
            }
        ]
    }
    df = parser(resposta, "teste_sem_match")
    assert df is not None
    assert df.attrs.get("colunas_identificadas") is False
    assert list(df.columns) == [0, 1, 2]  # nomes genéricos mantidos
    print("✔ test_colunas_nao_identificadas_quando_select_nao_bate passou")


if __name__ == "__main__":
    test_decodifica_linhas_e_renomeia_colunas()
    test_resposta_vazia_retorna_none()
    test_colunas_nao_identificadas_quando_select_nao_bate()
    print("\n🎉 Todos os testes do parser passaram!")
