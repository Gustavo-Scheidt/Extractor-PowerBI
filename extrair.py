import json
import logging
import os
import time

import requests

from config import (
    ARQUIVO_API_URL,
    ARQUIVO_RESOURCE_KEY,
    HEADERS,
    MAX_TENTATIVAS,
    PASTA_PAYLOADS,
    PASTA_RESPOSTAS,
    TIMEOUT,
    URL,
)

logger = logging.getLogger("extractor_powerbi")


def obter_url_atualizada():
    caminho_url = os.path.join(PASTA_PAYLOADS, ARQUIVO_API_URL)
    if os.path.exists(caminho_url):
        with open(caminho_url, "r", encoding="utf-8") as f:
            url_capturada = f.read().strip()
            if url_capturada:
                return url_capturada
    return URL


def obter_headers_atualizados():
    headers = HEADERS.copy()
    caminho_key = os.path.join(PASTA_PAYLOADS, ARQUIVO_RESOURCE_KEY)

    if not os.path.exists(caminho_key):
        raise RuntimeError(
            f"Resource key não encontrada em '{caminho_key}'. "
            "Rode a captura (capturar_payloads_da_url) antes de extrair."
        )

    with open(caminho_key, "r", encoding="utf-8") as f:
        chave = f.read().strip()
        if not chave:
            raise RuntimeError(f"Resource key vazia em '{caminho_key}'.")
        headers["X-PowerBI-ResourceKey"] = chave

    return headers


def extrair(caminho_payload):
    """
    Lê o payload interceptado e envia uma requisição POST para a API do Power BI
    para obter a resposta com os dados brutos das tabelas.
    """
    try:
        with open(caminho_payload, "r", encoding="utf-8") as f:
            payload = json.load(f)

        if not payload:
            return None

        url = obter_url_atualizada()
        headers = obter_headers_atualizados()

        # Códigos que indicam problema definitivo (resource key inválida/expirada,
        # payload rejeitado etc.) — retentar não vai resolver, então paramos na hora.
        CODIGOS_DEFINITIVOS = {400, 401, 403, 404}

        ultimo_erro = None

        for tentativa in range(1, MAX_TENTATIVAS + 1):
            try:
                resposta = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)

                if resposta.status_code == 200:
                    resposta_json = resposta.json()

                    nome_arquivo = os.path.splitext(os.path.basename(caminho_payload))[0]
                    os.makedirs(PASTA_RESPOSTAS, exist_ok=True)
                    caminho_resposta = os.path.join(PASTA_RESPOSTAS, f"{nome_arquivo}.json")

                    with open(caminho_resposta, "w", encoding="utf-8") as f:
                        json.dump(resposta_json, f, indent=2, ensure_ascii=False)

                    return resposta_json

                ultimo_erro = f"HTTP {resposta.status_code}: {resposta.text[:300]}"

                if resposta.status_code in CODIGOS_DEFINITIVOS:
                    logger.error(
                        "Erro definitivo (HTTP %d) para %s -> %s. "
                        "Provável resource key expirada ou payload inválido; não vou retentar. "
                        "Recapture o dashboard e rode novamente.",
                        resposta.status_code, caminho_payload, ultimo_erro,
                    )
                    return None

                logger.warning(
                    "Tentativa %d/%d falhou (erro transitório) para %s -> %s",
                    tentativa, MAX_TENTATIVAS, caminho_payload, ultimo_erro,
                )

            except requests.RequestException as e:
                ultimo_erro = str(e)
                logger.warning(
                    "Tentativa %d/%d - erro de conexão para %s -> %s",
                    tentativa, MAX_TENTATIVAS, caminho_payload, ultimo_erro,
                )

            if tentativa < MAX_TENTATIVAS:
                time.sleep(1)

        logger.error("Falha definitiva ao extrair %s após %d tentativas: %s", caminho_payload, MAX_TENTATIVAS, ultimo_erro)
        return None

    except Exception as e:
        logger.error("Erro ao extrair %s: %s", caminho_payload, e)
        return None
