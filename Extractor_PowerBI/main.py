import argparse
import logging
import os

from tqdm import tqdm

from utils import (
    configurar_logging,
    criar_pastas,
    limpar_pastas_antigas,
    listar_payloads,
    salvar_csvs_individuais,
    salvar_excel_consolidado,
)

from config import MAX_PAGINAS, PASTA_CSV, PASTA_EXCEL
from extrair import extrair
from parser import parser
from capturador import capturar_payloads_da_url


def parse_args():
    p = argparse.ArgumentParser(description="Extractor Power BI (API pública via captura de rede).")
    p.add_argument("--url", help="URL do dashboard Power BI. Se omitido, será perguntado no console.")
    p.add_argument(
        "--max-paginas",
        type=int,
        default=MAX_PAGINAS,
        help=f"Número máximo de páginas do relatório a percorrer (padrão: {MAX_PAGINAS}).",
    )
    p.add_argument(
        "--sem-csv",
        action="store_true",
        help="Não gerar CSVs individuais por visual (só o Excel consolidado).",
    )
    return p.parse_args()


def main():
    logger = configurar_logging()

    args = parse_args()

    print("╔══════════════════════════════════════════════╗")
    print("║         EXTRACTOR POWER-BI v1.1              ║")
    print("╚══════════════════════════════════════════════╝")

    # 1. Prepara e limpa o ambiente
    criar_pastas()
    limpar_pastas_antigas()

    # 2. Obtém a URL do dashboard (argumento ou input interativo)
    url_dashboard = args.url or input("\n🔗 URL do Dashboard Power BI: ").strip()

    if not url_dashboard:
        logger.error("URL inválida.")
        return

    # 3. Captura os visuais e payloads em tempo real
    logger.info("Capturando payloads de %s", url_dashboard)
    capturar_payloads_da_url(url_dashboard, max_paginas=args.max_paginas)

    # 4. Lista os ficheiros capturados
    payloads = listar_payloads()

    print("\n=== PAYLOADS ENCONTRADOS ===")
    for payload in payloads:
        print(payload)
    print(f"Total de payloads: {len(payloads)}")

    if not payloads:
        logger.error("Nenhum payload foi capturado do dashboard. Verifique a URL.")
        return

    print(f"\n⚙️ Processando {len(payloads)} visual(is)...\n")

    dataframes = {}

    # 5. Processa cada payload
    for caminho_payload in tqdm(payloads, desc="Processando visuais", unit="visual"):
        nome = os.path.splitext(os.path.basename(caminho_payload))[0]

        resposta = extrair(caminho_payload)

        if resposta:
            df = parser(resposta, nome)

            if df is not None:
                print(f"✔ {nome}: {df.shape[0]} linhas x {df.shape[1]} colunas")
                dataframes[nome] = df
            else:
                logger.warning("Parser retornou None para %s", nome)
        else:
            logger.warning("Extrair retornou None para %s", nome)

    # 6. Resumo final
    print("\n=== RESUMO FINAL ===")
    for nome, df in dataframes.items():
        print(f"{nome}: {df.shape[0]} linhas x {df.shape[1]} colunas")
    print(f"Total de DataFrames: {len(dataframes)}")

    if not dataframes:
        logger.error("Nenhum DataFrame foi gerado.")
        return

    # 7. Salva o ficheiro Excel consolidado
    caminho_excel = os.path.join(PASTA_EXCEL, "dashboard_completo.xlsx")
    salvar_excel_consolidado(dataframes, caminho_excel)
    print(f"\n✔ Excel consolidado salvo: {caminho_excel} ({len(dataframes)} aba(s))")

    # 8. Salva CSVs individuais (a menos que --sem-csv tenha sido passado)
    if not args.sem_csv:
        caminhos_csv = salvar_csvs_individuais(dataframes, PASTA_CSV)
        print(f"✔ {len(caminhos_csv)} CSV(s) individuais salvos em {PASTA_CSV}/")

    print("\n🎉 Processo concluído com sucesso!")


if __name__ == "__main__":
    main()
