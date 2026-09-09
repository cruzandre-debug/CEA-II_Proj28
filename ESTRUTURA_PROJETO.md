# Estrutura do Projeto — IPCA e INPC (CEA-IME USP)

Documenta o estado atual dos diretórios `1.DADOS/` e `2.SCRIPTS/`: o que os pipelines
`consolida_bases.py` (IPCA) e `consolida_bases_inpc.py` (INPC) produzem, e o que o
dashboard `app.py` faz com esse resultado. O escopo do IPCA já cobre **todos os 9 grupos**
(não só Alimentação/Habitação — ver "Histórico" no fim deste documento). O INPC foi
integrado à mesma estrutura de dados e ao dashboard a partir de 06/09/2026 — `app.py` lê
as duas bases e permite comparar IPCA (SP) × INPC (SP) × INPC (Brasil) lado a lado.

## 1.DADOS/

### 1.1.DADOS_BRUTOS/
Não são modificados — servem apenas de fonte primária. Dividido em duas subpastas, uma por
índice, porque a origem e o formato bruto de cada um são bem diferentes.

#### 1.1.1.IPCA_BRUTO/
Baixados do Google Drive em 12/08/2026, sob instrução de Ulisses Magdalena — exports da API
SIDRA, já em CSV "limpo" (uma linha de cabeçalho, sem rodapé). Todos referentes a "São
Paulo", Nível Territorial "Região Metropolitana até 2020" (código `7`), e já trazem os 9
grupos do IPCA (Alimentação e bebidas, Habitação, Artigos de residência, Vestuário,
Transportes, Saúde e cuidados pessoais, Despesas pessoais, Educação, Comunicação) — o
recorte para só 2 grupos era uma limitação do pipeline antigo, não das bases em si.

| Arquivo | Período | Séries distintas |
|---|---|---|
| `tabela_58.csv` | jan/1991 – jul/1999 | 423 |
| `tabela_655.csv` | ago/1999 – jun/2006 | 593 |
| `tabela_2938.csv` | jul/2006 – dez/2011 | 465 |
| `tabela_1419.csv` | jan/2012 – dez/2019 | 464 |
| `tabela_7060.csv` | jan/2020 – abr/2026 | 914 |

`tabela_7060.csv` traz também Nível Territorial `71` ("Categoria Metropolitana"), cujos
registros são descartados no pipeline (irrelevantes / fora do escopo RM São Paulo nível 7).

#### 1.1.2.INPC_BRUTO/
INPC = mesma metodologia do IPCA, mas com pesos de ponderação calculados a partir de
famílias com renda de 1 a 5 salários mínimos. Adicionados em 06/09/2026. Diferente do IPCA,
são **exports manuais do SIDRA** (não a API), então cada arquivo tem: uma linha de título
antes do cabeçalho; uma coluna de valor sem nome no cabeçalho (na prática são 2 colunas —
valor + unidade `%`); ordem de colunas própria (diferente em cada um dos 5 arquivos); e um
rodapé de fonte/legenda/notas colado direto após a última linha de dado (a partir da linha
que começa com `"Fonte: IBGE`). Valores em formato BR (vírgula decimal); marcadores de
dado ausente `-`, `..`, `...`. Trazem **Brasil inteiro e Região Metropolitana de São Paulo**
juntos (coluna `Nível`/`Cód.`: `BR`/`1` ou `RM`/`3501`) — ao contrário do IPCA, o pipeline
do INPC mantém as duas abrangências (ver `1.2.DADOS_REFINADOS/` abaixo). Não têm coluna de
mês-código (só texto, ex. `"janeiro 1991"`) nem peso mensal em nenhum dos 5 arquivos.

| Arquivo | Período | Variável disponível |
|---|---|---|
| `tabela634.csv` | jan/1991 – jul/1999 | só **acumulada no ano** |
| `tabela651.csv` | ago/1999 – jun/2006 | só **acumulada no ano** |
| `tabela2951.csv` | jul/2006 – dez/2011 | só **mensal** |
| `tabela1100.csv` | jan/2012 – dez/2019 | só **mensal** |
| `tabela7063.csv` | jan/2020 – presente | só **mensal** |

Apesar do título de cada tabela mencionar várias variáveis (mensal, acumulada 12m, acumulada
no ano, peso mensal), cada export manual só contém a variável indicada acima — confirmado
por inspeção direta dos dados. Por isso o pipeline deriva a variação mensal de jan/1991 a
jun/2006 a partir da acumulada no ano (ver `consolida_bases_inpc.py` abaixo).

### 1.2.DADOS_REFINADOS/
Nunca editados manualmente.

#### Saída do IPCA (gerada por `consolida_bases.py`)

- **`IPCA_CONSOLIDADO_BRUTO.csv`**: concatenação simples das 5 bases brutas, com colunas
  renomeadas para um padrão único e coluna `BASE_ORIGEM` indicando o arquivo de origem de
  cada linha. Sem nenhum filtro de nível territorial ou categoria — é o espelho fiel das
  bases brutas, só que unificado.
- **`IPCA_CONSOLIDADO.csv`**: dataset final, filtrado e tratado (ver passo a passo
  abaixo). Lido por `app.py` junto com `INPC_CONSOLIDADO.csv`. Cobre os 9 grupos do IPCA +
  "Índice geral" — **720 séries (`CODIGO`) distintas** no total:

  | GRUPO | Séries |
  |---|---|
  | Alimentação e bebidas | 301 |
  | Artigos de residência | 82 |
  | Vestuário | 66 |
  | Saúde e cuidados pessoais | 57 |
  | Habitação | 51 |
  | Despesas pessoais | 75 |
  | Transportes | 41 |
  | Educação | 34 |
  | Comunicação | 12 |
  | Índice geral | 1 |

  Colunas: `CATEGORIA_COD`, `CATEGORIA` (texto original do IBGE), `CODIGO`,
  `NOME_ATIVO_BRUTO` (nome cru do IBGE), `NOME_ATIVO` (nome corrigido — usar como
  referência), **`GRUPO`** (nome do grupo do IPCA por extenso, ou "Índice geral"),
  `CATEGORIA_TIPO` (`GERAL`/`GRUPO`/`SUBGRUPO`/`ITEM`/`SUBITEM`), `COMPLETUDE_INFO`
  (`COMPLETA`/`PARCIAL`/`NENHUMA`), `ANO_COD`, `MES_COD`, `MES`, `IPCA_VAR_MENSAL`,
  `IPCA_PESO_MENSAL`, `CALC_IPCA_VAR_12M`, `CALC_IPCA_VAR_ANO`, `CALC_NUM_IND_IPCA_2000`,
  `CALC_NUM_IND_IPCA_2005`, `CALC_NUM_IND_IPCA_2010`.
- **`IPCA_AUSENTES_VAR_MENSAL.csv`**: para cada `CODIGO` que tem ao menos um mês sem
  `IPCA_VAR_MENSAL`, lista quantos meses faltam e em quais intervalos de datas (422 das
  720 séries têm ao menos uma lacuna; 211 nunca têm o dado).

#### Saída do INPC (gerada por `consolida_bases_inpc.py`)

- **`INPC_CONSOLIDADO_BRUTO.csv`**: concatenação simples das 5 bases brutas (após remover
  título/rodapé de cada uma e padronizar nomes de coluna), com `BASE_ORIGEM`. Mantém as
  linhas de Brasil e São Paulo (RM) juntas, sem filtro. Colunas: `CATEGORIA`, `ABRANGENCIA`,
  `MES`, `MES_COD`, `VARIAVEL` (qual das 2 variáveis a linha carrega), `VALOR`,
  `CATEGORIA_TIPO`.
- **`INPC_CONSOLIDADO.csv`**: dataset final, filtrado e tratado (ver passo a passo em "O
  que `consolida_bases_inpc.py` faz"). Lido por `app.py` junto com `IPCA_CONSOLIDADO.csv`.
  Cobre os 9 grupos do INPC + "Índice geral" — **732 códigos distintos × 2 abrangências =
  1.464 séries** no total:

  | GRUPO | Códigos distintos |
  |---|---|
  | Alimentação e bebidas | 303 |
  | Artigos de residência | 80 |
  | Vestuário | 71 |
  | Saúde e cuidados pessoais | 61 |
  | Habitação | 50 |
  | Despesas pessoais | 74 |
  | Transportes | 45 |
  | Educação | 33 |
  | Comunicação | 14 |
  | Índice geral | 1 |

  Colunas: `CATEGORIA`, `CODIGO`, `NOME_ATIVO_BRUTO`, `NOME_ATIVO` (corrigido
  automaticamente — ver passo 6/7 abaixo, não há mapa manual como no IPCA), `GRUPO`,
  `CATEGORIA_TIPO`, **`ABRANGENCIA`** (`Brasil` ou `São Paulo (RM)` — coluna que não existe
  no IPCA, que só cobre RM São Paulo), `COMPLETUDE_INFO`, `ANO_COD`, `MES_COD`, `MES`,
  `INPC_VAR_MENSAL` (parte bruta, parte derivada — ver abaixo), `INPC_PESO_MENSAL`
  (**sempre vazia**: nenhuma das 5 bases brutas do INPC traz peso mensal; mantida só por
  paridade estrutural com o IPCA), `CALC_INPC_VAR_12M`, `CALC_INPC_VAR_ANO`,
  `CALC_NUM_IND_INPC_2000`, `CALC_NUM_IND_INPC_2005`, `CALC_NUM_IND_INPC_2010`.
- **`INPC_AUSENTES_VAR_MENSAL.csv`**: igual ao equivalente do IPCA, mas particionado por
  `(CODIGO, ABRANGENCIA)` (467 das 1.464 séries têm ao menos uma lacuna; 229 nunca têm o
  dado).

### 1.3.DADOS_EXTRAS/
- **`tabelagrupos19992026.csv`**: tabela adicional (BR e SP lado a lado, formato largo,
  uma coluna por grupo/subitem, 1999–2026). Ainda não é lida por nenhum script do
  pipeline e não está versionada no git (aparece como untracked).

## 2.SCRIPTS/

- **`consolida_comum.py`**: funções e constantes compartilhadas entre os dois pipelines
  (`GRUPO_NOMES`, classificação de `CATEGORIA_TIPO`, cálculo de completude, de
  variação acumulada/número-índice, detecção de redundância pai/filho e geração do
  relatório de lacunas) — extraído ao integrar o INPC para não duplicar a lógica que os
  dois índices compartilham.
- **`consolida_bases.py`**: pipeline de consolidação do IPCA (detalhado abaixo).
- **`consolida_bases_inpc.py`**: pipeline de consolidação do INPC (detalhado abaixo).
- **`app.py`**: dashboard Streamlit (detalhado abaixo). Lê `IPCA_CONSOLIDADO.csv` e
  `INPC_CONSOLIDADO.csv`.
- **`TESTE.ipynb`**: notebook em branco, de rascunho (gitignored).
- **`.vscode/settings.json`**: configuração local do editor (gitignored).

## O que `consolida_bases.py` faz

1. **Leitura**: lê todos os `.csv` de `1.1.DADOS_BRUTOS/1.1.1.IPCA_BRUTO/`, padroniza nomes
   de colunas divergentes entre bases (ex.: `tabela_7060.csv` nomeia colunas de forma
   diferente das demais) e marca a origem de cada linha em `BASE_ORIGEM`.
2. **Concatenação**: empilha as 5 bases em `df_consolidado` e classifica cada categoria em
   `CATEGORIA_TIPO` (`GERAL`, `GRUPO`, `SUBGRUPO`, `ITEM`, `SUBITEM`) a partir do tamanho do
   código extraído de `CATEGORIA` (1/2/4/7 caracteres respectivamente — vale sem exceção
   para os 9 grupos). Esse resultado, sem nenhum filtro, é salvo como
   `IPCA_CONSOLIDADO_BRUTO.csv`.
3. **Filtro territorial**: mantém só `NIVEL_TERRITORIAL_COD == 7` (RM São Paulo). Não há
   mais recorte temático — todo `CODIGO` de 1-9 (mais o "Índice geral") passa por aqui.
4. **Extração de código/nome**: separa `CATEGORIA` em `CODIGO` e `NOME_ATIVO_BRUTO`
   (`Índice geral` vira código `0`).
5. **Grupo do IPCA**: deriva a coluna `GRUPO` a partir do 1º dígito do `CODIGO`, mapeado
   para o nome oficial do IBGE (`GRUPO_NOMES`); código `0` vira `'Índice geral'`.
6. **Checagem de inconsistências de nome**: compara, para cada `CODIGO`, se o nome bruto
   variou entre as diferentes bases/períodos (ex.: um item escrito de duas formas
   diferentes ao longo do tempo) e imprime um relatório dessas divergências.
7. **Correção manual de nomes**: aplica `MAPA_CORRECAO_NOME_ATIVO` (222 códigos, cobrindo
   os 9 grupos) para padronizar o nome final (`NOME_ATIVO`) das séries com inconsistência
   de escrita identificada no passo anterior. Códigos fora do mapa mantêm o nome bruto
   original. Dois códigos (`3202005`, `7201052`) são reclassificações reais do IBGE ao
   longo do tempo (produto diferente sob o mesmo código, não erro de digitação) — o nome
   mais recente foi mantido, com comentário inline no código explicando o caso.
8. **Marcação de completude**: classifica cada `CODIGO` em `COMPLETA`, `PARCIAL` ou
   `NENHUMA`, conforme a presença de `IPCA_VAR_MENSAL` ao longo de toda a série.
9. **Remoção de redundância**: descarta 16 códigos (lista `CODIGOS_REDUNDANTES_COM_PAI`)
   cujo `IPCA_VAR_MENSAL` é idêntico, mês a mês, ao do pai imediato — casos em que o IBGE
   não desagregou aquele nível (ex.: `2202003` ≡ `2202`, `1201` ≡ `12`, `81` ≡ `8`).
   Mantém-se só o pai em cada caso.
10. **Variações acumuladas e número-índice**: recalcula `CALC_IPCA_VAR_12M` (últimos 12
    meses, janela móvel) e `CALC_IPCA_VAR_ANO` (acumulado dentro do ano corrente) a partir
    de `IPCA_VAR_MENSAL`, em vez de usar os campos de acumulado já vindos do IBGE. Também
    calcula número-índice (base 100) a partir de 3 pontos de referência (jan/2000,
    jan/2005, jan/2010) — meses sem dado tratados como variação 0% para o índice não
    travar em `NaN` (diferente dos acumulados 12M/ano, que propagam `NaN` quando há
    lacuna na janela).
11. **Saída final**: grava `IPCA_CONSOLIDADO.csv`, ordenado por `CODIGO` e `MES_COD`.
12. **Levantamento de lacunas**: para cada `CODIGO` com meses ausentes em
    `IPCA_VAR_MENSAL`, formata os intervalos de datas ausentes e salva em
    `IPCA_AUSENTES_VAR_MENSAL.csv`.

**Cobertura confirmada**: todas as séries dos 9 grupos presentes nas bases brutas (nível
territorial 7) chegam ao `IPCA_CONSOLIDADO.csv`, com exceção intencional dos 16 códigos
redundantes do passo 9.

## O que `consolida_bases_inpc.py` faz

Mesma filosofia do pipeline do IPCA, mas adaptado ao formato de export manual do SIDRA e à
manutenção das 2 abrangências (Brasil e São Paulo/RM).

1. **Leitura**: cada um dos 5 arquivos tem sua própria ordem de colunas
   (`COLUNAS_POR_ARQUIVO`), então são lidos com `names=` posicional (ignorando o cabeçalho
   de texto do arquivo), pulando a linha de título e cortando tudo a partir da linha
   `"Fonte: IBGE` (rodapé de fonte/legenda/notas). Valor convertido de vírgula para ponto
   decimal; marcadores `-`/`..`/`...` viram `NaN`; `MES_COD` é derivado do texto do mês
   (não vem pronto como no IPCA).
2. **Concatenação**: empilha as 5 bases (`BASE_ORIGEM`) e classifica `CATEGORIA_TIPO` a
   partir do `CATEGORIA` bruto — salvo sem filtro em `INPC_CONSOLIDADO_BRUTO.csv`.
3. **Abrangência**: deriva `ABRANGENCIA` (`Brasil` a partir de `Nível=="BR"`/`Cód.=="1"`,
   `São Paulo (RM)` a partir de `Nível=="RM"`/`Cód.=="3501"`). Ao contrário do IPCA, **não
   há filtro territorial** — as duas abrangências seguem para o dataset final.
4. **Extração de código/nome**: mesma lógica do IPCA (`CATEGORIA` → `CODIGO` +
   `NOME_ATIVO_BRUTO`; `Índice geral` vira código `0`).
5. **Grupo**: mesma lógica do IPCA (`deriva_grupo`, `GRUPO_NOMES` compartilhado).
6. **Checagem de inconsistências de nome**: mesmo relatório do IPCA (230 códigos com
   grafia divergente entre bases/períodos).
7. **Correção de nomes — automática**: diferente do IPCA (mapa manual de 222 entradas),
   aqui `NOME_ATIVO` é resolvido automaticamente mantendo o nome do registro **mais
   recente** de cada `CODIGO` — política equivalente à usada manualmente nos 2 casos de
   reclassificação real do IPCA (`3202005`, `7201052`). Não há curadoria manual item a
   item.
8. **Derivação de `INPC_VAR_MENSAL` (jan/1991–jun/2006)**: nesse trecho as bases brutas
   (`tabela634`, `tabela651`) só trazem a variação **acumulada no ano**, não a mensal.
   A mensal é derivada por `(CODIGO, ABRANGENCIA, ANO_COD)`: em janeiro, igual ao
   acumulado; nos demais meses, pela razão entre o acumulado do mês e o do mês anterior.
   Uma checagem de sanidade compara, em todo dezembro desse trecho, o acumulado
   recalculado a partir da mensal derivada contra o valor bruto do IBGE — **validada sem
   nenhuma divergência** na consolidação atual.
9. **Marcação de completude**: igual ao IPCA, mas por `(CODIGO, ABRANGENCIA)`.
10. **Remoção de redundância — detectada automaticamente**: diferente do IPCA (lista fixa
    curada manualmente), aqui cada código é comparado programaticamente com o pai imediato
    na hierarquia (`SUBITEM→ITEM→SUBGRUPO→GRUPO`, por truncamento de código), por
    `ABRANGENCIA`; descartado se a série bater com a do pai em todos os meses em comum
    (mínimo de 6 meses de sobreposição). 28 códigos descartados na consolidação atual.
11. **Variações acumuladas e número-índice**: igual ao IPCA (`calcula_variacao_acumulada`,
    `calcula_numero_indice`), agrupado por `(CODIGO, ABRANGENCIA)`. `INPC_PESO_MENSAL`
    fica sempre `NaN` (nenhuma base bruta traz peso).
12. **Saída final**: grava `INPC_CONSOLIDADO.csv`, ordenado por `CODIGO`, `ABRANGENCIA` e
    `MES_COD`.
13. **Levantamento de lacunas**: igual ao IPCA, mas por `(CODIGO, ABRANGENCIA)`, salvo em
    `INPC_AUSENTES_VAR_MENSAL.csv`.

**Limitação conhecida**: a derivação do passo 8 assume que uma lacuna de mês dentro do
trecho 1991–jun/2006 nunca ocorre no meio de um ano (só detecta e reporta divergência via a
checagem de dezembro); na consolidação atual isso não se confirmou como problema.

## O que `app.py` faz

Dashboard Streamlit (tema claro/escuro, identidade visual IME-USP) que lê
`IPCA_CONSOLIDADO.csv` **e** `INPC_CONSOLIDADO.csv` (cacheados via `@st.cache_data`),
empilha os dois num único dataframe com a coluna `FONTE` (`IPCA (SP)`, `INPC (SP)`,
`INPC (Brasil)` — nomes de coluna de variável harmonizados, ex.: `IPCA_VAR_MENSAL` e
`INPC_VAR_MENSAL` viram ambos `VAR_MENSAL`) e plota as séries selecionadas.

- **Catálogo de séries unificado**: construído pela união dos `CODIGO` das duas bases
  (672 em comum, ~48 só no IPCA, ~60 só no INPC). Quando o nome diverge entre as duas
  fontes, prevalece o `NOME_ATIVO` do IPCA (curado manualmente). Uma série que não existe
  numa fonte simplesmente não aparece nessa fonte no gráfico (sem erro).
- **Sidebar**: seleção de **Fontes** (multiselect — `IPCA (SP)` / `INPC (SP)` /
  `INPC (Brasil)`, todas ativas por padrão), variável (mensal, acum. 12m, acum. no ano,
  número-índice em 3 bases), janela temporal (slider de ano), filtro por grupo (segmented
  control com os 9 grupos do IPCA/INPC, lidos de `GRUPO_ORDER`), e checkboxes de séries
  organizados por `CATEGORIA_TIPO` (com busca textual quando há mais de 15 séries no
  tipo).
- **Controles de visualização** (toggles): Série / Tendência / Sazonalidade (decomposição
  STL, cacheada por série+**fonte**+variável, exige ≥24 meses não-nulos) / paleta
  Daltônico (Okabe-Ito) / **Comparar grupos** (split view) / Mesma escala Y (só com split
  view) / **Linha por fonte** (liga/desliga o padrão de traço por fonte — ver abaixo).
- **Comparar grupos (split view)**: gera dinamicamente **uma coluna por grupo
  efetivamente presente entre as séries selecionadas**; "Índice geral" é replicado em
  todas as colunas como referência. Dentro de cada coluna, uma mesma série pode ter até 3
  linhas (uma por fonte ativa).
- **Linha por fonte**: cor identifica a **série** (como antes); o padrão de traço agora
  identifica a **fonte** (`IPCA (SP)`=sólido, `INPC (SP)`=tracejado,
  `INPC (Brasil)`=pontilhado) — isso é o que viabiliza o caso de uso principal do INPC:
  sobrepor as 3 linhas de uma mesma série (ex. "Alimentação e bebidas") no mesmo eixo para
  ver se o custo de vida de famílias de baixa renda (INPC) diverge muito da média geral
  (IPCA) na mesma região. Quando mais de 1 fonte está ativa, o nome na legenda/hover vira
  `NOME_ATIVO — FONTE` para diferenciar as linhas. O toggle "〰️ Linha por fonte" (ligado
  por padrão) desativa esse estilo, fazendo todas as séries usarem linha sólida.
- **Tabela informativa** (rodapé): uma linha por combinação `(CODIGO, FONTE)`
  efetivamente selecionada, com `NOME_ATIVO`, `FONTE`, `GRUPO`, `CATEGORIA_TIPO` e
  `COMPLETUDE_INFO` — que agora é por fonte (uma série pode estar completa numa fonte e
  ter lacunas em outra).

## Histórico

- O pipeline e o dashboard originalmente cobriam só os grupos 1 (Alimentação e bebidas) e
  2 (Habitação) do IPCA, com um mapa manual de ~92 correções de nome.
- Expandido para os 9 grupos do IPCA: recorte temático removido do pipeline, mapa de
  correção de nomes ampliado para 222 entradas, lista de redundância pai/filho ampliada
  de 1 para 16 códigos, e `app.py` generalizado (grupo, paleta de traço, filtro,
  split-view dinâmicos).
- Adicionada a coluna `GRUPO` ao `IPCA_CONSOLIDADO.csv` (antes o grupo só existia
  calculado em memória dentro do `app.py`) e o toggle "Linha por grupo" no dashboard.
- **06/09/2026**: integração do INPC. `1.1.DADOS_BRUTOS/` reorganizado em subpastas
  (`1.1.1.IPCA_BRUTO/`, `1.1.2.INPC_BRUTO/`); lógica comum aos dois índices extraída para
  `consolida_comum.py`; novo `consolida_bases_inpc.py` cobrindo os 5 brutos do INPC
  (exports manuais do SIDRA, formato bem mais sujo que o do IPCA). Diferente do IPCA, o
  INPC mantém as abrangências Brasil e São Paulo (RM) lado a lado (`ABRANGENCIA`), tem
  `NOME_ATIVO` corrigido automaticamente (sem mapa manual) e `CODIGOS_REDUNDANTES_COM_PAI`
  detectado programaticamente (sem lista fixa).
- **06/09/2026**: INPC integrado ao `app.py`. Nova coluna `FONTE` (`IPCA (SP)`,
  `INPC (SP)`, `INPC (Brasil)`) unifica os dois datasets; catálogo de séries passa a ser a
  união dos `CODIGO` das duas bases (nome do IPCA prevalece em caso de divergência); dash
  por grupo virou **dash por fonte**, permitindo sobrepor as 3 fontes de uma mesma série
  no mesmo eixo — o caso de uso motivador é comparar o custo de vida de famílias de baixa
  renda (INPC) contra a média geral (IPCA) na RM São Paulo.
