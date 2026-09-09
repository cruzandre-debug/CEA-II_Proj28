import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from statsmodels.tsa.seasonal import STL
from pathlib import Path

# ── Configuração da página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="IPCA & INPC | CEA-IME USP",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Constantes ────────────────────────────────────────────────────────────────
IME_BLUE = "#003D7A"
LOGO_URL = "https://www.ime.usp.br/cea/resources/logo-ime-horizontal.png"
PALETTE  = [
    "#1f77b4", "#e6550d", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#636363", "#bcbd22", "#17becf",
    "#6baed6", "#fd8d3c", "#74c476", "#fb6a4a", "#9e9ac8",
    "#fdae6b", "#41b6c4", "#a1d99b", "#fc9272", "#c6dbef",
]
# Paleta Okabe-Ito — segura para os três tipos mais comuns de daltonismo
PALETTE_CB = [
    "#E69F00", "#56B4E9", "#009E73", "#D55E00",
    "#0072B2", "#CC79A7", "#F0E442", "#000000",
]
# Os 9 grupos do IPCA, na ordem oficial do IBGE. A coluna GRUPO já vem pronta do CSV
# (gerada em consolida_bases.py), então usamos o próprio nome do grupo como chave.
GRUPO_ORDER = [
    "Alimentação e bebidas", "Habitação", "Artigos de residência", "Vestuário",
    "Transportes", "Saúde e cuidados pessoais", "Despesas pessoais", "Educação",
    "Comunicação",
]
GRUPO_GERAL = "Índice geral"
GRUPO_EMOJI = {
    "Alimentação e bebidas": "🍎", "Habitação": "🏠", "Artigos de residência": "🛋️",
    "Vestuário": "👕", "Transportes": "🚗", "Saúde e cuidados pessoais": "💊",
    "Despesas pessoais": "💼", "Educação": "📚", "Comunicação": "📱",
    GRUPO_GERAL: "📊",
}
# Fonte = de qual índice/abrangência a série vem. IPCA só cobre RM São Paulo; o INPC traz
# Brasil e RM São Paulo lado a lado — ver ESTRUTURA_PROJETO.md.
FONTE_ORDER = ["IPCA (SP)", "INPC (SP)", "INPC (Brasil)"]
FONTE_DASH = {"IPCA (SP)": "solid", "INPC (SP)": "dash", "INPC (Brasil)": "dot"}

# ── Dados ─────────────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).resolve().parent.parent / "1.DADOS" / "1.2.DADOS_REFINADOS"

# Nomes das colunas de variável divergem entre os dois CSVs (prefixo IPCA_/INPC_) — aqui
# são renomeadas para um padrão comum antes de empilhar as duas fontes num único dataframe.
_COLUNAS_VARIAVEL = ["VAR_MENSAL", "PESO_MENSAL", "CALC_VAR_12M", "CALC_VAR_ANO",
                     "CALC_NUM_IND_2000", "CALC_NUM_IND_2005", "CALC_NUM_IND_2010"]
_COLUNAS_COMUNS = ["CODIGO", "NOME_ATIVO", "GRUPO", "CATEGORIA_TIPO", "COMPLETUDE_INFO",
                   "ANO_COD", "MES_COD", "MES", "FONTE"] + _COLUNAS_VARIAVEL

@st.cache_data
def load_data() -> pd.DataFrame:
    ipca = pd.read_csv(DATA_DIR / "IPCA_CONSOLIDADO.csv", sep=";", low_memory=False)
    ipca = ipca.rename(columns={
        "IPCA_VAR_MENSAL": "VAR_MENSAL", "IPCA_PESO_MENSAL": "PESO_MENSAL",
        "CALC_IPCA_VAR_12M": "CALC_VAR_12M", "CALC_IPCA_VAR_ANO": "CALC_VAR_ANO",
        "CALC_NUM_IND_IPCA_2000": "CALC_NUM_IND_2000",
        "CALC_NUM_IND_IPCA_2005": "CALC_NUM_IND_2005",
        "CALC_NUM_IND_IPCA_2010": "CALC_NUM_IND_2010",
    })
    ipca["FONTE"] = "IPCA (SP)"

    inpc = pd.read_csv(DATA_DIR / "INPC_CONSOLIDADO.csv", sep=";", low_memory=False)
    inpc = inpc.rename(columns={
        "INPC_VAR_MENSAL": "VAR_MENSAL", "INPC_PESO_MENSAL": "PESO_MENSAL",
        "CALC_INPC_VAR_12M": "CALC_VAR_12M", "CALC_INPC_VAR_ANO": "CALC_VAR_ANO",
        "CALC_NUM_IND_INPC_2000": "CALC_NUM_IND_2000",
        "CALC_NUM_IND_INPC_2005": "CALC_NUM_IND_2005",
        "CALC_NUM_IND_INPC_2010": "CALC_NUM_IND_2010",
    })
    inpc["FONTE"] = inpc["ABRANGENCIA"].map({"São Paulo (RM)": "INPC (SP)", "Brasil": "INPC (Brasil)"})

    df = pd.concat([ipca[_COLUNAS_COMUNS], inpc[_COLUNAS_COMUNS]], ignore_index=True)
    df["DATA"] = pd.to_datetime(df["MES_COD"], format="%Y%m")
    for col in _COLUNAS_VARIAVEL:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

df = load_data()

TIPO_ORDER = ["GERAL", "GRUPO", "SUBGRUPO", "ITEM", "SUBITEM"]
DEFAULT_ON = {"GERAL", "GRUPO"}

# Catálogo único de séries por CODIGO, mesclando IPCA e INPC. Nem todo CODIGO existe nas 2
# bases (672 em comum, ~50-60 exclusivos de cada uma) — quando o nome diverge entre elas
# (grafia diferente, ~102 casos), prevalece o NOME_ATIVO do IPCA (curado manualmente) por
# vir primeiro no concat abaixo; séries só do INPC usam o nome já corrigido automaticamente
# de lá (ver consolida_bases_inpc.py).
series_info = (
    pd.concat([
        df.loc[df["FONTE"] == "IPCA (SP)", ["CODIGO", "NOME_ATIVO", "GRUPO", "CATEGORIA_TIPO"]],
        df.loc[df["FONTE"] != "IPCA (SP)", ["CODIGO", "NOME_ATIVO", "GRUPO", "CATEGORIA_TIPO"]],
    ])
    .drop_duplicates(subset="CODIGO", keep="first")
    .sort_values(["CATEGORIA_TIPO", "NOME_ATIVO"])
    .reset_index(drop=True)
)
series_by_type = {
    tipo: series_info[series_info["CATEGORIA_TIPO"] == tipo]
    for tipo in TIPO_ORDER
}
GRUPO_BY_CODIGO = series_info.set_index("CODIGO")["GRUPO"].to_dict()

# ── Inicialização do session_state ────────────────────────────────────────────
if "dark_mode" not in st.session_state:
    st.session_state["dark_mode"] = False

for tipo in TIPO_ORDER:
    if f"all_{tipo}" not in st.session_state:
        st.session_state[f"all_{tipo}"] = tipo in DEFAULT_ON
    for cod in series_by_type[tipo]["CODIGO"]:
        if f"s_{cod}" not in st.session_state:
            st.session_state[f"s_{cod}"] = tipo in DEFAULT_ON

# ── Tema dinâmico ─────────────────────────────────────────────────────────────
dark = st.session_state["dark_mode"]

if dark:
    main_bg       = "#0E1117"
    title_color   = "#6EB0E8"
    sub_color     = "#AAAAAA"
    plot_bg       = "#1A1A2E"
    paper_bg      = "#0E1117"
    grid_color    = "#2A2A2A"
    zero_color    = "#444444"
    font_color    = "#EEEEEE"
    legend_bg     = "rgba(14,17,23,0.88)"
    legend_border  = "#444444"
    logo_filter   = "brightness(0) invert(1)"
    text_main     = "#EEEEEE"
    toggle_bg     = "rgba(255,255,255,0.08)"
    toggle_border = "rgba(255,255,255,0.25)"
else:
    main_bg       = "#FAF8F3"
    title_color   = IME_BLUE
    sub_color     = "#555555"
    plot_bg       = "#FAF8F3"
    paper_bg      = "#FAF8F3"
    grid_color    = "#E0DDD6"
    zero_color    = "#BBBBBB"
    font_color    = "#222222"
    legend_bg     = "rgba(250,248,243,0.92)"
    legend_border  = "#CCCCCC"
    logo_filter   = "none"
    text_main     = "#222222"
    toggle_bg     = "rgba(0,61,122,0.13)"
    toggle_border = "rgba(0,61,122,0.50)"

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  /* Fundo e cor de texto da área principal */
  .stApp,
  [data-testid="stAppViewContainer"],
  [data-testid="stMain"],
  section[data-testid="stMain"] > div,
  .block-container {{
      background-color: {main_bg} !important;
  }}
  /* Textos da área principal */
  [data-testid="stMain"] p,
  [data-testid="stMain"] label,
  [data-testid="stMain"] span:not([data-baseweb]),
  [data-testid="stMain"] .stMarkdown,
  [data-testid="stMain"] .stCaption,
  [data-testid="stMain"] li {{
      color: {text_main} !important;
  }}

  /* Sidebar azul IME */
  section[data-testid="stSidebar"] > div:first-child {{
      background-color: {IME_BLUE} !important;
  }}
  section[data-testid="stSidebar"] label,
  section[data-testid="stSidebar"] p,
  section[data-testid="stSidebar"] .stMarkdown p,
  section[data-testid="stSidebar"] details summary p,
  section[data-testid="stSidebar"] .stSelectbox label,
  section[data-testid="stSidebar"] .stSlider label {{
      color: #FFFFFF !important;
  }}
  section[data-testid="stSidebar"] .stExpander details {{
      border-color: rgba(255,255,255,0.25) !important;
      background-color: rgba(255,255,255,0.06);
      border-radius: 6px;
  }}
  section[data-testid="stSidebar"] .stTextInput input {{
      background-color: rgba(255,255,255,0.1);
      color: white;
      border-color: rgba(255,255,255,0.3);
  }}
  section[data-testid="stSidebar"] .stTextInput input::placeholder {{
      color: rgba(255,255,255,0.45);
  }}
  section[data-testid="stSidebar"] .stCheckbox span {{
      color: #FFFFFF !important;
  }}
  /* Toggles da área principal — visíveis em ambos os estados */
  [data-testid="stMain"] [data-testid="stToggle"] {{
      background-color: {toggle_bg};
      border: 1px solid {toggle_border};
      border-radius: 8px;
      padding: 3px 10px 3px 6px;
  }}
  .block-container {{ padding-top: 3.5rem; }}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f'<img src="{LOGO_URL}" '
        'style="width:100%; filter:brightness(0) invert(1); padding:2px 0 4px 0">',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="color:rgba(255,255,255,0.55); font-size:0.72rem; '
        'margin:0 0 10px 1px; letter-spacing:.04em">CENTRO DE ESTATÍSTICA APLICADA</p>',
        unsafe_allow_html=True,
    )
    st.divider()

    st.toggle("🌙 Modo escuro", key="dark_mode")
    st.divider()

    st.markdown("**Variável**")
    VAR_OPTIONS = {
        "Variação mensal (%)":                    "VAR_MENSAL",
        "Variação acum. 12 meses (%)":             "CALC_VAR_12M",
        "Variação acumulada no ano (%)":           "CALC_VAR_ANO",
        "Número índice (base 100 = jan/2000)":     "CALC_NUM_IND_2000",
        "Número índice (base 100 = jan/2005)":     "CALC_NUM_IND_2005",
        "Número índice (base 100 = jan/2010)":     "CALC_NUM_IND_2010",
    }
    var_label = st.selectbox("Variável", list(VAR_OPTIONS.keys()), label_visibility="collapsed")
    var_col   = VAR_OPTIONS[var_label]
    is_indice = var_col.startswith("CALC_NUM_IND")
    unidade   = "" if is_indice else "%"

    st.markdown("**Janela temporal**")
    min_year = int(df["DATA"].dt.year.min())
    max_year = int(df["DATA"].dt.year.max())
    ano_ini, ano_fim = st.slider(
        "Ano", min_year, max_year, (2000, max_year),
        label_visibility="collapsed",
    )

    st.divider()
    st.markdown("**Fontes**")
    fontes_ativas = st.multiselect(
        "Fontes", FONTE_ORDER, default=FONTE_ORDER, label_visibility="collapsed",
        help="IPCA cobre só a RM São Paulo. O INPC traz Brasil e RM São Paulo — útil para "
             "comparar o custo de vida de famílias de baixa renda (INPC) contra a média "
             "geral (IPCA) na mesma região.",
    )

    st.divider()
    st.markdown("**Séries**")

    GRUPO_OPCOES = {"Todas": None}
    for _g in GRUPO_ORDER:
        GRUPO_OPCOES[f"{GRUPO_EMOJI[_g]} {_g}"] = _g
    grupo_label = st.segmented_control(
        "Grupo", list(GRUPO_OPCOES.keys()),
        default="Todas", key="grupo_filtro", label_visibility="collapsed",
    )
    grupo_sel = GRUPO_OPCOES.get(grupo_label)

    def _make_select_all_cb(tipo: str, rows: pd.DataFrame):
        def cb():
            val = st.session_state[f"all_{tipo}"]
            for cod in rows["CODIGO"].tolist():
                st.session_state[f"s_{cod}"] = val
        return cb

    for tipo in TIPO_ORDER:
        rows_tipo = series_by_type[tipo]
        rows = rows_tipo if grupo_sel is None else rows_tipo[rows_tipo["GRUPO"] == grupo_sel]
        n    = len(rows)
        with st.expander(f"{tipo}  ({n})", expanded=(tipo in DEFAULT_ON)):
            st.checkbox(
                "Selecionar todas",
                key=f"all_{tipo}",
                on_change=_make_select_all_cb(tipo, rows),
            )
            filtro = ""
            if n > 15:
                filtro = st.text_input(
                    "buscar", key=f"f_{tipo}",
                    placeholder="🔍 Buscar série…",
                    label_visibility="collapsed",
                ).strip().lower()
            for _, row in rows.iterrows():
                if filtro and filtro not in row["NOME_ATIVO"].lower():
                    continue
                st.checkbox(row["NOME_ATIVO"], key=f"s_{row['CODIGO']}")

# ── Séries selecionadas ───────────────────────────────────────────────────────
selected = [
    cod for cod in series_info["CODIGO"]
    if st.session_state.get(f"s_{cod}", False)
]

# ── Cabeçalho principal ───────────────────────────────────────────────────────
fontes_label = " · ".join(fontes_ativas) if fontes_ativas else "Nenhuma fonte selecionada"

st.markdown(
    f"""
    <div style="display:flex; align-items:center; justify-content:space-between;
                margin-bottom:0.6rem; gap:1rem">
        <div>
            <p style="font-size:1.7rem; font-weight:700; color:{title_color};
                      margin:0; line-height:1.2">
                Análise Descritiva — IPCA &amp; INPC
            </p>
            <p style="color:{sub_color}; font-size:0.88rem; margin:3px 0 0 0">
                {fontes_label} &nbsp;·&nbsp; IBGE &nbsp;·&nbsp; {ano_ini}–{ano_fim}
            </p>
        </div>
        <img src="{LOGO_URL}"
             style="height:56px; max-width:240px; object-fit:contain;
                    flex-shrink:0; filter:{logo_filter}">
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Controles de visualização ─────────────────────────────────────────────────
col_a, col_b, col_c, col_d, col_e, col_f, col_g, _ = st.columns(
    [1.5, 1.8, 2.0, 2.0, 2.0, 2.0, 2.2, 0.6]
)
with col_a:
    show_series   = st.toggle("📉 Série",        value=True)
with col_b:
    show_trend    = st.toggle("📈 Tendência",    value=False)
with col_c:
    show_seasonal = st.toggle("🌊 Sazonalidade", value=False)
with col_d:
    cb_friendly   = st.toggle("👁 Daltônico",    value=False)
with col_e:
    split_view    = st.toggle("🪟 Comparar grupos", value=False)
with col_f:
    match_y_toggle = st.toggle(
        "🔗 Mesma escala Y", value=False,
        disabled=not split_view,
        help="Disponível quando 'Comparar grupos' está ativo.",
    )
with col_g:
    dash_por_fonte = st.toggle(
        "〰️ Linha por fonte", value=True, key="dash_por_fonte",
        help="Quando ativado, cada fonte (IPCA SP / INPC SP / INPC Brasil) usa um padrão "
             "de traço diferente (sólido, tracejado, pontilhado), facilitando comparar as "
             "mesmas séries entre índices/abrangências. Desative para todas usarem linha "
             "sólida.",
    )

match_y = split_view and match_y_toggle
palette = PALETTE_CB if cb_friendly else PALETTE

if not fontes_ativas:
    st.info("Selecione ao menos uma fonte no painel lateral.")
    st.stop()

if not selected:
    st.info("Selecione ao menos uma série no painel lateral.")
    st.stop()

if not show_series and not show_trend and not show_seasonal:
    st.warning("Ative ao menos um componente para visualizar o gráfico.")
    st.stop()

# ── Filtragem por janela temporal ─────────────────────────────────────────────
df_sel = df[
    df["CODIGO"].isin(selected) &
    df["FONTE"].isin(fontes_ativas) &
    (df["DATA"].dt.year >= ano_ini) &
    (df["DATA"].dt.year <= ano_fim)
].copy()

# ── Decomposição STL (cacheada por série + fonte + variável) ──────────────────
@st.cache_data(show_spinner=False)
def get_decomposition(cod: str, fonte: str, col: str):
    sub   = df[(df["CODIGO"] == cod) & (df["FONTE"] == fonte)].set_index("DATA")[col].sort_index()
    clean = sub.dropna()
    if len(clean) < 24:
        return None, None
    idx = pd.date_range(clean.index.min(), clean.index.max(), freq="MS")
    s   = clean.reindex(idx).interpolate("linear")
    try:
        res = STL(s, period=12, robust=True).fit()
        return res.trend, res.seasonal
    except Exception:
        return None, None

# ── Construção do gráfico ─────────────────────────────────────────────────────
n_rows = 1 + (1 if show_seasonal else 0)
heights = [0.62, 0.38] if show_seasonal else [1.0]

# Uma coluna por grupo efetivamente presente entre as séries selecionadas (o "Índice
# geral" não conta como grupo próprio — ele aparece replicado em todas as colunas).
if split_view:
    grupos_presentes = [
        g for g in GRUPO_ORDER
        if any(GRUPO_BY_CODIGO.get(cod) == g for cod in selected)
    ]
    if not grupos_presentes:
        grupos_presentes = [GRUPO_GERAL]
else:
    grupos_presentes = []

n_cols = len(grupos_presentes) if split_view else 1
col_by_grupo = {g: i + 1 for i, g in enumerate(grupos_presentes)}

if split_view:
    def _titulo_grupo(g):
        return f"{GRUPO_EMOJI.get(g, '')} {g}".strip()
    subtitles = [f"{var_label} — {_titulo_grupo(g)}" for g in grupos_presentes]
    if show_seasonal:
        subtitles += [f"Sazonalidade — {_titulo_grupo(g)}" for g in grupos_presentes]
    horizontal_spacing = min(0.06, 0.9 / (n_cols - 1)) if n_cols > 1 else 0.02
else:
    subtitles = [var_label] + (["Componente Sazonal"] if show_seasonal else [])
    horizontal_spacing = 0.02

fig = make_subplots(
    rows=n_rows,
    cols=n_cols,
    shared_xaxes=True,
    shared_yaxes=match_y,
    row_heights=heights,
    horizontal_spacing=horizontal_spacing,
    vertical_spacing=0.10,
    subplot_titles=subtitles,
)

# Cor dos títulos dos subplots
for ann in fig.layout.annotations:
    ann.font.color = font_color

stl_warnings = []
mostra_fonte_na_legenda = len(fontes_ativas) > 1

for i, cod in enumerate(selected):
    color = palette[i % len(palette)]
    grupo = GRUPO_BY_CODIGO.get(cod, GRUPO_GERAL)
    nome  = series_info.loc[series_info["CODIGO"] == cod, "NOME_ATIVO"].iloc[0]

    # Em qual(is) coluna(s) esta série aparece. Sem divisão por grupo: sempre a coluna 1.
    # Com divisão: cada grupo tem sua própria coluna, e o Índice geral (não pertence a
    # nenhum grupo) aparece em todas para servir de referência.
    if not split_view:
        cols_target = [1]
    elif grupo == GRUPO_GERAL:
        cols_target = list(range(1, n_cols + 1))
    else:
        cols_target = [col_by_grupo.get(grupo, 1)]

    # Qual componente aparece primeiro na legenda para esta série+fonte
    legend_anchor = (
        "series"   if show_series   else
        "trend"    if show_trend    else
        "seasonal"
    )

    for fonte in fontes_ativas:
        # Nem todo CODIGO existe nas 3 fontes (ver série unificada acima) — pula em
        # silêncio quando a combinação série+fonte não tem dado.
        sub = df_sel[(df_sel["CODIGO"] == cod) & (df_sel["FONTE"] == fonte)].sort_values("DATA")
        if sub.empty:
            continue

        dash  = FONTE_DASH.get(fonte, "solid") if dash_por_fonte else "solid"
        label = f"{nome} — {fonte}" if mostra_fonte_na_legenda else nome
        legend_key = f"{cod}|{fonte}"
        y = sub.set_index("DATA")[var_col].sort_index()

        # ── Série original ────────────────────────────────────────────────────
        if show_series:
            for c in cols_target:
                fig.add_trace(
                    go.Scatter(
                        x=y.index,
                        y=y.values,
                        name=label,
                        line=dict(color=color, width=1.8, dash=dash),
                        legendgroup=legend_key,
                        showlegend=(legend_anchor == "series" and c == cols_target[0]),
                        hovertemplate=(
                            f"<b>{label}</b><br>%{{x|%b %Y}}: %{{y:.2f}}{unidade}<extra></extra>"
                        ),
                    ),
                    row=1, col=c,
                )

        # ── Decomposição ──────────────────────────────────────────────────────
        if show_trend or show_seasonal:
            trend, seasonal = get_decomposition(cod, fonte, var_col)

            if trend is None:
                stl_warnings.append(label)
            else:
                mask = (trend.index.year >= ano_ini) & (trend.index.year <= ano_fim)

                if show_trend:
                    t = trend[mask]
                    for c in cols_target:
                        fig.add_trace(
                            go.Scatter(
                                x=t.index,
                                y=t.values,
                                name=label,
                                line=dict(color=color, width=2.8, dash=dash),
                                legendgroup=legend_key,
                                showlegend=(legend_anchor == "trend" and c == cols_target[0]),
                                hovertemplate=(
                                    f"<b>Tendência — {label}</b><br>"
                                    f"%{{x|%b %Y}}: %{{y:.2f}}{unidade}<extra></extra>"
                                ),
                            ),
                            row=1, col=c,
                        )

                if show_seasonal:
                    s = seasonal[mask]
                    for c in cols_target:
                        fig.add_trace(
                            go.Scatter(
                                x=s.index,
                                y=s.values,
                                name=label,
                                line=dict(color=color, width=1.5, dash=dash),
                                legendgroup=legend_key,
                                showlegend=(legend_anchor == "seasonal" and c == cols_target[0]),
                                hovertemplate=(
                                    f"<b>Sazonalidade — {label}</b><br>"
                                    f"%{{x|%b %Y}}: %{{y:.2f}}{unidade}<extra></extra>"
                                ),
                            ),
                            row=2, col=c,
                        )

# ── Eixos ─────────────────────────────────────────────────────────────────────
fig.update_xaxes(
    showgrid=True, gridcolor=grid_color, zeroline=False,
    tickfont=dict(color=font_color),
    title_font=dict(color=font_color),
)
fig.update_yaxes(
    showgrid=True, gridcolor=grid_color,
    zeroline=True, zerolinecolor=zero_color, zerolinewidth=1.2,
    ticksuffix=unidade,
    tickfont=dict(color=font_color),
    title_font=dict(color=font_color),
)
fig.update_yaxes(title_text=var_label, row=1, col=1)
if show_seasonal:
    fig.update_yaxes(title_text=f"Componente sazonal ({unidade or 'pts'})", row=2, col=1)
    fig.update_xaxes(title_text="Data", row=2)
else:
    fig.update_xaxes(title_text="Data", row=1)

# ── Layout geral ──────────────────────────────────────────────────────────────
fig.update_layout(
    height=530 if not show_seasonal else 750,
    plot_bgcolor=plot_bg,
    paper_bgcolor=paper_bg,
    hovermode="x unified",
    hoverlabel=dict(bgcolor=legend_bg, font_color=font_color),
    legend=dict(
        orientation="v",
        yanchor="top",
        y=1.0,
        xanchor="left",
        x=1.01,
        bgcolor=legend_bg,
        bordercolor=legend_border,
        borderwidth=1,
        font=dict(size=12, color=font_color),
        tracegroupgap=4,
        maxheight=450,
    ),
    margin=dict(t=40, l=80, r=200, b=50),
    font=dict(family="Arial, sans-serif", size=13, color=font_color),
)

st.plotly_chart(fig, use_container_width=True)

if dash_por_fonte:
    st.caption(
        "O tipo de linha (sólida, tracejada, pontilhada) varia por fonte "
        f"({', '.join(fontes_ativas)}) — mesma série, cor igual, comparável entre fontes."
    )

if stl_warnings:
    st.caption(
        "⚠️ Decomposição STL não disponível para: "
        + ", ".join(f"**{n}**" for n in stl_warnings)
        + " (série com menos de 24 meses não nulos)."
    )

# ── Tabela informativa ────────────────────────────────────────────────────────
with st.expander("ℹ️ Informações das séries selecionadas"):
    # Completude é por (CODIGO, FONTE) — uma série pode faltar numa fonte e estar
    # completa em outra, então a tabela abre uma linha por combinação existente.
    tabela_info = (
        df.loc[
            df["CODIGO"].isin(selected) & df["FONTE"].isin(fontes_ativas),
            ["CODIGO", "FONTE", "GRUPO", "CATEGORIA_TIPO", "COMPLETUDE_INFO"],
        ]
        .drop_duplicates(subset=["CODIGO", "FONTE"])
        .merge(series_info[["CODIGO", "NOME_ATIVO"]], on="CODIGO", how="left")
        .sort_values(["CATEGORIA_TIPO", "NOME_ATIVO", "FONTE"])
    )
    st.dataframe(
        tabela_info[
            ["CODIGO", "NOME_ATIVO", "FONTE", "GRUPO", "CATEGORIA_TIPO", "COMPLETUDE_INFO"]
        ].reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
    )
