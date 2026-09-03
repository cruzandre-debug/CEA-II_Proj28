# Estrutura do Projeto — IPCA (CEA-IME USP)

Documenta o estado atual dos diretórios `1.DADOS/` e `2.SCRIPTS/`, com foco no que o
pipeline `consolida_bases.py` já produz.

## 1.DADOS/

### 1.1.DADOS_BRUTOS/
Dados baixados do Google Drive em 12/08/2026, sob instrução de Ulisses Magdalena. Não são
modificados — servem apenas de fonte primária. Todos referentes a "São Paulo", Nível
Territorial "Região Metropolitana até 2020" (código `7`).

| Arquivo | Período | Séries distintas |
|---|---|---|
| `tabela_58.csv` | jan/1991 – jul/1999 | 423 |
| `tabela_655.csv` | ago/1999 – jun/2006 | 593 |
| `tabela_2938.csv` | jul/2006 – dez/2011 | 465 |
| `tabela_1419.csv` | jan/2012 – dez/2019 | 464 |
| `tabela_7060.csv` | jan/2020 – abr/2026 | 914 |

`tabela_7060.csv` traz também Nível Territorial `71` ("Categoria Metropolitana"), cujos
registros são descartados no pipeline (irrelevantes / fora do escopo RM São Paulo nível 7).

### 1.2.DADOS_REFINADOS/
Gerados por `2.SCRIPTS/consolida_bases.py` — nunca editados manualmente.

- **`IPCA_CONSOLIDADO_BRUTO.csv`**: concatenação simples das 5 bases brutas, com colunas
  renomeadas para um padrão único e coluna `BASE_ORIGEM` indicando o arquivo de origem de
  cada linha. Sem nenhum filtro de nível territorial ou categoria — é o espelho fiel das
  bases brutas, só que unificado.
- **`IPCA_CONSOLIDADO.csv`**: dataset final, filtrado e tratado (ver passo a passo abaixo).
  É o único arquivo que `app.py` lê.
- **`IPCA_AUSENTES_VAR_MENSAL.csv`**: para cada `CODIGO` que tem ao menos um mês sem
  `IPCA_VAR_MENSAL`, lista quantos meses faltam e em quais intervalos de datas.

### 1.3.DADOS_EXTRAS/
- **`tabelagrupos19992026.csv`**: tabela adicional (BR e SP lado a lado, formato largo,
  uma coluna por grupo/subitem, 1999–2026). Ainda não é lida por nenhum script do
  pipeline e não está versionada no git (aparece como untracked).

## 2.SCRIPTS/

- **`consolida_bases.py`**: pipeline de consolidação (detalhado abaixo).
- **`app.py`**: dashboard Streamlit que lê `IPCA_CONSOLIDADO.csv` e plota as séries
  selecionadas (mensal, acum. 12 meses, acum. no ano) com decomposição STL opcional,
  filtro por tipo de categoria (Geral/Grupo/Subgrupo/Item/Subitem) e por grupo
  (Alimentação/Habitação).
- **`TESTE.ipynb`**: notebook em branco, de rascunho (gitignored).
- **`.vscode/settings.json`**: configuração local do editor (gitignored).

## O que `consolida_bases.py` já faz

1. **Leitura**: lê todos os `.csv` de `1.1.DADOS_BRUTOS/`, padroniza nomes de colunas
   divergentes entre bases (ex.: `tabela_7060.csv` nomeia colunas de forma diferente das
   demais) e marca a origem de cada linha em `BASE_ORIGEM`.
2. **Concatenação**: empilha as 5 bases em `df_consolidado` e classifica cada categoria em
   `CATEGORIA_TIPO` (`GERAL`, `GRUPO`, `SUBGRUPO`, `ITEM`, `SUBITEM`) a partir do tamanho do
   código extraído de `CATEGORIA`. Esse resultado, sem nenhum filtro, é salvo como
   `IPCA_CONSOLIDADO_BRUTO.csv`.
3. **Filtro territorial e temático**: mantém só `NIVEL_TERRITORIAL_COD == 7` (RM São Paulo) e,
   dentro disso, só "Índice geral" + categorias de código iniciado em `1` (Alimentação e
   bebidas) ou `2` (Habitação).
4. **Extração de código/nome**: separa `CATEGORIA` em `CODIGO` e `NOME_ATIVO_BRUTO`
   (`Índice geral` vira código `0`).
5. **Checagem de inconsistências de nome**: compara, para cada `CODIGO`, se o nome bruto
   variou entre as diferentes bases/períodos (ex.: um item escrito de duas formas
   diferentes ao longo do tempo) e imprime um relatório dessas divergências.
6. **Correção manual de nomes**: aplica `MAPA_CORRECAO_NOME_ATIVO` (~70 códigos) para
   padronizar o nome final (`NOME_ATIVO`) das séries com inconsistência de escrita
   identificada no passo anterior. Códigos fora do mapa mantêm o nome bruto original.
7. **Marcação de completude**: classifica cada `CODIGO` em `COMPLETA`, `PARCIAL` ou
   `NENHUMA`, conforme a presença de `IPCA_VAR_MENSAL` ao longo de toda a série.
8. **Remoção de redundância**: descarta o código `2202003` ("Energia elétrica
   residencial"), por ser idêntico ao subgrupo pai `2202` (mesmos valores em todos os
   meses) — mantém só o grupo.
9. **Variações acumuladas**: recalcula `CALC_IPCA_VAR_12M` (últimos 12 meses, janela
   móvel) e `CALC_IPCA_VAR_ANO` (acumulado dentro do ano corrente) a partir de
   `IPCA_VAR_MENSAL`, em vez de usar os campos de acumulado já vindos do IBGE.
10. **Saída final**: grava `IPCA_CONSOLIDADO.csv`, ordenado por `CODIGO` e `MES_COD`.
11. **Levantamento de lacunas**: para cada `CODIGO` com meses ausentes em
    `IPCA_VAR_MENSAL`, formata os intervalos de datas ausentes e salva em
    `IPCA_AUSENTES_VAR_MENSAL.csv`.

**Cobertura confirmada**: todas as séries de Alimentação e Habitação presentes nas bases
brutas (nível territorial 7) chegam ao `IPCA_CONSOLIDADO.csv`, com a única exceção
intencional do `2202003` (passo 8, duplicata exata do `2202`).
