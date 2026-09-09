# =========== BIBLIOTECAS =========== #
import numpy as np
import pandas as pd

from pathlib import Path
# ----------------------------------- #

# Funções/constantes compartilhadas entre consolida_bases.py (IPCA) e
# consolida_bases_inpc.py (INPC): os dois índices usam a mesma classificação
# de categorias do IBGE (9 grupos + Índice geral, códigos de 1/2/4/7
# caracteres) e a mesma metodologia de cálculo de acumulados, número-índice
# e levantamento de lacunas.

# =========== PATHs =========== #
PATH_SCRIPTS         = Path(__file__).parent
PATH_DADOS_BRUTOS    = PATH_SCRIPTS.parent / '1.DADOS' / '1.1.DADOS_BRUTOS'
PATH_DADOS_REFINADOS = PATH_SCRIPTS.parent / '1.DADOS' / '1.2.DADOS_REFINADOS'
# ----------------------------- #

# =========== GRUPO =========== #
# Grupo do IPCA/INPC (1º dígito do CODIGO), por extenso, na nomenclatura oficial do IBGE.
GRUPO_NOMES = {
    '1': 'Alimentação e bebidas',
    '2': 'Habitação',
    '3': 'Artigos de residência',
    '4': 'Vestuário',
    '5': 'Transportes',
    '6': 'Saúde e cuidados pessoais',
    '7': 'Despesas pessoais',
    '8': 'Educação',
    '9': 'Comunicação',
}


def deriva_grupo(codigo_serie):
    return np.where(codigo_serie == '0', 'Índice geral', codigo_serie.str[0].map(GRUPO_NOMES))
# ------------------------------ #


# =========== CATEGORIA_TIPO =========== #
# Determina se uma série é o índice geral. Se não for, pegamos o código usado como prefixo
def deriva_codigo(categoria_serie):
    codigo = categoria_serie.str.split('.', n=1).str[0].str.strip()
    tem_ponto = categoria_serie.str.contains('.', regex=False)
    return codigo.where(tem_ponto, '0')


def classifica_categoria_tipo(codigo_serie):
    tamanho = codigo_serie.str.len()
    return np.select(
        [codigo_serie == '0', tamanho == 1, tamanho == 2, tamanho == 4],
        ['GERAL', 'GRUPO', 'SUBGRUPO', 'ITEM'],
        default='SUBITEM'
    )
# ---------------------------------------- #


# =========== COMPLETUDE =========== #
def calcula_completude(df, colunas_grupo, col_var_mensal):
    # COMPLETUDE_INFO: por colunas_grupo (ex.: CODIGO, ou CODIGO+ABRANGENCIA), se
    # col_var_mensal está ausente em TODOS os meses (NENHUMA), em ALGUNS (PARCIAL) ou em
    # NENHUM (COMPLETA).
    resumo = df.groupby(colunas_grupo)[col_var_mensal].agg(
        n_total='size',
        n_ausente=lambda s: s.isna().sum()
    )
    resumo['COMPLETUDE_INFO'] = np.select(
        [resumo['n_ausente'] == 0, resumo['n_ausente'] == resumo['n_total']],
        ['COMPLETA', 'NENHUMA'],
        default='PARCIAL'
    )
    return df.merge(resumo['COMPLETUDE_INFO'], on=colunas_grupo, how='left')
# ----------------------------------- #


# ========== REDUNDÂNCIA PAI/FILHO =========== #
def deriva_codigo_pai(codigo_serie):
    # Truncamento hierárquico: SUBITEM(7)->ITEM(4)->SUBGRUPO(2)->GRUPO(1). Códigos de
    # GRUPO (1 char) não têm pai nessa lógica (GERAL/'0' não é uma agregação deles).
    tamanho = codigo_serie.str.len()
    return np.select(
        [tamanho == 7, tamanho == 4, tamanho == 2],
        [codigo_serie.str[:4], codigo_serie.str[:2], codigo_serie.str[:1]],
        default=None
    )


def detecta_codigos_redundantes_com_pai(df, colunas_grupo, col_codigo, col_var_mensal, col_mes_cod,
                                         min_meses_comuns=6, tolerancia=1e-6):
    # Detecta, separadamente por colunas_grupo (ex.: ABRANGENCIA), códigos cujo
    # col_var_mensal é idêntico, mês a mês (nos meses em que ambos têm dado), ao do pai
    # imediato na hierarquia — casos em que o IBGE não desagregou aquele nível. Retorna uma
    # lista de tuplas (chave_de_colunas_grupo, codigo, codigo_pai).
    df = df.copy()
    df['_CODIGO_PAI'] = deriva_codigo_pai(df[col_codigo])

    redundantes = []
    for chave_grupo, sub in df.groupby(colunas_grupo):
        serie_por_codigo = sub.pivot_table(index=col_mes_cod, columns=col_codigo, values=col_var_mensal, aggfunc='first')
        pais_por_codigo = sub[[col_codigo, '_CODIGO_PAI']].drop_duplicates().set_index(col_codigo)['_CODIGO_PAI']
        for codigo, pai in pais_por_codigo.items():
            if pai is None or pai not in serie_por_codigo.columns or codigo not in serie_por_codigo.columns:
                continue
            comuns = serie_por_codigo[[codigo, pai]].dropna()
            if len(comuns) < min_meses_comuns:
                continue
            if np.allclose(comuns[codigo], comuns[pai], atol=tolerancia):
                redundantes.append((chave_grupo, codigo, pai))
    return redundantes
# --------------------------------------------- #


# ========== CÁLCULOS DE VARIAÇÃO ACUMULADA E NÚMERO-ÍNDICE ============ #
def var_acumulada(janela_temporal):
    return (np.prod((1 + janela_temporal / 100)) - 1) * 100


def calcula_variacao_acumulada(df, colunas_grupo, col_var_mensal, col_ano_cod, prefixo):
    # CALC_{prefixo}_VAR_12M (últimos 12 meses, janela móvel) e CALC_{prefixo}_VAR_ANO
    # (acumulado dentro do ano corrente), recalculados a partir de col_var_mensal.
    df[f'CALC_{prefixo}_VAR_12M'] = df.groupby(
        by=colunas_grupo, as_index=False
    )[col_var_mensal].rolling(window=12, min_periods=1).apply(var_acumulada, raw=True)[col_var_mensal]

    df[f'CALC_{prefixo}_VAR_ANO'] = df.groupby(
        by=colunas_grupo + [col_ano_cod], as_index=False
    )[col_var_mensal].rolling(window=12, min_periods=1).apply(var_acumulada, raw=True)[col_var_mensal]

    return df


def calcula_numero_indice(df, colunas_grupo, col_var_mensal, col_mes_cod, prefixo, ponto_tempo, base_value=100):
    # Número-índice acumulado, por colunas_grupo, a partir de ponto_tempo (mês-base = base_value).
    # Meses sem col_var_mensal são tratados como variação 0% para o índice não travar em NaN
    # (diferente dos acumulados 12M/ano, que propagam NaN quando há lacuna na janela).
    col_name = f"CALC_NUM_IND_{prefixo}_{str(ponto_tempo)[:4]}"
    df = df.copy()
    df[col_name] = np.nan

    sub = (
        df[df[col_mes_cod] >= ponto_tempo]
        .sort_values(by=colunas_grupo + [col_mes_cod])
        .copy()
    )
    variacao = sub[col_var_mensal].fillna(0)
    # o mês-base não compõe seu próprio índice — por isso o fator dele é 1
    fator = np.where(sub[col_mes_cod] == ponto_tempo, 1.0, 1 + variacao / 100)
    sub['fator'] = fator
    sub[col_name] = sub.groupby(colunas_grupo)['fator'].transform(lambda f: base_value * np.cumprod(f))

    df.loc[sub.index, col_name] = sub[col_name]
    return df
# ------------------------------------------------------------------------ #


# =========== LEVANTAMENTO DE LACUNAS =========== #
def formata_intervalos_ausentes(datas):
    datas = sorted(datas)
    intervalos = []
    inicio = fim = datas[0]
    for data in datas[1:]:
        if (data.year - fim.year) * 12 + (data.month - fim.month) == 1:
            fim = data
        else:
            intervalos.append((inicio, fim))
            inicio = fim = data
    intervalos.append((inicio, fim))

    partes = []
    for ini, fim in intervalos:
        if ini == fim:
            partes.append(ini.strftime('%Y-%m'))
        else:
            partes.append(f"{ini.strftime('%Y-%m')} a {fim.strftime('%Y-%m')}")
    return '; '.join(partes)


def gera_relatorio_lacunas(df, colunas_grupo, col_var_mensal, col_mes_cod, col_nome_ativo='NOME_ATIVO'):
    df_lacunas = df.copy()
    df_lacunas['DATA'] = pd.to_datetime(df_lacunas[col_mes_cod], format='%Y%m')

    linhas = []
    for chave, grupo in df_lacunas.groupby(colunas_grupo):
        datas_ausentes = grupo.loc[grupo[col_var_mensal].isna(), 'DATA'].tolist()
        if not datas_ausentes:
            continue
        chave_tupla = chave if isinstance(chave, tuple) else (chave,)
        linha = dict(zip(colunas_grupo, chave_tupla))
        linha.update({
            'NOME_ATIVO': grupo[col_nome_ativo].iloc[0],
            'N_MESES_TOTAL': len(grupo),
            'N_MESES_AUSENTES': len(datas_ausentes),
            'INTERVALOS_AUSENTES': formata_intervalos_ausentes(datas_ausentes),
        })
        linhas.append(linha)

    return pd.DataFrame(linhas).sort_values('N_MESES_AUSENTES', ascending=False)
# ------------------------------------------------- #
