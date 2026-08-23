import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from statsmodels.tsa.seasonal import STL
from pathlib import Path

# ── Configuração da página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="IPCA | CEA-IME USP",
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

# ── Dados ─────────────────────────────────────────────────────────────────────
DATA_PATH = (
    Path(__file__).resolve().parent.parent
    / "1.DADOS" / "1.2.DADOS_REFINADOS" / "IPCA_CONSOLIDADO.csv"
)

@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, sep=";", low_memory=False)
    df["DATA"] = pd.to_datetime(df["MES_COD"], format="%Y%m")
    for col in ["IPCA_VAR_MENSAL", "CALC_IPCA_VAR_12M", "CALC_IPCA_VAR_ANO", "IPCA_PESO_MENSAL"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

df = load_data()

TIPO_ORDER = ["GERAL", "GRUPO", "SUBGRUPO", "ITEM", "SUBITEM"]
DEFAULT_ON = {"GERAL", "GRUPO"}

series_info = (
    df[["CODIGO", "NOME_ATIVO", "CATEGORIA_TIPO", "COMPLETUDE_INFO"]]
    .drop_duplicates(subset="CODIGO")
    .sort_values(["CATEGORIA_TIPO", "CODIGO"])
    .reset_index(drop=True)
)
series_by_type = {
    tipo: series_info[series_info["CATEGORIA_TIPO"] == tipo]
    for tipo in TIPO_ORDER
}

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
        "Variação mensal (%)":           "IPCA_VAR_MENSAL",
        "Variação acum. 12 meses (%)":   "CALC_IPCA_VAR_12M",
        "Variação acumulada no ano (%)": "CALC_IPCA_VAR_ANO",
    }
    var_label = st.selectbox("Variável", list(VAR_OPTIONS.keys()), label_visibility="collapsed")
    var_col   = VAR_OPTIONS[var_label]

    st.markdown("**Janela temporal**")
    min_year = int(df["DATA"].dt.year.min())
    max_year = int(df["DATA"].dt.year.max())
    ano_ini, ano_fim = st.slider(
        "Ano", min_year, max_year, (2000, max_year),
        label_visibility="collapsed",
    )

    st.divider()
    st.markdown("**Séries**")

    def _make_select_all_cb(tipo: str, rows: pd.DataFrame):
        def cb():
            val = st.session_state[f"all_{tipo}"]
            for cod in rows["CODIGO"].tolist():
                st.session_state[f"s_{cod}"] = val
        return cb

    for tipo in TIPO_ORDER:
        rows = series_by_type[tipo]
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
st.markdown(
    f"""
    <div style="display:flex; align-items:center; justify-content:space-between;
                margin-bottom:0.6rem; gap:1rem">
        <div>
            <p style="font-size:1.7rem; font-weight:700; color:{title_color};
                      margin:0; line-height:1.2">
                Análise Descritiva — IPCA
            </p>
            <p style="color:{sub_color}; font-size:0.88rem; margin:3px 0 0 0">
                Região Metropolitana de São Paulo &nbsp;·&nbsp;
                IBGE &nbsp;·&nbsp; {ano_ini}–{ano_fim}
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
col_a, col_b, col_c, col_d, _ = st.columns([1.5, 1.8, 2.0, 2.2, 3])
with col_a:
    show_series   = st.toggle("📉 Série",        value=True)
with col_b:
    show_trend    = st.toggle("📈 Tendência",    value=False)
with col_c:
    show_seasonal = st.toggle("🌊 Sazonalidade", value=False)
with col_d:
    cb_friendly   = st.toggle("👁 Daltônico",    value=False)

palette = PALETTE_CB if cb_friendly else PALETTE

if not selected:
    st.info("Selecione ao menos uma série no painel lateral.")
    st.stop()

if not show_series and not show_trend and not show_seasonal:
    st.warning("Ative ao menos um componente para visualizar o gráfico.")
    st.stop()

# ── Filtragem por janela temporal ─────────────────────────────────────────────
df_sel = df[
    df["CODIGO"].isin(selected) &
    (df["DATA"].dt.year >= ano_ini) &
    (df["DATA"].dt.year <= ano_fim)
].copy()

# ── Decomposição STL (cacheada por série + variável) ──────────────────────────
@st.cache_data(show_spinner=False)
def get_decomposition(cod: str, col: str):
    sub   = df[df["CODIGO"] == cod].set_index("DATA")[col].sort_index()
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
n_rows    = 1 + (1 if show_seasonal else 0)
heights   = [0.62, 0.38] if show_seasonal else [1.0]
subtitles = [var_label] + (["Componente Sazonal"] if show_seasonal else [])

fig = make_subplots(
    rows=n_rows,
    cols=1,
    shared_xaxes=True,
    row_heights=heights,
    vertical_spacing=0.10,
    subplot_titles=subtitles,
)

# Cor dos títulos dos subplots
for ann in fig.layout.annotations:
    ann.font.color = font_color

stl_warnings = []

for i, cod in enumerate(selected):
    color = palette[i % len(palette)]
    sub   = df_sel[df_sel["CODIGO"] == cod].sort_values("DATA")
    if sub.empty:
        continue

    nome = sub["NOME_ATIVO"].iloc[0]
    y    = sub.set_index("DATA")[var_col].sort_index()

    # Qual componente aparece primeiro na legenda para este grupo
    legend_anchor = (
        "series"   if show_series   else
        "trend"    if show_trend    else
        "seasonal"
    )

    # ── Série original ────────────────────────────────────────────────────────
    if show_series:
        fig.add_trace(
            go.Scatter(
                x=y.index,
                y=y.values,
                name=nome,
                line=dict(color=color, width=1.8),
                legendgroup=cod,
                showlegend=(legend_anchor == "series"),
                hovertemplate=(
                    f"<b>{nome}</b><br>%{{x|%b %Y}}: %{{y:.2f}}%<extra></extra>"
                ),
            ),
            row=1, col=1,
        )

    # ── Decomposição ──────────────────────────────────────────────────────────
    if show_trend or show_seasonal:
        trend, seasonal = get_decomposition(cod, var_col)

        if trend is None:
            stl_warnings.append(nome)
        else:
            mask = (trend.index.year >= ano_ini) & (trend.index.year <= ano_fim)

            if show_trend:
                t = trend[mask]
                fig.add_trace(
                    go.Scatter(
                        x=t.index,
                        y=t.values,
                        name=nome,
                        line=dict(color=color, width=2.8, dash="dash"),
                        legendgroup=cod,
                        showlegend=(legend_anchor == "trend"),
                        hovertemplate=(
                            f"<b>Tendência — {nome}</b><br>"
                            "%{x|%b %Y}: %{y:.2f}%<extra></extra>"
                        ),
                    ),
                    row=1, col=1,
                )

            if show_seasonal:
                s = seasonal[mask]
                fig.add_trace(
                    go.Scatter(
                        x=s.index,
                        y=s.values,
                        name=nome,
                        line=dict(color=color, width=1.5),
                        legendgroup=cod,
                        showlegend=(legend_anchor == "seasonal"),
                        hovertemplate=(
                            f"<b>Sazonalidade — {nome}</b><br>"
                            "%{x|%b %Y}: %{y:.2f}%<extra></extra>"
                        ),
                    ),
                    row=2, col=1,
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
    ticksuffix="%",
    tickfont=dict(color=font_color),
    title_font=dict(color=font_color),
)
fig.update_yaxes(title_text=var_label, row=1, col=1)
if show_seasonal:
    fig.update_yaxes(title_text="Componente sazonal (%)", row=2, col=1)
    fig.update_xaxes(title_text="Data", row=2, col=1)
else:
    fig.update_xaxes(title_text="Data", row=1, col=1)

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

if stl_warnings:
    st.caption(
        "⚠️ Decomposição STL não disponível para: "
        + ", ".join(f"**{n}**" for n in stl_warnings)
        + " (série com menos de 24 meses não nulos)."
    )

# ── Tabela informativa ────────────────────────────────────────────────────────
with st.expander("ℹ️ Informações das séries selecionadas"):
    st.dataframe(
        series_info[series_info["CODIGO"].isin(selected)][
            ["CODIGO", "NOME_ATIVO", "CATEGORIA_TIPO", "COMPLETUDE_INFO"]
        ].reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
    )
