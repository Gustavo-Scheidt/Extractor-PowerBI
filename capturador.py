import hashlib
import json
import os
import re
from datetime import datetime

from playwright.sync_api import sync_playwright

from config import ARQUIVO_LOG_CAPTURA


def _log_captura(mensagem):
    """
    Grava uma linha no logs/captura.log (com timestamp) e imprime no console.
    """
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    linha = f"[{data_hora}] {mensagem}"
    print(linha)
    try:
        os.makedirs(os.path.dirname(ARQUIVO_LOG_CAPTURA), exist_ok=True)
        with open(ARQUIVO_LOG_CAPTURA, "a", encoding="utf-8") as f:
            f.write(linha + "\n")
    except Exception:
        pass


def capturar_payloads_da_url(url_dashboard, pasta_destino="payloads", max_paginas=25, debug=False):
    os.makedirs(pasta_destino, exist_ok=True)

    estado = {
        "payload_count": 0,
        "pagina_atual": "pagina_01",
        "hashes_vistos": set(),  # Armazena tuplas (pagina, hash) para não duplicar na mesma pagina
        "resource_key": None,
        "url_api": None,
    }

    if debug:
        _log_captura("Modo debug ativado: navegador visível, ações mais lentas para observação.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not debug, slow_mo=250 if debug else 0)
        context = browser.new_context()
        page = context.new_page()

        def interceptar_requisicao(request):
            if "querydata" not in request.url or request.method != "POST":
                return

            if estado["url_api"] is None:
                estado["url_api"] = request.url

            headers = request.headers
            if "x-powerbi-resourcekey" in headers:
                estado["resource_key"] = headers["x-powerbi-resourcekey"]

            try:
                post_data = request.post_data
                if not post_data:
                    return

                # Deduplica considerando a PÁGINA ATUAL
                hash_payload = hashlib.sha256(post_data.encode("utf-8")).hexdigest()
                chave_unica = (estado["pagina_atual"], hash_payload)

                if chave_unica in estado["hashes_vistos"]:
                    _log_captura(
                        f"IGNORADO (duplicado na mesma página) - {estado['pagina_atual']}"
                    )
                    return

                estado["hashes_vistos"].add(chave_unica)
                estado["payload_count"] += 1
                payload_json = json.loads(post_data)

                nome_arquivo = os.path.join(
                    pasta_destino,
                    f"payload_{estado['payload_count']:03d}_{estado['pagina_atual']}.json",
                )
                with open(nome_arquivo, "w", encoding="utf-8") as f:
                    json.dump(payload_json, f, indent=4, ensure_ascii=False)

                _log_captura(
                    f"CAPTURADO - {os.path.basename(nome_arquivo)}"
                )
            except Exception as e:
                _log_captura(f"ERRO ao salvar payload: {e}")

        page.on("request", interceptar_requisicao)

        _log_captura("Acessando a página e aguardando os dados carregarem...")
        try:
            page.goto(url_dashboard, wait_until="load", timeout=30000)
        except Exception as e:
            _log_captura(f"Aviso no carregamento inicial: {e}")

        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

        _log_captura(f"Total de frames na página: {len(page.frames)}")
        for frame in page.frames:
            _log_captura(f"  frame: {frame.url}")

        try:
            iframe_element = page.locator("iframe").first
            if iframe_element.count() > 0:
                iframe_element.scroll_into_view_if_needed(timeout=5000)
                page.wait_for_timeout(3000)
        except Exception as e:
            _log_captura(f"Nenhum iframe localizado via locator: {e}")

        _rolar_e_esperar(page)

        try:
            caminho_screenshot = os.path.join(pasta_destino, "debug_screenshot.png")
            page.screenshot(path=caminho_screenshot, full_page=True)
            _log_captura(f"Screenshot salvo em: {caminho_screenshot}")
        except Exception as e:
            _log_captura(f"Falha ao salvar screenshot: {e}")

        # Navega pelas demais páginas/abas do relatório Power BI
        navegar_paginas_do_relatorio(page, estado, max_paginas=max_paginas)

        if estado["resource_key"]:
            with open(os.path.join(pasta_destino, "resource_key.txt"), "w", encoding="utf-8") as f:
                f.write(estado["resource_key"])

        if estado["url_api"]:
            with open(os.path.join(pasta_destino, "api_url.txt"), "w", encoding="utf-8") as f:
                f.write(estado["url_api"])

        _log_captura(f"Total geral de payloads capturados: {estado['payload_count']}")

        browser.close()


def _rolar_e_esperar(page):
    """Rola a página (e o iframe do relatório) para forçar o carregamento de visuais."""
    for _ in range(4):
        page.mouse.wheel(0, 1000)
        try:
            page.wait_for_load_state("networkidle", timeout=3000)
        except Exception:
            pass
    page.mouse.wheel(0, -4000)
    try:
        page.wait_for_load_state("networkidle", timeout=3000)
    except Exception:
        pass

    for frame in page.frames:
        try:
            frame.evaluate("() => { window.scrollTo(0, document.body.scrollHeight); }")
            page.wait_for_timeout(300)
            frame.evaluate("() => { window.scrollTo(0, 0); }")
        except Exception:
            continue


def _esperar_novo_payload(page, estado, contagem_antes, timeout_ms=8000):
    """Espera ativamente até que pelo menos um payload novo seja adicionado."""
    intervalo = 250
    tempo_total = 0
    while tempo_total < timeout_ms:
        page.wait_for_timeout(intervalo)
        tempo_total += intervalo
        if estado["payload_count"] > contagem_antes:
            page.wait_for_timeout(600)
            return


def navegar_paginas_do_relatorio(page, estado, max_paginas=25):
    """
    Navega pelas páginas usando a barra de controle inferior do Power BI (< X of Y >).
    """
    pbi_frame = None
    for frame in page.frames:
        if "powerbi.com" in frame.url:
            pbi_frame = frame
            break

    if not pbi_frame:
        pbi_frame = page

    seletor_voltar = "button[aria-label='Previous Page'], button[aria-label='Página anterior'], .pbi-glyph-chevronleftmedium"
    seletor_avancar = "button[aria-label='Next Page'], button[aria-label='Página seguinte'], .pbi-glyph-chevronrightmedium"

    _log_captura("Verificando navegação inferior (< X of Y >)...")

    # 1. Voltar para a PRIMEIRA página
    for _ in range(10):
        try:
            btn_voltar = pbi_frame.locator(seletor_voltar).first
            if btn_voltar.count() > 0 and btn_voltar.is_visible() and btn_voltar.is_enabled():
                _log_captura("Voltando para a página anterior...")
                btn_voltar.click(force=True, timeout=3000)
                page.wait_for_timeout(2000)
            else:
                break
        except Exception:
            break

    _log_captura("Iniciando varredura das páginas (avançando)...")

    # 2. Avançar página por página
    for i in range(1, max_paginas + 1):
        estado["pagina_atual"] = f"pagina_{i:02d}"
        contagem_antes = estado["payload_count"]

        _rolar_e_esperar(page)
        _esperar_novo_payload(page, estado, contagem_antes)

        novos = estado["payload_count"] - contagem_antes
        _log_captura(f"Página {i}: +{novos} payload(s) capturado(s).")

        try:
            btn_avancar = pbi_frame.locator(seletor_avancar).first
            avancar_disponivel = btn_avancar.count() > 0 and btn_avancar.is_visible() and btn_avancar.is_enabled()

            if avancar_disponivel:
                _log_captura(f"Avançando para a página {i + 1}...")
                btn_avancar.click(force=True, timeout=5000)
                page.wait_for_timeout(3000)
            else:
                # Checagem cruzada: tenta ler o indicador "X de Y" pra confirmar
                # que realmente chegamos na última página, e não que o seletor
                # do botão simplesmente não bateu (relatório com navegação customizada).
                indicador = _ler_indicador_paginas(pbi_frame)
                if indicador:
                    _log_captura(f"Chegou na última página ({indicador}). Fim da navegação.")
                else:
                    _log_captura(
                        "AVISO: botão 'avançar' não encontrado/habilitado e o indicador "
                        "'X de Y' também não foi lido. Pode ser fim real do relatório OU "
                        "navegação customizada não suportada — confira o screenshot final "
                        "e o número de páginas esperado."
                    )
                break
        except Exception as e:
            _log_captura(f"Fim da navegação: {e}")
            break


def _ler_indicador_paginas(pbi_frame):
    """
    Tenta ler o texto tipo '3 of 8' / '3 de 8' que o Power BI costuma exibir
    na barra de navegação inferior, usado só como checagem cruzada — nunca
    como fonte principal de decisão (o layout desse texto pode variar).
    """
    seletor_indicador = ".pageNavigationIndicator, [class*='pageIndicator'], [class*='page-indicator']"
    try:
        elemento = pbi_frame.locator(seletor_indicador).first
        if elemento.count() > 0:
            texto = elemento.inner_text(timeout=1500).strip()
            if texto and re.search(r"\d+\s*(of|de)\s*\d+", texto, re.IGNORECASE):
                return texto
    except Exception:
        pass
    return None


def _slug(texto, tamanho_max=30):
    permitido = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
    texto = texto.strip().replace(" ", "_")
    texto = "".join(c for c in texto if c in permitido)
    return texto[:tamanho_max] if texto else "pagina"