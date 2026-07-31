# URL padrão da API pública do Power BI.
# É sobrescrita em tempo de execução pela URL realmente capturada
# no dashboard (ver payloads/api_url.txt), então normalmente não
# precisa ser alterada aqui.
URL = "https://wabi-brazil-south-b-primary-api.analysis.windows.net/public/reports/querydata?synchronous=true"

# Cabeçalhos da requisição.
# NÃO defina aqui uma X-PowerBI-ResourceKey fixa: cada dashboard tem a sua
# própria chave, capturada automaticamente em payloads/resource_key.txt.
# Um valor fixo aqui faria requisições irem para o dashboard errado sem avisar.
HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=UTF-8",
    "Origin": "https://app.powerbi.com",
    "Referer": "https://app.powerbi.com/",
}

# Configurações
TIMEOUT = 60
MAX_TENTATIVAS = 3
MAX_PAGINAS = 25

# Pastas
PASTA_PAYLOADS = "payloads"
PASTA_RESPOSTAS = "respostas"
PASTA_CSV = "csv"
PASTA_EXCEL = "excel"
PASTA_LOGS = "logs"

# Arquivos de captura (dentro de PASTA_PAYLOADS)
ARQUIVO_API_URL = "api_url.txt"
ARQUIVO_RESOURCE_KEY = "resource_key.txt"

# Arquivos de log
ARQUIVO_LOG = "logs/extracao.log"
ARQUIVO_LOG_CAPTURA = "logs/captura.log"
