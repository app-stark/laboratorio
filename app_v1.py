
import io
import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Causas de mortalidad mundial 2017",
    page_icon="🩺",
    layout="wide",
)

REQUIRED_COLUMNS = [
    "id_causa",
    "causa_original",
    "porcentaje_muertes_2017",
    "variacion_anual_2010_2017",
    "tendencia",
    "ranking_2017",
    "grupo_gbd_nivel1_es",
    "categoria_gbd_nivel2_es",
    "grupo_gbd_nivel1_en",
    "categoria_gbd_nivel2_en",
    "orden_categoria_gbd",
    "fuente_metodologica",
    "url_gbd_2017",
    "url_gbd_cod_2017",
    "url_who_ghe",
    "porcentaje_muertes_2017_pp",
    "variacion_anual_2010_2017_pp",
]

DEFAULT_FILE = Path(__file__).with_name("dataset_final_causas_GBD2017.xlsx")


def normalize_name(value):
    value = str(value).strip().lower()
    value = re.sub(r"\s+", "_", value)
    return value


def find_header_row(raw):
    """Encuentra automáticamente la primera fila que contiene id_causa."""
    for i in range(min(len(raw), 100)):
        values = {normalize_name(v) for v in raw.iloc[i].tolist()}
        if "id_causa" in values:
            return i
    raise ValueError("No se encontró una fila de encabezados con 'id_causa'.")


@st.cache_data
def load_dataframe_from_bytes(file_bytes, filename):
    suffix = Path(filename).suffix.lower()

    if suffix in [".xlsx", ".xls"]:
        raw = pd.read_excel(io.BytesIO(file_bytes), header=None)
    elif suffix == ".csv":
        raw = pd.read_csv(io.BytesIO(file_bytes), header=None)
    else:
        raise ValueError("Formato no soportado. Usa XLSX, XLS o CSV.")

    header_row = find_header_row(raw)
    df = raw.iloc[header_row + 1:].copy()
    df.columns = [normalize_name(x) for x in raw.iloc[header_row].tolist()]

    # Elimina columnas completamente vacías y filas sin identificador.
    df = df.dropna(axis=1, how="all")
    df = df[df["id_causa"].notna()].copy()

    # Conserva solo las columnas disponibles y avisa de las que falten.
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            "Faltan columnas requeridas: " + ", ".join(missing)
        )

    # Conversión numérica robusta.
    numeric_cols = [
        "porcentaje_muertes_2017",
        "variacion_anual_2010_2017",
        "ranking_2017",
        "orden_categoria_gbd",
        "porcentaje_muertes_2017_pp",
        "variacion_anual_2010_2017_pp",
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Limpieza de texto.
    text_cols = df.select_dtypes(include=["object"]).columns
    for col in text_cols:
        df[col] = df[col].astype(str).str.strip()

    # Elimina registros sin causa.
    df = df[df["causa_original"].notna()]
    df = df[df["causa_original"].astype(str).str.lower() != "nan"]

    # Cálculos derivados para análisis.
    df["participacion_pct"] = df["porcentaje_muertes_2017"] * 100
    df["variacion_pp"] = df["variacion_anual_2010_2017"] * 100
    df["abs_variacion_pp"] = df["variacion_pp"].abs()

    # Ranking recalculado: evita depender de un orden externo.
    df["ranking_calculado"] = (
        df["porcentaje_muertes_2017"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    return df.reset_index(drop=True), header_row


def build_external_context():
    """Metadatos de enriquecimiento metodológico procedentes de fuentes externas."""
    return pd.DataFrame(
        [
            {
                "fuente": "OMS - Global Health Estimates",
                "tipo": "Fuente metodológica",
                "uso": "Contraste y contextualización de estadísticas de mortalidad.",
                "url": "https://www.who.int/data/global-health-estimates/",
            },
            {
                "fuente": "OMS - WHO Mortality Database",
                "tipo": "Fuente metodológica",
                "uso": "Contexto sobre registro y clasificación de causas de muerte.",
                "url": "https://platform.who.int/mortality/about/about-the-who-mortality-database",
            },
            {
                "fuente": "OMS - Clasificación de causas de muerte",
                "tipo": "Clasificación",
                "uso": "Contexto sobre la causa subyacente y estándares de clasificación.",
                "url": "https://www.who.int/standards/classifications/classification-of-diseases/cause-of-death",
            },
            {
                "fuente": "IHME - Global Burden of Disease",
                "tipo": "Fuente metodológica",
                "uso": "Contextualización de la clasificación GBD utilizada por el dataset.",
                "url": "https://www.healthdata.org/research-analysis/gbd",
            },
        ]
    )


def interpretation_text(df):
    top = df.nlargest(1, "porcentaje_muertes_2017").iloc[0]
    top10 = df.nlargest(10, "porcentaje_muertes_2017")
    increase = df[df["tendencia"].str.lower().eq("aumento")]
    decrease = df[df["tendencia"].str.lower().eq("descenso")]

    return {
        "top": top["causa_original"],
        "top_pct": top["participacion_pct"],
        "top10_pct": top10["participacion_pct"].sum(),
        "increase": len(increase),
        "decrease": len(decrease),
    }


st.title("🩺 Causas de mortalidad mundial — GBD 2017")
st.markdown(
    "Laboratorio de limpieza, preparación, enriquecimiento y visualización de datos."
)

with st.sidebar:
    st.header("Carga de datos")
    uploaded = st.file_uploader(
        "Sube el dataset",
        type=["xlsx", "xls", "csv"],
        help="La aplicación detecta automáticamente la primera fila que contiene id_causa y se adapta al número de registros.",
    )

    if uploaded is not None:
        file_bytes = uploaded.getvalue()
        filename = uploaded.name
    elif DEFAULT_FILE.exists():
        file_bytes = DEFAULT_FILE.read_bytes()
        filename = DEFAULT_FILE.name
        st.info("Usando el dataset incluido en el proyecto.")
    else:
        st.warning("Sube un archivo XLSX, XLS o CSV para comenzar.")
        st.stop()

try:
    df, header_row = load_dataframe_from_bytes(file_bytes, filename)
except Exception as e:
    st.error(f"No fue posible procesar el archivo: {e}")
    st.stop()

ctx = interpretation_text(df)

# ----------------------------
# KPIs
# ----------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Causas analizadas", f"{len(df):,}")
c2.metric("Principal causa", ctx["top"])
c3.metric("Participación principal", f"{ctx['top_pct']:.2f}%")
c4.metric("Top 10 causas", f"{ctx['top10_pct']:.2f}%")

st.caption(
    f"Encabezados detectados automáticamente en la fila {header_row + 1}. "
    f"Registros válidos procesados: {len(df)}."
)

# ----------------------------
# Filtros
# ----------------------------
st.sidebar.header("Filtros")

groups = sorted(df["grupo_gbd_nivel1_es"].dropna().unique())
selected_groups = st.sidebar.multiselect(
    "Grupo GBD nivel 1",
    groups,
    default=groups,
)

trends = sorted(df["tendencia"].dropna().unique())
selected_trends = st.sidebar.multiselect(
    "Tendencia",
    trends,
    default=trends,
)

min_pct, max_pct = float(df["participacion_pct"].min()), float(df["participacion_pct"].max())
pct_range = st.sidebar.slider(
    "Participación de muertes (%)",
    min_value=0.0,
    max_value=max(1.0, round(max_pct, 2)),
    value=(0.0, max(1.0, round(max_pct, 2))),
    step=0.1,
)

filtered = df[
    df["grupo_gbd_nivel1_es"].isin(selected_groups)
    & df["tendencia"].isin(selected_trends)
    & df["participacion_pct"].between(pct_range[0], pct_range[1])
].copy()

st.subheader("1. Principales causas de muerte")

top_n = st.slider("Número de causas a mostrar", 5, 25, 15)

top_df = (
    filtered.nlargest(top_n, "participacion_pct")
    .sort_values("participacion_pct")
)

fig_top = px.bar(
    top_df,
    x="participacion_pct",
    y="causa_original",
    orientation="h",
    text="participacion_pct",
    labels={
        "participacion_pct": "Porcentaje de muertes (%)",
        "causa_original": "Causa",
    },
    title=f"Top {top_n} causas por participación en las muertes de 2017",
)
fig_top.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
fig_top.update_layout(height=600, margin=dict(l=20, r=50, t=70, b=20))
st.plotly_chart(fig_top, use_container_width=True)

st.markdown(
    f"**Lectura:** {ctx['top']} presenta la mayor participación individual, "
    f"con aproximadamente {ctx['top_pct']:.2f}% del total representado por el dataset. "
    f"Las diez primeras causas concentran cerca del {ctx['top10_pct']:.2f}%."
)

# ----------------------------
# Tendencia vs magnitud
# ----------------------------
st.subheader("2. Magnitud de la causa frente a su evolución")

scatter = px.scatter(
    filtered,
    x="variacion_pp",
    y="participacion_pct",
    size="participacion_pct",
    color="grupo_gbd_nivel1_es",
    hover_name="causa_original",
    hover_data={
        "participacion_pct": ":.2f",
        "variacion_pp": ":.2f",
        "tendencia": True,
        "grupo_gbd_nivel1_es": True,
    },
    labels={
        "variacion_pp": "Variación 2010–2017 (puntos porcentuales)",
        "participacion_pct": "Participación de muertes 2017 (%)",
        "grupo_gbd_nivel1_es": "Grupo GBD nivel 1",
    },
    title="¿Qué causas tienen mayor peso y cuáles están cambiando?",
)
scatter.add_vline(x=0, line_dash="dash")
scatter.add_hline(y=filtered["participacion_pct"].median(), line_dash="dot")
scatter.update_layout(height=620)
st.plotly_chart(scatter, use_container_width=True)

st.info(
    "La zona superior derecha reúne causas con alta participación y aumento; "
    "la superior izquierda, causas relevantes pero en descenso. "
    "Esta visualización es especialmente útil para priorizar causas de alto impacto."
)

# ----------------------------
# Grupo GBD
# ----------------------------
st.subheader("3. Distribución por grandes grupos GBD")

group_df = (
    filtered.groupby("grupo_gbd_nivel1_es", as_index=False)
    .agg(
        participacion_pct=("participacion_pct", "sum"),
        causas=("id_causa", "count"),
    )
    .sort_values("participacion_pct", ascending=False)
)

fig_group = px.bar(
    group_df,
    x="grupo_gbd_nivel1_es",
    y="participacion_pct",
    text="participacion_pct",
    labels={
        "grupo_gbd_nivel1_es": "Grupo GBD nivel 1",
        "participacion_pct": "Participación acumulada (%)",
    },
    title="Participación acumulada por grupo GBD",
)
fig_group.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
fig_group.update_layout(height=450)
st.plotly_chart(fig_group, use_container_width=True)

# ----------------------------
# Tendencias
# ----------------------------
st.subheader("4. Causas en aumento y en descenso")

trend_df = (
    filtered.groupby("tendencia", as_index=False)
    .agg(
        causas=("id_causa", "count"),
        participacion_pct=("participacion_pct", "sum"),
    )
)

fig_trend = px.bar(
    trend_df,
    x="tendencia",
    y="participacion_pct",
    text="participacion_pct",
    color="tendencia",
    labels={
        "tendencia": "Tendencia",
        "participacion_pct": "Participación acumulada (%)",
    },
    title="Participación de las causas según su tendencia",
)
fig_trend.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
fig_trend.update_layout(height=430, showlegend=False)
st.plotly_chart(fig_trend, use_container_width=True)

# ----------------------------
# Ranking de aumentos y descensos
# ----------------------------
a, b = st.columns(2)

with a:
    st.markdown("#### Mayores aumentos")
    inc = filtered.nlargest(10, "variacion_pp")[
        ["causa_original", "participacion_pct", "variacion_pp"]
    ].copy()
    inc.columns = ["Causa", "Muertes 2017 (%)", "Variación (pp)"]
    st.dataframe(inc, use_container_width=True, hide_index=True)

with b:
    st.markdown("#### Mayores descensos")
    dec = filtered.nsmallest(10, "variacion_pp")[
        ["causa_original", "participacion_pct", "variacion_pp"]
    ].copy()
    dec.columns = ["Causa", "Muertes 2017 (%)", "Variación (pp)"]
    st.dataframe(dec, use_container_width=True, hide_index=True)

# ----------------------------
# Enriquecimiento / fuentes
# ----------------------------
st.subheader("5. Enriquecimiento y trazabilidad de fuentes")

st.markdown(
    """
El dataset incorpora campos de clasificación GBD, categoría GBD, fuente
metodológica y enlaces a GBD/OMS. Para el laboratorio se conserva esta
trazabilidad y se añade una capa de contexto metodológico basada en fuentes
externas de la OMS y GBD. Esto permite documentar de dónde procede la
clasificación y cómo debe interpretarse la información.
"""
)

context_df = build_external_context()
st.dataframe(context_df, use_container_width=True, hide_index=True)

st.markdown(
    "**Recomendación académica:** si el profesor exige un cruce numérico con "
    "otra base, añade un segundo archivo (por ejemplo, población 2017 por país "
    "o una tabla OMS con causas) y realiza el cruce por una clave compatible. "
    "No debe inventarse una correspondencia entre causas que no comparten una "
    "clave común."
)

# ----------------------------
# Tabla de datos procesados
# ----------------------------
st.subheader("6. Datos limpios y preparados")

show_cols = [
    "id_causa",
    "causa_original",
    "participacion_pct",
    "variacion_pp",
    "tendencia",
    "ranking_calculado",
    "grupo_gbd_nivel1_es",
    "categoria_gbd_nivel2_es",
]

st.dataframe(
    filtered[show_cols].sort_values("ranking_calculado"),
    use_container_width=True,
    hide_index=True,
)

csv = filtered.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "⬇️ Descargar datos procesados (CSV)",
    data=csv,
    file_name="causas_mortalidad_GBD2017_procesado.csv",
    mime="text/csv",
)

st.caption(
    "Proyecto académico de visualización de datos. Las estimaciones de "
    "mortalidad deben interpretarse como datos epidemiológicos estimados y no "
    "como conteos directos de registros civiles."
)
