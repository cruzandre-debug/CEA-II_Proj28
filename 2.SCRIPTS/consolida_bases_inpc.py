# =========== BIBLIOTECAS =========== #
import io
import datetime as dt

import numpy as np
import pandas as pd

from consolida_comum import (
    PATH_DADOS_REFINADOS,
    deriva_codigo,
    deriva_grupo,
    classifica_categoria_tipo,
    calcula_completude,
    calcula_variacao_acumulada,
    calcula_numero_indice,
    gera_relatorio_lacunas,
    detecta_codigos_redundantes_com_pai,
)
# ----------------------------------- #

# =========== PATHs =========== #
PATH_DADOS_BRUTOS_INPC = PATH_DADOS_REFINADOS.parent / '1.1.DADOS_BRUTOS' / '1.1.2.INPC_BRUTO'
# ----------------------------- #

# Os 5 brutos do INPC são exports manuais do SIDRA (não a API usada para o IPCA), então cada
# um tem: (1) uma linha de título antes do cabeçalho, (2) uma ORDEM DE COLUNAS própria, com
# a coluna de valor sem nome no cabeçalho (na prática são 2 colunas ali: valor + unidade
# "%"), e (3) um rodapé de fonte/legenda/notas colado direto após a última linha de dado.
# Por isso lemos cada arquivo com sua própria lista posicional de nomes, ignorando o
# cabeçalho de texto do arquivo.
COLUNAS_POR_ARQUIVO = {
    'tabela634.csv':  ['NIVEL', 'COD_TERRITORIAL', 'LOCAL', 'CATEGORIA', 'MES', 'VARIAVEL', 'VALOR_BRUTO', 'UNIDADE'],
    'tabela651.csv':  ['NIVEL', 'COD_TERRITORIAL', 'LOCAL', 'VARIAVEL', 'MES', 'CATEGORIA', 'VALOR_BRUTO', 'UNIDADE'],
    'tabela1100.csv': ['NIVEL', 'COD_TERRITORIAL', 'LOCAL', 'MES', 'CATEGORIA', 'VARIAVEL', 'VALOR_BRUTO', 'UNIDADE'],
    'tabela2951.csv': ['NIVEL', 'COD_TERRITORIAL', 'LOCAL', 'VARIAVEL', 'MES', 'CATEGORIA', 'VALOR_BRUTO', 'UNIDADE'],
    'tabela7063.csv': ['CATEGORIA', 'NIVEL', 'COD_TERRITORIAL', 'LOCAL', 'MES', 'VARIAVEL', 'VALOR_BRUTO', 'UNIDADE'],
}

MESES_PT = {
    'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4, 'maio': 5, 'junho': 6,
    'julho': 7, 'agosto': 8, 'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12,
}

MARCADORES_AUSENTE = ['-', '..', '...']


def le_arquivo_inpc(caminho, nomes_colunas):
    with open(caminho, encoding='utf-8-sig') as f:
        linhas = f.readlines()
    fim_dados = next(i for i, linha in enumerate(linhas) if linha.lstrip().startswith('"Fonte: IBGE'))
    conteudo = ''.join(linhas[2:fim_dados])  # pula linha de título e cabeçalho
    return pd.read_csv(io.StringIO(conteudo), sep=';', quotechar='"', header=None, names=nomes_colunas, dtype=str)


def converte_valor(serie_valor_bruto):
    return pd.to_numeric(serie_valor_bruto.replace(MARCADORES_AUSENTE, np.nan).str.replace(',', '.', regex=False))


def deriva_mes_cod(serie_mes):
    partes = serie_mes.str.rsplit(' ', n=1, expand=True)
    mes_nome = partes[0].str.strip().str.lower()
    ano = partes[1].astype(int)
    return ano * 100 + mes_nome.map(MESES_PT)


# =========== LEITURA =========== #
lista_dfs = []
for nome_arquivo, colunas in COLUNAS_POR_ARQUIVO.items():
    df = le_arquivo_inpc(PATH_DADOS_BRUTOS_INPC / nome_arquivo, colunas)
    df['VALOR'] = converte_valor(df['VALOR_BRUTO'])
    df['MES_COD'] = deriva_mes_cod(df['MES'])
    df['BASE_ORIGEM'] = nome_arquivo
    print(f'>>> ✅ Arquivo {nome_arquivo} lido com sucesso. {df.shape[0]} linhas.')
    print(f'>>> ⏱️ Extensão temporal da base: {dt.datetime.strptime(str(df["MES_COD"].min()), "%Y%m")} até '
          f'{dt.datetime.strptime(str(df["MES_COD"].max()), "%Y%m")}')
    print(f'>>> 🔎 Variável presente: {df["VARIAVEL"].unique().tolist()}\n')
    lista_dfs.append(df)

df_consolidado = pd.concat(lista_dfs, axis=0, ignore_index=True)
print(f'>>> ✅ Base consolidada com sucesso. {df_consolidado.shape[0]} linhas.\n')
# ------------------------------ #


# =========== ABRANGÊNCIA (Brasil e São Paulo/RM) =========== #
# Diferente do IPCA (só RM São Paulo), aqui mantemos as duas abrangências disponíveis nos
# brutos do INPC: Brasil inteiro e a Região Metropolitana de São Paulo.
CONDICOES_ABRANGENCIA = [
    (df_consolidado['NIVEL'] == 'BR') & (df_consolidado['COD_TERRITORIAL'] == '1'),
    (df_consolidado['NIVEL'] == 'RM') & (df_consolidado['COD_TERRITORIAL'] == '3501'),
]
df_consolidado['ABRANGENCIA'] = np.select(CONDICOES_ABRANGENCIA, ['Brasil', 'São Paulo (RM)'], default=None)

n_nao_reconhecidas = df_consolidado['ABRANGENCIA'].isna().sum()
if n_nao_reconhecidas:
    print(f'>>> ⚠️ {n_nao_reconhecidas} linha(s) com combinação NIVEL/COD_TERRITORIAL não reconhecida, descartada(s).')
df_consolidado = df_consolidado[df_consolidado['ABRANGENCIA'].notna()].copy()
# ------------------------------------------------------------ #


# =========== BASES BRUTA e REFINADA =========== #
df_consolidado['CATEGORIA_TIPO'] = classifica_categoria_tipo(deriva_codigo(df_consolidado['CATEGORIA']))
df_consolidado[
    ['CATEGORIA', 'ABRANGENCIA', 'MES', 'MES_COD', 'VARIAVEL', 'VALOR', 'CATEGORIA_TIPO', 'BASE_ORIGEM']
].to_csv(PATH_DADOS_REFINADOS / 'INPC_CONSOLIDADO_BRUTO.csv', sep=';', index=False, encoding='utf-8')

df_limpo = df_consolidado[['CATEGORIA', 'ABRANGENCIA', 'MES_COD', 'MES', 'VARIAVEL', 'VALOR']].copy()

df_limpo[['CODIGO', 'NOME_ATIVO_BRUTO']] = df_limpo['CATEGORIA'].str.split('.', n=1, expand=True)
df_limpo['CODIGO'] = df_limpo['CODIGO'].str.strip()
df_limpo['NOME_ATIVO_BRUTO'] = df_limpo['NOME_ATIVO_BRUTO'].str.strip()

# 'Índice geral' não tem '.' no CATEGORIA, então o split joga o nome inteiro em CODIGO.
sem_codigo = df_limpo['NOME_ATIVO_BRUTO'].isna()
df_limpo.loc[sem_codigo, 'NOME_ATIVO_BRUTO'] = df_limpo.loc[sem_codigo, 'CODIGO']
df_limpo.loc[sem_codigo, 'CODIGO'] = '0'

df_limpo['CATEGORIA_TIPO'] = classifica_categoria_tipo(df_limpo['CODIGO'])
df_limpo['GRUPO'] = deriva_grupo(df_limpo['CODIGO'])
df_limpo['ANO_COD'] = df_limpo['MES_COD'] // 100
# ------------------------------ #


# ============ CHECAGEM DE INCONSISTÊNCIAS DOS NOMES BRUTOS ============ #
combinacoes = df_limpo[['CODIGO', 'NOME_ATIVO_BRUTO']].drop_duplicates()
inconsistencias = combinacoes[combinacoes.duplicated(subset='CODIGO', keep=False)].sort_values('CODIGO')

if not inconsistencias.empty:
    print(f'>>> ⚠️ Inconsistências de escrita encontradas para {inconsistencias["CODIGO"].nunique()} código(s) '
          f'(resolvidas automaticamente abaixo, mantendo o nome do registro mais recente):')
    print(inconsistencias.to_string(index=False))
else:
    print('>>> ✅ Nenhuma inconsistência de escrita encontrada entre CODIGO e NOME_ATIVO_BRUTO.')

# Diferente do IPCA (mapa manual construído a partir da checagem acima), aqui resolvemos
# automaticamente mantendo o nome do registro mais recente de cada CODIGO — política que
# corresponde, na prática, ao mesmo critério usado manualmente nas 2 reclassificações reais
# do IBGE identificadas no mapa do IPCA (ver MAPA_CORRECAO_NOME_ATIVO em consolida_bases.py).
indice_mais_recente = df_limpo.groupby('CODIGO')['MES_COD'].idxmax()
nome_mais_recente = df_limpo.loc[indice_mais_recente].set_index('CODIGO')['NOME_ATIVO_BRUTO']
df_limpo['NOME_ATIVO'] = df_limpo['CODIGO'].map(nome_mais_recente)
print(">>> ✅ Limpeza dos nomes das séries concluída. Utilize a coluna NOME_ATIVO como referência.\n")
# ------------------------------ #


# ============== SEPARAÇÃO DAS VARIÁVEIS E DERIVAÇÃO DA VARIAÇÃO MENSAL =============== #
# jan/1991-jul/1999 (tabela634) e ago/1999-jun/2006 (tabela651) só trazem a variação
# acumulada no ano; jul/2006 em diante (tabela2951/1100/7063) só traz a mensal. Cada linha
# já carrega exatamente 1 das 2 variáveis (nunca as 2 juntas), então não há reshape: só
# espalhamos VALOR em 2 colunas conforme VARIAVEL.
df_limpo['INPC_VAR_MENSAL'] = np.where(df_limpo['VARIAVEL'] == 'INPC - Variação mensal', df_limpo['VALOR'], np.nan)
df_limpo['INPC_VAR_ANO_BRUTO'] = np.where(df_limpo['VARIAVEL'] == 'INPC - Variação acumulada no ano', df_limpo['VALOR'], np.nan)

# Deriva a mensal ausente (1991-jun/2006) a partir do acumulado no ano: em janeiro, a
# variação mensal é o próprio acumulado (reinicia todo ano); nos demais meses, é a razão
# entre o acumulado do mês e o do mês anterior dentro do mesmo ano.
df_limpo = df_limpo.sort_values(['CODIGO', 'ABRANGENCIA', 'MES_COD'])
acumulado_anterior = df_limpo.groupby(['CODIGO', 'ABRANGENCIA', 'ANO_COD'])['INPC_VAR_ANO_BRUTO'].shift(1)
variacao_derivada = np.where(
    acumulado_anterior.isna(),
    df_limpo['INPC_VAR_ANO_BRUTO'],
    ((1 + df_limpo['INPC_VAR_ANO_BRUTO'] / 100) / (1 + acumulado_anterior / 100) - 1) * 100
)
df_limpo['INPC_VAR_MENSAL'] = df_limpo['INPC_VAR_MENSAL'].fillna(pd.Series(variacao_derivada, index=df_limpo.index))

# Nenhuma das 5 bases brutas do INPC traz peso mensal (diferente do IPCA, que tem isso na
# tabela_7060 desde 2020) — coluna mantida por paridade estrutural, sempre vazia.
df_limpo['INPC_PESO_MENSAL'] = np.nan
# ------------------------------------------------------------------------------------- #


# ============== ANÁLISE DE DADOS MISSING =============== #
df_limpo = calcula_completude(df_limpo, ['CODIGO', 'ABRANGENCIA'], 'INPC_VAR_MENSAL')
# -------------------------------------------------------- #


# ========== REDUNDÂNCIA PAI/FILHO (detectada automaticamente) ========== #
# Diferente do IPCA (lista fixa, curada manualmente), aqui detectamos programaticamente
# comparando cada código com o pai imediato na hierarquia, separadamente por ABRANGENCIA.
redundantes = detecta_codigos_redundantes_com_pai(df_limpo, ['ABRANGENCIA'], 'CODIGO', 'INPC_VAR_MENSAL', 'MES_COD')
if redundantes:
    print(f'>>> ⚠️ {len(redundantes)} código(s) redundante(s) com o pai imediato (mantido só o pai):')
    for abrangencia, codigo, pai in redundantes:
        print(f'    {abrangencia}: {codigo} == {pai}')
    chaves_redundantes = pd.DataFrame(redundantes, columns=['ABRANGENCIA', 'CODIGO', 'PAI'])[['ABRANGENCIA', 'CODIGO']]
    df_limpo = df_limpo.merge(chaves_redundantes.assign(_REDUNDANTE=True), on=['ABRANGENCIA', 'CODIGO'], how='left')
    df_limpo = df_limpo[df_limpo['_REDUNDANTE'].isna()].drop(columns='_REDUNDANTE')
else:
    print('>>> ✅ Nenhum código redundante com o pai imediato encontrado.')
# ------------------------------------------------------------------------ #


# ========== CÁLCULOS DE VARIAÇÃO ACUMULADA E NÚMERO-ÍNDICE ============ #
df_limpo = calcula_variacao_acumulada(df_limpo, ['CODIGO', 'ABRANGENCIA'], 'INPC_VAR_MENSAL', 'ANO_COD', 'INPC')

PONTOS_NUM_INDICE = [200001, 200501, 201001]
for ponto in PONTOS_NUM_INDICE:
    df_limpo = calcula_numero_indice(df_limpo, ['CODIGO', 'ABRANGENCIA'], 'INPC_VAR_MENSAL', 'MES_COD', 'INPC', ponto)
#--------------------------------------------------------#


# ========== CHECAGEM DE SANIDADE DA DERIVAÇÃO (jan/1991-jun/2006) ========== #
# Em dezembro, o acumulado-no-ano recalculado a partir da INPC_VAR_MENSAL (derivada nesse
# trecho) tem que bater com o valor bruto de "acumulada no ano" de dezembro fornecido pelo
# IBGE. Divergência indica lacuna dentro do ano que quebrou a reconstrução mês a mês.
dezembros = df_limpo[(df_limpo['MES_COD'] % 100 == 12) & df_limpo['INPC_VAR_ANO_BRUTO'].notna()]
divergencias = dezembros[(dezembros['CALC_INPC_VAR_ANO'] - dezembros['INPC_VAR_ANO_BRUTO']).abs() > 0.05]
if not divergencias.empty:
    print(f'>>> ⚠️ {len(divergencias)} série(s)/dezembro com divergência entre a variação anual derivada '
          f'e o valor bruto do IBGE:')
    print(divergencias[['CODIGO', 'ABRANGENCIA', 'MES_COD', 'CALC_INPC_VAR_ANO', 'INPC_VAR_ANO_BRUTO']].to_string(index=False))
else:
    print('>>> ✅ Derivação da variação mensal (1991-jun/2006) validada: acumulado recalculado bate '
          'com o bruto do IBGE em todos os dezembros.')
# ---------------------------------------------------------------------------- #


colunas_finais = ['CATEGORIA', 'CODIGO', 'NOME_ATIVO_BRUTO', 'NOME_ATIVO', 'GRUPO', 'CATEGORIA_TIPO',
                   'ABRANGENCIA', 'COMPLETUDE_INFO', 'ANO_COD', 'MES_COD', 'MES',
                   'INPC_VAR_MENSAL', 'INPC_PESO_MENSAL', 'CALC_INPC_VAR_12M', 'CALC_INPC_VAR_ANO'] + \
                  [f"CALC_NUM_IND_INPC_{str(p)[:4]}" for p in PONTOS_NUM_INDICE]

df_limpo = df_limpo[colunas_finais].sort_values(by=['CODIGO', 'ABRANGENCIA', 'MES_COD'])
df_limpo.to_csv(PATH_DADOS_REFINADOS / 'INPC_CONSOLIDADO.csv', sep=';', index=False, encoding='utf-8')


# =========== LEVANTAMENTO DE LACUNAS EM INPC_VAR_MENSAL =========== #
df_series_com_lacunas = gera_relatorio_lacunas(df_limpo, ['CODIGO', 'ABRANGENCIA'], 'INPC_VAR_MENSAL', 'MES_COD')
df_series_com_lacunas.to_csv(PATH_DADOS_REFINADOS / 'INPC_AUSENTES_VAR_MENSAL.csv', sep=';', index=False, encoding='utf-8')

n_series = len(df_limpo[['CODIGO', 'ABRANGENCIA']].drop_duplicates())
n_total_ausentes = (df_series_com_lacunas['N_MESES_TOTAL'] == df_series_com_lacunas['N_MESES_AUSENTES']).sum()
print(f'\n>>> ⚠️ {len(df_series_com_lacunas)} de {n_series} séries têm ao menos 1 mês sem INPC_VAR_MENSAL '
      f'({n_total_ausentes} delas nunca têm o dado). Detalhe em INPC_AUSENTES_VAR_MENSAL.csv.')
# ------------------------------------------------------------------- #

print("\n>>> 🏁 Bases bruta e refinada do INPC consolidadas em .CSV com sucesso. Encerrando operação. 🏁")
