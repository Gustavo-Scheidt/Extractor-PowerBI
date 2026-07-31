===============================================================================
                    COMO O EXTRACTOR POWER BI FUNCIONA
===============================================================================

1. O PROBLEMA QUE ELE RESOLVE
-------------------------------------------------------------------------------
O dashboard é um relatório Power BI publicado via "Publish to Web". Esse tipo
de relatório não tem exportação de dados habilitada e não usa a API oficial
autenticada do Power BI (Service Principal / OAuth2) — é só um link público.

Por isso, o projeto não "pede" os dados a uma API documentada: ele observa as
próprias requisições que o navegador faz para renderizar os gráficos, e
depois repete essas requisições por conta própria para pegar os dados brutos.

2. O FLUXO, PASSO A PASSO
-------------------------------------------------------------------------------

  ETAPA 1 — CAPTURA (capturador.py, via Playwright)
  Abre a URL do dashboard num Chromium headless e "escuta" toda requisição de
  rede feita pela página. Toda vez que aparece uma requisição POST para o
  endpoint .../querydata (o endpoint interno que o Power BI usa para buscar
  os dados de cada visual), o corpo dessa requisição é salvo como um arquivo
  em payloads/payload_NNN_paginaXX.json. Junto, também são salvos:
    - a resource key do relatório (payloads/resource_key.txt), extraída do
      cabeçalho X-PowerBI-ResourceKey da própria requisição capturada;
    - a URL exata da API (payloads/api_url.txt).
  O script também navega automaticamente pelas páginas do relatório (usando
  os botões "página anterior/seguinte"), pra garantir que os visuais de
  todas as páginas — não só da primeira — sejam capturados.

  ETAPA 2 — REPLAY (extrair.py)
  Cada payload capturado na etapa 1 é reenviado, via requests, para o mesmo
  endpoint .../querydata, usando a resource key salva. A resposta (com os
  dados de verdade) é salva em respostas/payload_NNN_paginaXX.json. Se a
  requisição falhar (erro de rede ou HTTP diferente de 200), há retentativas
  automáticas, e o motivo da falha fica registrado em logs/extracao.log.

  ETAPA 3 — DECODIFICAÇÃO (parser.py)
  A resposta do Power BI não vem como uma tabela simples: ela vem num formato
  comprimido chamado DSR. Para economizar espaço, quando o valor de uma coluna
  se repete de uma linha para a próxima, o Power BI não manda o valor de novo
  — ele só marca, num bitmask ("R"), quais colunas devem repetir o valor da
  linha anterior. Da mesma forma, um bitmask ("Ø") marca quais colunas são
  nulas naquela linha. O parser reconstrói cada linha completa combinando:
    - os valores novos que vieram em "C";
    - os valores repetidos da linha anterior, onde o bitmask R indica;
    - nulos, onde o bitmask Ø indica.
  Depois disso, ele também resolve os "ValueDicts" (Power BI troca valores de
  texto repetidos por um índice numérico, pra economizar espaço, e manda a
  lista real de textos à parte) e, quando possível, renomeia as colunas
  usando os nomes reais dos campos (vindos de descriptor.Select na própria
  resposta) em vez de deixá-las como 0, 1, 2...

  ETAPA 4 — CONSOLIDAÇÃO (main.py / utils.py)
  Cada payload processado vira um DataFrame do pandas. No final, todos os
  DataFrames são salvos como abas de um único arquivo Excel
  (excel/dashboard_completo.xlsx) e, opcionalmente, como CSVs individuais
  (csv/<nome_do_visual>.csv).

3. ESTRUTURA DE ARQUIVOS
-------------------------------------------------------------------------------
config.py       → URLs, headers, timeouts, nomes de pastas/arquivos.
capturador.py   → Etapa 1: captura de payloads via navegador.
extrair.py      → Etapa 2: reenvio dos payloads e obtenção das respostas.
parser.py       → Etapa 3: decodificação do DSR em DataFrame.
utils.py        → Criação/limpeza de pastas, logging, exportação Excel/CSV.
main.py         → Orquestra as 4 etapas (ponto de entrada / CLI).

payloads/       → Payloads capturados + resource_key.txt + api_url.txt.
respostas/      → Respostas brutas da API, uma por visual.
csv/            → CSVs individuais (opcional).
excel/          → dashboard_completo.xlsx consolidado.
logs/           → captura.log (etapa 1) e extracao.log (etapas 2 e 3).

4. COMO RODAR
-------------------------------------------------------------------------------
    python main.py --url "https://app.powerbi.com/view?r=..."

Parâmetros opcionais:
    --max-paginas N   Limite de páginas do relatório a percorrer (padrão: 25)
    --sem-csv         Não gera CSVs individuais, só o Excel consolidado

Se --url for omitido, o programa pergunta a URL interativamente.

5. LIMITAÇÕES CONHECIDAS
--------------------------------------------------------------------------------
- A resource key e a URL da API são específicas de cada dashboard capturado;
  não existe (nem deveria existir) uma chave fixa como fallback.
- A navegação entre páginas depende dos botões padrão do Power BI (seletores
  em inglês/português); relatórios com navegação customizada podem não ser
  detectados.
- Se um visual tiver muitas medidas ou hierarquias, a renomeação automática
  de colunas pode não bater exatamente — nesse caso o código usa nomes
  genéricos (0, 1, 2...) em vez de arriscar um nome errado.
-------------------------------------------------------------------------------