# =========== BIBLIOTECAS =========== #
import pandas as pd
import numpy as np

import datetime as dt

from pathlib import Path 
# ----------------------------------- #

# =========== PATHs =========== #
PATH_ATUAL = Path(__file__).parent
PATH_DADOS_BRUTOS    = PATH_ATUAL.parent / '1.DADOS' / '1.1.DADOS_BRUTOS'
PATH_DADOS_REFINADOS = PATH_ATUAL.parent / '1.DADOS' / '1.2.DADOS_REFINADOS'
# ----------------------------- #

# =========== CATEGORIA_TIPO =========== #
# Determina se uma série é o indice geral. Se não for, pegamos o código usaado como prefixo
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

# =========== LEITURA =========== #
lista_dfs = []

for arquivo in PATH_DADOS_BRUTOS.glob('*.csv'):
    df = pd.read_csv(
            arquivo, 
            sep=',',
            quotechar  = '"',
            encoding   = 'utf-8',
            low_memory = False)
    df.rename(columns = {
        'Região Metropolitana até 2020 e Categoria Metropolitana (Código)' : 'Região Metropolitana até 2020 (Código)',
        'Região Metropolitana até 2020 e Categoria Metropolitana' : 'Região Metropolitana até 2020',
        'Geral, grupos, subgrupos, itens e subitens (Código)' : 'Geral, grupo, subgrupo, item e subitem (Código)',
        'Geral, grupos, subgrupos, itens e subitens' : 'Geral, grupo, subgrupo, item e subitem'
    }, inplace=True)
    print(f'>>> ✅ Arquivo {arquivo.name} lido com sucesso. {df.shape[0]} linhas e {df.shape[1]} colunas.')
    print(f'>>> ⏱️ Extensão temporal da base: {dt.datetime.strptime(str(df["Mês (Código)"].min()), "%Y%m")} até {dt.datetime.strptime(str(df["Mês (Código)"].max()), "%Y%m")}\n')
    df['BASE_ORIGEM'] = arquivo.name
    lista_dfs.append(df)

df_consolidado = pd.concat(lista_dfs, axis=0, ignore_index=True)
print(f'>>> ✅ Base consolidada com sucesso. {df_consolidado.shape[0]} linhas e {df_consolidado.shape[1]} colunas.')
print(f'>>> ⏱️ Extensão temporal da base consolidada: {dt.datetime.strptime(str(df_consolidado["Mês (Código)"].min()), "%Y%m")} até {dt.datetime.strptime(str(df_consolidado["Mês (Código)"].max()), "%Y%m")}\n')

df_consolidado.rename(columns = 
                     {
    'Nível Territorial (Código)': 'NIVEL_TERRITORIAL_COD',
    'Nível Territorial': 'NIVEL_TERRITORIAL',
    'Unidade de Medida (Código)': 'UNIDADE_MEDIDA_COD',
    'Unidade de Medida': 'UNIDADE_MEDIDA',
    'Região Metropolitana até 2020 (Código)': 'REGIAO_METRO_COD',
    'Região Metropolitana até 2020': 'REGIAO_METRO',
    'Geral, grupo, subgrupo, item e subitem (Código)': 'CATEGORIA_COD',
    'Geral, grupo, subgrupo, item e subitem': 'CATEGORIA',
    'Mês (Código)': 'MES_COD',
    'Mês': 'MES',
    'IPCA - Variação mensal': 'IPCA_VAR_MENSAL',
    'IPCA - Peso mensal': 'IPCA_PESO_MENSAL',
    'IPCA - Variação acumulada em 12 meses': 'IPCA_VAR_12M',
    'IPCA - Variação acumulada no ano': 'IPCA_VAR_YTD'
}, inplace = True)
# ------------------------------ #


# =========== BASES BRUTA e REFINADA =========== #
df_consolidado['CATEGORIA_TIPO'] = classifica_categoria_tipo(deriva_codigo(df_consolidado['CATEGORIA']))
df_consolidado.to_csv(PATH_DADOS_REFINADOS / 'IPCA_CONSOLIDADO_BRUTO.csv', sep=';', index=False, encoding='utf-8')
df_limpo = df_consolidado[df_consolidado["NIVEL_TERRITORIAL_COD"] == 7][['CATEGORIA_COD', 'CATEGORIA', 'MES_COD', 'MES', 'IPCA_VAR_MENSAL', 'IPCA_PESO_MENSAL', 'IPCA_VAR_12M', 'IPCA_VAR_YTD']].copy()

df_limpo[['CODIGO', 'NOME_ATIVO_BRUTO']] = df_limpo['CATEGORIA'].str.split('.', n=1, expand=True)
df_limpo['CODIGO'] = df_limpo['CODIGO'].str.strip()
df_limpo['NOME_ATIVO_BRUTO'] = df_limpo['NOME_ATIVO_BRUTO'].str.strip()

# 'Índice geral' não tem '.' no CATEGORIA, então o split joga o nome inteiro em CODIGO.
sem_codigo = df_limpo['NOME_ATIVO_BRUTO'].isna()
df_limpo.loc[sem_codigo, 'NOME_ATIVO_BRUTO'] = df_limpo.loc[sem_codigo, 'CODIGO']
df_limpo.loc[sem_codigo, 'CODIGO'] = '0'

df_limpo['CATEGORIA_TIPO'] = classifica_categoria_tipo(df_limpo['CODIGO'])

# Grupo do IPCA (1º dígito do CODIGO) por extenso, na nomenclatura oficial do IBGE.
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
df_limpo['GRUPO'] = np.where(
    df_limpo['CODIGO'] == '0', 'Índice geral', df_limpo['CODIGO'].str[0].map(GRUPO_NOMES)
)
# ------------------------------ #



# ============ CHECAGEM DE INCONSISTÊNCIAS DOS NOMES BRUTOS ============ #
combinacoes = df_limpo[['CODIGO', 'NOME_ATIVO_BRUTO']].drop_duplicates()
inconsistencias = combinacoes[combinacoes.duplicated(subset='CODIGO', keep=False)].sort_values('CODIGO')

if not inconsistencias.empty:
    print(f'>>> ⚠️ Inconsistências de escrita encontradas para {inconsistencias["CODIGO"].nunique()} código(s):')
    print(inconsistencias.to_string(index=False))
else:
    print('>>> ✅ Nenhuma inconsistência de escrita encontrada entre CODIGO e NOME_ATIVO_BRUTO.')
# ------------------------------ #


# Correção manual das inconsistências de escrita identificadas em NOME_ATIVO_BRUTO.
# Códigos ausentes daqui não tinham inconsistência e mantêm o nome original.
MAPA_CORRECAO_NOME_ATIVO = {
    '1101053': 'Feijão - macassar (fradinho)',
    '1101073': 'Feijão - carioca (rajado)',
    '1101079': 'Milho (em grão)',
    '1102': 'Farinhas, féculas e massas',
    '1103046': 'Mandioquinha (batata-baroa)',
    '1104018': 'Balas, chicletes, etc.',
    '1104023': 'Chocolate em barra e bombom',
    '1104024': 'Bombons',
    '1104028': 'Gelatina de frutas em pó',
    '1104032': 'Sorvetes',
    '1104052': 'Chocolate e achocolatado em pó',
    '1104060': 'Doce de frutas em pasta',
    '1106005': "Banana-d'água",
    '1106006': 'Banana-maçã',
    '1106008': 'Banana-prata',
    '1106011': 'Laranja-da-baía',
    '1106012': 'Laranja lima',
    '1106013': 'Laranja seleta',
    '1106039': 'Laranja pera',
    '1107': 'Carnes frescas e vísceras',
    '1107008': 'Vísceras de boi',
    '1107084': 'Contrafilé',
    '1107085': 'Filé-mignon',
    '1107087': 'Chã-de-dentro',
    '1107091': 'Lagarto comum',
    '1108': 'Pescados',
    '1108002': 'Peixe anchova',
    '1108003': 'Peixe badejo',
    '1108004': 'Peixe corvina',
    '1108005': 'Peixe cavalinha',
    '1108009': 'Peixe pescadinha',
    '1108012': 'Peixe sardinha',
    '1108015': 'Peixe vermelho',
    '1108019': 'Peixe cavala',
    '1108032': 'Peixe serra',
    '1108033': 'Peixe pargo',
    '1108038': 'Peixe pescada',
    '1108044': 'Peixe cioba',
    '1108053': 'Peixe piramutaba',
    '1108057': 'Peixe surubim',
    '1108076': 'Peixe acará',
    '1108088': 'Peixe dourada',
    '1108092': 'Peixe - filhote',
    '1109007': 'Salsicha e salsichão',
    '1109010': 'Mortadela, salame, salaminho',
    '1109012': 'Salame e salaminho',
    '1109056': 'Carne-seca e de sol',
    '1109058': 'Carne de porco salgada e defumada',
    '1109088': 'Carne de hambúrguer',
    '1110009': 'Frango inteiro',
    '1111': 'Leites e derivados',
    '1111004': 'Leite pasteurizado',
    '1111019': 'Iogurte e bebidas lácteas',
    '1111021': 'Requeijão',
    '1111024': 'Queijo prato e muzzarela',
    '1112003': 'Biscoitos',
    '1113040': 'Margarina vegetal',
    '1114001': 'Suco de frutas',
    '1114004': 'Polpa de açaí',
    '1114029': 'Chá',
    '1114083': 'Refrigerante e água mineral',
    '1115006': 'Ervilha em conserva',
    '1115008': 'Feijoada em conserva',
    '1115013': 'Alimento infantil',
    '1115039': 'Sardinha em conserva',
    '1115050': 'Salsicha em conserva',
    '1115051': 'Carne em conserva',
    '1115056': 'Sopas desidratadas',
    '1115058': 'Milho-verde em conserva',
    '1115075': 'Atum em conserva',
    '1116005': 'Massa de tomate',
    '1116013': 'Sal refinado',
    '1116026': 'Fermento em pó',
    '1116048': 'Caldo concentrado',
    '1116062': 'Pimenta-do-reino',
    '1201007': 'Refrigerante e água mineral',
    '2101': 'Habitação (Aluguel e Taxas)',
    '2103012': 'Material de vidro',
    '2103014': 'Tinta para casa',
    '2103032': 'Revestimento de piso e parede',
    '2104002': 'Vassoura, rodo, etc',
    '2104009': 'Sabão (pó e barra)',
    '2104013': 'Inseticida e raticida',
    '2104014': 'Cera e lustra-móveis',
    '2104016': 'Esponja e bombril',
    '2104020': 'Limpador multiuso',
    '2104032': 'Amaciante, alvejante, etc',
    '22': 'Combustíveis e energia',
    '2201': 'Combustíveis (domésticos)',
    '2201004': 'Gás de botijão',
    '2202': 'Energia elétrica residencial',
    '2202003': 'Energia elétrica residencial',
    '1201': 'Alimentação fora do domicílio',

    # --- Grupo 3: Artigos de residência ---
    '3101002': 'Móveis para sala',
    '3101003': 'Móveis para quarto',
    '3101015': 'Móveis para copa e cozinha',
    '3102005': 'Tapetes',
    '3102006': 'Cortinas',
    '3102007': 'Utensílios de copa e cozinha de metal',
    '3102009': 'Utensílios de copa e cozinha de vidro e louça',
    '3102010': 'Utensílios de plástico',
    '3102012': 'Mamadeira, garrafa térmica',
    '3103001': 'Roupas de cama',
    '3103002': 'Roupas de mesa',
    '3103003': 'Roupas de banho',
    '32': 'Aparelhos eletroeletrônicos',
    '3201002': 'Ar-condicionado',
    '3201006': 'Máquina de lavar e secar roupa',
    '3201013': 'Ventilador e exaustor',
    '3201027': 'Lâmpadas',
    '3202': 'TV, som e informática',
    # Mesmo CODIGO, produto diferente: bases antigas registram "Vídeo-cassete",
    # bases recentes "Aparelho de DVD" (reclassificação do IBGE, não erro de escrita).
    # Mantido o nome mais recente.
    '3202005': 'Aparelho de DVD',
    '3202008': 'Videogame (console)',
    '3202028': 'Computador pessoal',
    '3301002': 'Conserto de refrigerador e freezer',
    '3301015': 'Conserto de máquina de lavar/secar roupa',

    # --- Grupo 4: Vestuário ---
    '4101': 'Roupa masculina',
    '4101002': 'Calça comprida masculina',
    '4101005': 'Agasalho masculino',
    '4101006': 'Bermuda e short masculino',
    '4101009': 'Camisa masculina',
    '4101010': 'Camiseta masculina',
    '4102': 'Roupa feminina',
    '4102002': 'Calça comprida feminina',
    '4102003': 'Agasalho feminino',
    '4102008': 'Blusa',
    '4102009': 'Meia feminina',
    '4102011': 'Roupa de dormir feminina',
    '4102012': 'Roupa de banho feminina',
    '4102013': 'Bermuda e short feminino',
    '4103': 'Roupa infantil',
    '4103001': 'Uniforme escolar',
    '4103002': 'Calça comprida infantil',
    '4103005': 'Agasalho infantil',
    '4103007': 'Vestido infantil',
    '4103008': 'Bermuda e short infantil',
    '4103011': 'Camisa infantil',
    '4103012': 'Camiseta infantil',
    '4103031': 'Conjunto infantil',
    '4201002': 'Sapato masculino',
    '4201003': 'Sapato feminino',
    '4201004': 'Sapato infantil',
    '4201007': 'Sandália / chinelo feminino',
    '4201015': 'Bolsa e carteira feminina',
    '4201029': 'Bolsa e carteira masculina',
    '4201063': 'Tênis de homem ou mulher',
    '43': 'Joias, relógios e bijuterias',
    '4301': 'Joias, relógios e bijuterias',
    '4301002': 'Joias',
    '4401001': 'Tecidos',

    # --- Grupo 5: Transportes ---
    '5': 'Transportes',
    '51': 'Transportes',
    '5101006': 'Ônibus intermunicipal',
    '5101010': 'Passagem aérea',
    '5101022': 'Transporte hidroviário',
    '5102001': 'Automóvel novo',
    '5102005': 'Seguro voluntário de veículo',
    '5102007': 'Óleo lubrificante',
    '5102010': 'Pneu e câmara-de-ar',
    '5102011': 'Conserto de automóvel',
    '5102020': 'Automóvel usado',
    '5102053': 'Motocicleta',
    '5104': 'Combustíveis (veículos)',
    '5104002': 'Etanol',

    # --- Grupo 6: Saúde e cuidados pessoais ---
    '61': 'Produtos farmacêuticos e óticos',
    '6101001': 'Anti-infeccioso e antibiótico',
    '6101002': 'Analgésico e antitérmico',
    '6101004': 'Antigripal e antitussígeno',
    '6101005': 'Colagogos e hepatoprotetores',
    '6101006': 'Antimicótico e parasiticida',
    '6101007': 'Antialérgico e broncodilatador',
    '6101009': 'Gastroprotetor',
    '6101010': 'Vitamina e fortificante',
    '6101011': 'Anticoncepcional e hormônio',
    '6101013': 'Psicotrópico e anorexígeno',
    '6101014': 'Hipotensor e hipocolesterolêmico',
    '6102': 'Óculos e lentes',
    '6102001': 'Lente de grau',
    '62': 'Serviços de saúde',
    '6201': 'Serviços médicos e dentários',
    '6201005': 'Aparelho ortodôntico',
    '6201008': 'Tratamento psicológico e fisioterapêutico',
    '6202': 'Serviços laboratoriais e hospitalares',
    '6202004': 'Hospitalização e cirurgia',
    '6202006': 'Exame de imagem',
    '6301001': 'Produto para cabelo',
    '6301004': 'Produto para barba',
    '6301006': 'Produto para pele',
    '6301007': 'Produto para higiene bucal',
    '6301014': 'Desodorante e perfume',
    '6301015': 'Absorvente higiênico',
    '6301020': 'Artigos de maquiagem',

    # --- Grupo 7: Despesas pessoais ---
    '71': 'Serviços pessoais',
    '7101001': 'Alfaiate e costureira',
    '7101004': 'Tinturaria e lavanderia',
    '7101005': 'Manicure e pedicure',
    '7101009': 'Cabeleireiro e manicure',
    '7101010': 'Empregado doméstico',
    '72': 'Recreação, fumo e fotografia',
    '7201003': 'Ingresso para jogo',
    '7201006': 'Clubes',
    '7201008': 'Disco e fita',
    '7201018': 'Compra e tratamento de animais',
    '7201020': 'Alimento para animais',
    '7201023': 'Brinquedos',
    # Mesmo CODIGO, produto diferente: bases antigas = locação de fita VHS,
    # bases recentes = locação de DVD (reclassificação do IBGE). Nome mais recente mantido.
    '7201052': 'Locação de DVD',
    '7201054': 'Boate, danceteria e discoteca',
    '7201063': 'Jogos de azar',
    '7201090': 'Hospedagem',
    '7201095': 'Pacote turístico',
    '7202041': 'Cigarros',

    # --- Grupo 8: Educação ---
    '8101': 'Cursos regulares',
    '8101002': 'Educação infantil',
    '8101003': 'Ensino fundamental',
    '8101004': 'Ensino médio',
    '8101005': 'Ensino superior',
    '8101008': 'Educação de jovens e adultos',
    '8102004': 'Revista não técnica',
    '8102005': 'Livro não didático',
    '8104006': 'Atividades físicas',

    # --- Grupo 9: Comunicação ---
    '9101002': 'Plano de telefonia fixa',
    '9101008': 'Plano de telefonia móvel',
    '9101010': 'TV por assinatura',
}
df_limpo['NOME_ATIVO'] = df_limpo['CODIGO'].map(MAPA_CORRECAO_NOME_ATIVO).fillna(df_limpo['NOME_ATIVO_BRUTO'])

print(">>> ✅ Limpeza dos nomes das séries concluída. Utilize a coluna NOME_ATIVO como referência.")

df_limpo['ANO_COD'] = df_limpo['MES_COD'] // 100

# ============== ANÁLISE DE DADOS MISSING =============== #
# - Levantamento de quais séries não tem nenhum IPCA, quais estão completas e quais são parciais

colunas_ipca = ['IPCA_VAR_MENSAL', 'IPCA_PESO_MENSAL', 'IPCA_VAR_12M', 'IPCA_VAR_YTD']
df_limpo[colunas_ipca] = df_limpo[colunas_ipca].replace(['-', '...'], np.nan).apply(pd.to_numeric)

# COMPLETUDE_INFO: por CODIGO, se IPCA_VAR_MENSAL está ausente em TODOS os meses (TOTAL),
# em ALGUNS meses (PARCIAL) ou em NENHUM (COMPLETA).
resumo_completude = df_limpo.groupby('CODIGO')['IPCA_VAR_MENSAL'].agg(
    n_total='size',
    n_ausente=lambda s: s.isna().sum()
)
resumo_completude['COMPLETUDE_INFO'] = np.select(
    [resumo_completude['n_ausente'] == 0, resumo_completude['n_ausente'] == resumo_completude['n_total']],
    ['COMPLETA', 'NENHUMA'],
    default='PARCIAL'
)
df_limpo = df_limpo.merge(resumo_completude['COMPLETUDE_INFO'], on='CODIGO', how='left')
# -------------------------------------------------------- #


# Códigos cujo IPCA_VAR_MENSAL é idêntico, mês a mês, ao do seu pai imediato (o IBGE não
# desagregou o nível inferior) - mantém só o pai, para não duplicar a mesma série duas vezes.
CODIGOS_REDUNDANTES_COM_PAI = [
    '2202003',  # == 2202
    '1201',     # == 12
    '3301',     # == 33
    '4201',     # == 42
    '4301',     # == 43
    '4401',     # == 44
    '5201',     # == 52
    '5201002',  # == 5201
    '6301',     # == 63
    '6102012',  # == 6102
    '6203001',  # == 6203
    '63',       # == 6
    '71',       # == 7
    '81',       # == 8
    '91',       # == 9
    '9101',     # == 91
]
df_limpo = df_limpo[~df_limpo['CODIGO'].isin(CODIGOS_REDUNDANTES_COM_PAI)]


# ========== CÁLCULOS DE VARIACAO ACUMULADA E NUMERO ÍNDICE ============ #
def var_acumulada(janela_temporal):
    return (np.prod((1 + janela_temporal/100)) - 1)*100

def num_ind_ipca(df, ponto_tempo = 200501, base_value = 100):
    # Número índice acumulado por CODIGO a partir de ponto_tempo (mês-base = base_value).
    # Meses sem IPCA_VAR_MENSAL são tratados como variação 0% para o índice não travar em NaN.
    col_name = f"CALC_NUM_IND_IPCA_{str(ponto_tempo)[:4]}"
    df = df.copy()
    df[col_name] = np.nan

    sub = (
        df[df['MES_COD'] >= ponto_tempo]
        .sort_values(by = ["CODIGO", "MES_COD"])
        .copy()
    )
    variacao = sub["IPCA_VAR_MENSAL"].fillna(0)
    # o mês-base não compõe seu próprio índice — por isso o fator dele é 1
    fator = np.where(sub["MES_COD"] == ponto_tempo, 1.0, 1 + variacao / 100)
    sub["fator"] = fator
    sub[col_name] = sub.groupby("CODIGO")["fator"].transform(lambda f: base_value * np.cumprod(f))

    df.loc[sub.index, col_name] = sub[col_name]
    return df


df_limpo["CALC_IPCA_VAR_12M"] = df_limpo.groupby(by = "CODIGO", as_index = False)["IPCA_VAR_MENSAL"].rolling(window = 12, min_periods = 1).apply(var_acumulada, raw = True)["IPCA_VAR_MENSAL"]
df_limpo["CALC_IPCA_VAR_ANO"] = df_limpo.groupby(by = ["CODIGO", "ANO_COD"], as_index = False)["IPCA_VAR_MENSAL"].rolling(window = 12, min_periods = 1).apply(var_acumulada, raw = True)["IPCA_VAR_MENSAL"]

PONTOS_NUM_INDICE = [200001, 200501, 201001]
for ponto in PONTOS_NUM_INDICE:
    df_limpo = num_ind_ipca(df_limpo, ponto_tempo = ponto)
#--------------------------------------------------------#

colunas_finais = ['CATEGORIA_COD', 'CATEGORIA', 'CODIGO',
                  'NOME_ATIVO_BRUTO', 'NOME_ATIVO', 'GRUPO', 'CATEGORIA_TIPO',
                  'COMPLETUDE_INFO', 'ANO_COD', 'MES_COD', 'MES'] + ['IPCA_VAR_MENSAL', 'IPCA_PESO_MENSAL', 'CALC_IPCA_VAR_12M', 'CALC_IPCA_VAR_ANO'] + [f"CALC_NUM_IND_IPCA_{str(p)[:4]}" for p in PONTOS_NUM_INDICE]

df_limpo = df_limpo[colunas_finais].sort_values(by = ['CODIGO', 'MES_COD']) # Ordenamos da seguinte forma: vemos todos o periodo completo de uma série por vez.

df_limpo.to_csv(PATH_DADOS_REFINADOS / 'IPCA_CONSOLIDADO.csv', sep=';', index=False, encoding='utf-8')


# =========== LEVANTAMENTO DE LACUNAS EM IPCA_VAR_MENSAL =========== #
# Das que são parciais ou 
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

df_lacunas = df_limpo.copy()
df_lacunas['DATA'] = pd.to_datetime(df_lacunas['MES_COD'], format='%Y%m')

linhas_lacunas = []
for codigo, grupo in df_lacunas.groupby('CODIGO'):
    datas_ausentes = grupo.loc[grupo['IPCA_VAR_MENSAL'].isna(), 'DATA'].tolist()
    if not datas_ausentes:
        continue
    linhas_lacunas.append({
        'CODIGO': codigo,
        'NOME_ATIVO': grupo['NOME_ATIVO'].iloc[0],
        'N_MESES_TOTAL': len(grupo),
        'N_MESES_AUSENTES': len(datas_ausentes),
        'INTERVALOS_AUSENTES': formata_intervalos_ausentes(datas_ausentes),
    })

df_series_com_lacunas = pd.DataFrame(linhas_lacunas).sort_values('N_MESES_AUSENTES', ascending=False)
df_series_com_lacunas.to_csv(PATH_DADOS_REFINADOS / 'IPCA_AUSENTES_VAR_MENSAL.csv', sep=';', index=False, encoding='utf-8')

n_total_ausentes = (df_series_com_lacunas['N_MESES_TOTAL'] == df_series_com_lacunas['N_MESES_AUSENTES']).sum()
print(f'>>> ⚠️ {len(df_series_com_lacunas)} de {df_limpo["CODIGO"].nunique()} séries têm ao menos 1 mês sem IPCA_VAR_MENSAL '
      f'({n_total_ausentes} delas nunca têm o dado). Detalhe em IPCA_LACUNAS_VAR_MENSAL.csv.')
# ------------------------------------------------------------------- #

print("\n>>> 🏁 Bases bruta e refinada consolidadas em .CSV com sucesso. Encerrando operação. 🏁")