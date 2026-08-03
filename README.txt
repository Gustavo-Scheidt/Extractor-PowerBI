===============================================================================
                    EXTRACTOR POWER BI
===============================================================================

Este projeto automatiza a captura de dados de relatórios públicos do Power BI,
extraindo payloads da interface, processando as respostas e gerando arquivos em
CSV e Excel para análise posterior.

O fluxo principal é:
1. Capturar os payloads do dashboard via navegador
2. Extrair as respostas da API pública
3. Parsear os dados para DataFrames
4. Salvar os resultados em arquivos estruturados

===============================================================================
                           O QUE O PROJETO FAZ
===============================================================================

- Captura automaticamente os visuais e payloads de um dashboard Power BI
- Processa respostas em formato DSR/DM0
- Converte os dados para DataFrames do pandas
- Gera arquivos CSV individuais por visual
- Gera um arquivo Excel consolidado com múltiplas abas
- Registra logs de execução para facilitar diagnóstico
- Inclui modo debug para acompanhar a captura em tempo real

===============================================================================
                           REQUISITOS
===============================================================================

- Python 3.10 ou superior
- Dependências listadas em requirements.txt
- Navegador compatível com Playwright

Instale as dependências:

    pip install -r requirements.txt

Depois, instale o browser do Playwright:

    playwright install

===============================================================================
                           COMO USAR
===============================================================================

Executar a captura a partir da linha de comando:

    python main.py

Nesse caso, o programa irá pedir a URL do dashboard Power BI no console.
Exemplo:

    URL do Dashboard Power BI: https://app.powerbi.com/view?r=...

Também é possível passar a URL diretamente na execução:

    python main.py --url "https://app.powerbi.com/view?r=..."

Opções úteis:

- --debug
  Roda o navegador em modo visível e mais devagar, útil para depuração.
  Se quiser acompanhar o processo na tela, use:

    python main.py --url "https://app.powerbi.com/view?r=..." --debug

  Contra: o processo wfica mais lento e o navegador fica aberto durante a execução.

- --max-paginas N
  Define o número máximo de páginas a percorrer.

- --sem-csv
  Gera apenas o Excel consolidado, sem salvar CSVs individuais.

===============================================================================
                           ESTRUTURA DO PROJETO
===============================================================================

capturador.py
    Responsável por navegar no dashboard e capturar os payloads.

extrair.py
    Faz a requisição da API pública e salva as respostas obtidas.

parser.py
    Processa o conteúdo JSON da resposta e transforma em DataFrames.

main.py
    Orquestra o fluxo completo da execução.

utils.py
    Funções auxiliares para logs, criação de pastas e exportação de arquivos.

config.py
    Configurações gerais do projeto, pastas e timeouts.

test_parser.py
    Testes automatizados para validar o parser.

payloads/
    Arquivos JSON capturados durante a execução.

respostas/
    Respostas da API salvas para análise.

csv/
    CSVs individuais gerados por visual.

excel/
    Arquivo Excel consolidado com múltiplas abas.

logs/
    Arquivos de log da execução.

===============================================================================
                        MELHORIAS IMPLEMENTADAS
===============================================================================

1. Retry inteligente
   Erros HTTP definitivos como 400, 401, 403 e 404 não são reprocessados.
   Erros transitórios como timeout e 5xx continuam sendo tentados.

2. Relatório de colunas não identificadas
   O parser marca quando um DataFrame ficou com nomes genéricos, permitindo
   revisar manualmente os visuais que precisem de ajuste.

3. Modo debug
   A opção --debug exibe o navegador durante a captura para facilitar a
   identificação de problemas.

4. Verificação de navegação entre páginas
   O capturador tenta identificar corretamente o fim do relatório, incluindo
   cenários com navegação customizada.

5. Testes automatizados do parser
   O projeto já conta com testes para validar decodificação de dados e
   renomeação de colunas.

===============================================================================
                           COMO TESTAR
===============================================================================

Executar os testes do parser:

    python test_parser.py

Executar o fluxo completo:

    python main.py --url "https://app.powerbi.com/view?r=..."

Executar o fluxo completo com navegador visível:
clea

===============================================================================
                           OBSERVAÇÕES
===============================================================================

- O projeto depende da estrutura do dashboard e da resposta retornada pela API.
- Em alguns casos, os nomes das colunas podem não ser identificados
  automaticamente e precisarão de revisão manual.
- Para uso mais estável, é recomendável testar primeiro em dashboards
  pequenos e com navegação simples.

===============================================================================
                           PRÓXIMOS PASSOS
===============================================================================

Algumas melhorias futuras recomendadas:
- adicionar interface gráfica simples;
- implementar reprocessamento de payloads já salvos;
- ampliar testes de integração;
- melhorar a documentação de uso por cenário.
===============================================================================