
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


st.title("🩺 Causas mortalidad mundial GBD 2017")

# El dataset se carga directamente desde el archivo incluido en el proyecto.
# Ya no se muestra ninguna opción para cargar archivos desde la interfaz.
if not DEFAULT_FILE.exists():
    st.error(f"No se encontró el dataset incluido: {DEFAULT_FILE.name}")
    st.stop()

try:
    file_bytes = DEFAULT_FILE.read_bytes()
    df, header_row = load_dataframe_from_bytes(file_bytes, DEFAULT_FILE.name)
except Exception as e:
    st.error(f"No fue posible procesar el dataset incluido: {e}")
    st.stop()

ctx = interpretation_text(df)


# ============================================================
# PANEL DE VISUALIZACIÓN PROFESIONAL
# ============================================================

st.markdown("""
<style>
    .block-container {padding-top: 2rem; padding-bottom: 2rem;}
    .section-title {
        font-size: 1.35rem;
        font-weight: 700;
        margin-top: 1rem;
        margin-bottom: .25rem;
    }
    .section-subtitle {
        color: #6b7280;
        margin-bottom: 1rem;
    }
    div[data-testid="stMetric"] {
        border: 1px solid rgba(128,128,128,.18);
        border-radius: 14px;
        padding: 12px 14px;
        background: rgba(128,128,128,.05);
    }
    .insight {
        border-left: 4px solid #64748b;
        padding: 10px 14px;
        margin: 8px 0 18px 0;
        background: rgba(100,116,139,.07);
        border-radius: 0 10px 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# ---------- filtros ----------
st.sidebar.header("Filtros interactivos")

groups = sorted(df["grupo_gbd_nivel1_es"].dropna().unique())
selected_groups = st.sidebar.multiselect(
    "Grupo GBD nivel 1", groups, default=groups
)

trends = sorted(df["tendencia"].dropna().unique())
selected_trends = st.sidebar.multiselect(
    "Tendencia", trends, default=trends
)

min_pct = float(df["participacion_pct"].min())
max_pct = float(df["participacion_pct"].max())
pct_range = st.sidebar.slider(
    "Participación de muertes (%)",
    min_value=0.0,
    max_value=max(1.0, round(max_pct, 2)),
    value=(0.0, max(1.0, round(max_pct, 2))),
    step=0.1,
)

top_n = st.sidebar.slider("Causas mostradas en rankings", 5, 25, 25, key="filtro_top_n")

filtered = df[
    df["grupo_gbd_nivel1_es"].isin(selected_groups)
    & df["tendencia"].isin(selected_trends)
    & df["participacion_pct"].between(pct_range[0], pct_range[1])
].copy()

if filtered.empty:
    st.warning("No hay registros que coincidan con los filtros seleccionados.")
    st.stop()

# Recalcular contexto sobre el subconjunto filtrado para que los KPIs sean dinámicos.
f_top = filtered.nlargest(1, "participacion_pct").iloc[0]
f_top10 = filtered.nlargest(min(10, len(filtered)), "participacion_pct")
f_increase = filtered[filtered["tendencia"].str.lower().eq("aumento")]
f_decrease = filtered[filtered["tendencia"].str.lower().eq("descenso")]


# ============================================================
# TAB 1 — PANORAMA
# ============================================================

# 1. Ranking horizontal
st.subheader("1. Principales causas de muerte")
st.caption("Ranking de las causas con mayor participación en el total de muertes de 2017.")

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
        color="grupo_gbd_nivel1_es",
        hover_data={
            "participacion_pct": ":.2f",
            "variacion_pp": ":.2f",
            "tendencia": True,
            "grupo_gbd_nivel1_es": True,
        },
        labels={
            "participacion_pct": "Participación (%)",
            "causa_original": "Causa",
            "grupo_gbd_nivel1_es": "Grupo GBD",
        },
        title=f"Top {min(top_n, len(filtered))} causas por participación",
)
fig_top.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
fig_top.update_layout(
        height=620,
        margin=dict(l=20, r=80, t=70, b=20),
        legend_title_text="Grupo GBD",
)
st.plotly_chart(fig_top, use_container_width=True)

st.markdown(
        f'<div class="insight"><b>Hallazgo:</b> la causa con mayor participación dentro de la selección es '
        f'<b>{f_top["causa_original"]}</b>, con <b>{f_top["participacion_pct"]:.2f}%</b>. '
        f'Las 10 primeras concentran <b>{f_top10["participacion_pct"].sum():.2f}%</b> del total representado.</div>',
        unsafe_allow_html=True,
)

# 2. Composición por grandes grupos
st.subheader("2. Composición de las muertes por grupo GBD")

# Los tres grupos GBD de nivel 1 son categorías exhaustivas:
# Enfermedades no transmisibles + CMNN + Lesiones = 100%
# En el dataset cargado, la suma directa de las causas de ENT queda
# incompleta, mientras que CMNN y Lesiones sí conservan su participación.
# Por ello, para esta gráfica se calcula ENT como el porcentaje residual
# necesario para completar el 100% de la mortalidad.
group_df = (
        filtered.groupby("grupo_gbd_nivel1_es", as_index=False)
        .agg(
            participacion_observada=("participacion_pct", "sum"),
            causas=("id_causa", "count"),
        )
)

# Identifica el grupo de enfermedades no transmisibles
ncd_mask = group_df["grupo_gbd_nivel1_es"].astype(str).str.contains(
    "no transmisibles", case=False, na=False
)

if ncd_mask.any():
    otros_pct = group_df.loc[~ncd_mask, "participacion_observada"].sum()
    ncd_residual = max(0.0, 100.0 - otros_pct)

    group_df.loc[ncd_mask, "participacion_pct"] = ncd_residual

    # Conserva los demás grupos con sus valores observados
    group_df.loc[~ncd_mask, "participacion_pct"] = group_df.loc[
        ~ncd_mask, "participacion_observada"
    ]
else:
    # Si el dataset no contiene ENT, mantiene el cálculo original
    group_df["participacion_pct"] = group_df["participacion_observada"]

group_df = group_df.sort_values("participacion_pct", ascending=False)

fig_group = px.bar(
        group_df,
        x="grupo_gbd_nivel1_es",
        y="participacion_pct",
        text="participacion_pct",
        color="grupo_gbd_nivel1_es",
        custom_data=["causas", "participacion_observada"],
        labels={
            "grupo_gbd_nivel1_es": "Grupo GBD nivel 1",
            "participacion_pct": "Participación de las muertes (%)",
        },
        title="¿Qué grandes grupos explican una mayor proporción de las muertes?",
)
fig_group.update_traces(
        texttemplate="%{text:.2f}%",
        textposition="outside",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Participación: %{y:.2f}%<br>"
            "Causas: %{customdata[0]}<br>"
            "Participación observada en dataset: %{customdata[1]:.2f}%"
            "<extra></extra>"
        ),
)
fig_group.update_layout(
    height=470,
    showlegend=False,
    margin=dict(l=20, r=30, t=70, b=80)
)
st.plotly_chart(fig_group, use_container_width=True)

# Lectura de la composición por grandes grupos.
if not group_df.empty:
    top_group = group_df.iloc[0]
    if len(group_df) > 1:
        second_group = group_df.iloc[1]
        hallazgo_grupos = (
            f'<div class="insight"><b>Hallazgo:</b> el grupo <b>{top_group["grupo_gbd_nivel1_es"]}</b> '
            f'concentra la mayor proporción, con <b>{top_group["participacion_pct"]:.2f}%</b> de las '
            f'muertes representadas. Le sigue <b>{second_group["grupo_gbd_nivel1_es"]}</b> con '
            f'<b>{second_group["participacion_pct"]:.2f}%</b>. '
            f'En conjunto, estos grupos permiten identificar qué grandes áreas de enfermedad '
            f'tienen mayor peso dentro de la mortalidad analizada.</div>'
        )
    else:
        hallazgo_grupos = (
            f'<div class="insight"><b>Hallazgo:</b> el grupo '
            f'<b>{top_group["grupo_gbd_nivel1_es"]}</b> representa '
            f'<b>{top_group["participacion_pct"]:.2f}%</b> de las muertes representadas.</div>'
        )
    st.markdown(hallazgo_grupos, unsafe_allow_html=True)


# ============================================================
# TAB 2 — EVOLUCIÓN
# ============================================================

# 3. Magnitud vs variación
st.subheader("3. Impacto frente a evolución")
st.caption("La posición de cada burbuja combina el peso de la causa en 2017 con su variación entre 2010 y 2017.")

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
            "participacion_pct": "Participación 2017 (%)",
            "grupo_gbd_nivel1_es": "Grupo GBD",
        },
        title="Causas de alto impacto: ¿aumentan o disminuyen?",
)
scatter.add_vline(x=0, line_dash="dash", annotation_text="Sin variación", annotation_position="top")
scatter.add_hline(
        y=filtered["participacion_pct"].median(),
        line_dash="dot",
        annotation_text="Mediana de participación",
        annotation_position="bottom right",
)
scatter.update_layout(height=650, margin=dict(l=20, r=30, t=80, b=40))
st.plotly_chart(scatter, use_container_width=True)

st.markdown(
        '<div class="insight"><b>Cómo leerlo:</b> a la derecha se encuentran las causas con variación positiva; '
        'a la izquierda, las que presentan descenso. Las causas más altas en el eje vertical tienen mayor peso en 2017.</div>',
        unsafe_allow_html=True,
)

# 4. Cambios más relevantes
st.subheader("4. Cambios más relevantes en las causas")
st.caption("Compara las causas con las mayores variaciones entre 2010 y 2017. El tamaño del punto representa su participación en 2017.")

inc = filtered.nlargest(min(6, len(filtered)), "variacion_pp").copy()
dec = filtered.nsmallest(min(6, len(filtered)), "variacion_pp").copy()
change_df = pd.concat([inc, dec], ignore_index=True).drop_duplicates(subset=["id_causa"])
change_df["comportamiento"] = change_df["variacion_pp"].apply(lambda x: "Aumento" if x > 0 else "Descenso")
change_df = change_df.sort_values("variacion_pp")

fig_change = px.scatter(
    change_df,
    x="variacion_pp",
    y="causa_original",
    size="participacion_pct",
    color="comportamiento",
    text="variacion_pp",
    custom_data=["participacion_pct", "grupo_gbd_nivel1_es"],
    labels={
        "variacion_pp": "Variación 2010–2017 (puntos porcentuales)",
        "causa_original": "Causa",
        "comportamiento": "Comportamiento",
    },
    title="Causas con mayor cambio relativo",
)
fig_change.add_vline(x=0, line_dash="dash", annotation_text="Sin cambio", annotation_position="top")
fig_change.update_traces(
    texttemplate="%{text:.2f} pp",
    textposition="middle right",
    hovertemplate="<b>%{y}</b><br>Variación: %{x:.2f} pp<br>Participación 2017: %{customdata[0]:.2f}%<br>Grupo GBD: %{customdata[1]}<extra></extra>",
)
fig_change.update_layout(
    height=650,
    margin=dict(l=20, r=90, t=80, b=40),
    xaxis=dict(zeroline=False),
    yaxis=dict(categoryorder="array", categoryarray=change_df["causa_original"]),
)
st.plotly_chart(fig_change, use_container_width=True)

best_inc = inc.iloc[0]
best_dec = dec.iloc[0]
st.markdown(
    f'<div class="insight"><b>Lectura:</b> el mayor aumento observado es <b>{best_inc["causa_original"]}</b> ({best_inc["variacion_pp"]:+.2f} pp), mientras que el mayor descenso corresponde a <b>{best_dec["causa_original"]}</b> ({best_dec["variacion_pp"]:+.2f} pp).</div>',
    unsafe_allow_html=True,
)

# 5. Distribución estadística del cambio
st.subheader("5. ¿Cómo se distribuyó el cambio entre 2010 y 2017?")
st.caption(
    "El diagrama de caja permite comparar la variación de las causas, "
    "identificar el cambio típico y detectar valores extremos."
)

trend_order = ["Aumento", "Descenso"]
box_df = filtered.copy()
box_df["tendencia"] = box_df["tendencia"].str.strip().str.capitalize()

fig_trend = px.box(
    box_df,
    x="tendencia",
    y="variacion_pp",
    color="tendencia",
    points="all",
    hover_name="causa_original",
    hover_data={
        "variacion_pp": ":.2f",
        "participacion_pct": ":.2f",
        "grupo_gbd_nivel1_es": True,
        "tendencia": False,
    },
    category_orders={"tendencia": trend_order},
    labels={
        "tendencia": "Tendencia",
        "variacion_pp": "Variación 2010–2017 (puntos porcentuales)",
    },
    title="Distribución de la variación de las causas",
)

fig_trend.add_hline(
    y=0,
    line_dash="dash",
    annotation_text="Sin cambio",
    annotation_position="top right",
)

fig_trend.update_layout(
    height=520,
    showlegend=False,
    margin=dict(l=20, r=30, t=75, b=40),
)

st.plotly_chart(fig_trend, use_container_width=True)

median_inc = box_df.loc[
    box_df["tendencia"].eq("Aumento"), "variacion_pp"
].median()
median_dec = box_df.loc[
    box_df["tendencia"].eq("Descenso"), "variacion_pp"
].median()

st.markdown(
    f'<div class="insight"><b>Lectura:</b> la mediana de las causas en aumento es '
    f'<b>{median_inc:+.2f} pp</b>, mientras que la mediana de las causas en descenso es '
    f'<b>{median_dec:+.2f} pp</b>. Los puntos individuales permiten identificar causas '
    f'con cambios especialmente altos o bajos.</div>',
    unsafe_allow_html=True,
)

# ============================================================
# TAB 3 — CLASIFICACIÓN
# ============================================================

# 6. Categorías GBD nivel 2 — ranking horizontal
st.subheader("6. Categorías GBD nivel 2 con mayor participación")
st.caption(
    "Ranking de las categorías específicas que concentran una mayor proporción "
    "de las muertes, facilitando la comparación entre categorías."
)

cat_df = (
        filtered.groupby(
            ["grupo_gbd_nivel1_es", "categoria_gbd_nivel2_es"],
            as_index=False
        )
        .agg(
            participacion_pct=("participacion_pct", "sum"),
            causas=("id_causa", "count"),
        )
        .sort_values("participacion_pct", ascending=False)
)

# Mostrar las 15 categorías más relevantes para mantener una lectura limpia
cat_top = cat_df.head(min(15, len(cat_df))).copy()
cat_top = cat_top.sort_values("participacion_pct", ascending=True)

fig_cat = px.bar(
        cat_top,
        x="participacion_pct",
        y="categoria_gbd_nivel2_es",
        orientation="h",
        color="grupo_gbd_nivel1_es",
        text="participacion_pct",
        custom_data=["grupo_gbd_nivel1_es", "causas"],
        labels={
            "participacion_pct": "Participación en las muertes (%)",
            "categoria_gbd_nivel2_es": "Categoría GBD nivel 2",
            "grupo_gbd_nivel1_es": "Grupo GBD nivel 1",
        },
        title="Top 15 categorías GBD nivel 2 por participación",
)

fig_cat.update_traces(
        texttemplate="%{text:.2f}%",
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Participación: %{x:.2f}%<br>"
            "Grupo GBD: %{customdata[0]}<br>"
            "Número de causas: %{customdata[1]}"
            "<extra></extra>"
        ),
)

fig_cat.update_layout(
        height=650,
        margin=dict(l=20, r=90, t=70, b=30),
        yaxis=dict(categoryorder="array", categoryarray=cat_top["categoria_gbd_nivel2_es"]),
        legend_title_text="Grupo GBD nivel 1",
)

st.plotly_chart(fig_cat, use_container_width=True)

if not cat_df.empty:
    top_category = cat_df.iloc[0]
    top_5_categories = cat_df.head(min(5, len(cat_df)))["participacion_pct"].sum()

    st.markdown(
        f'<div class="insight"><b>Hallazgo:</b> la categoría con mayor participación es '
        f'<b>{top_category["categoria_gbd_nivel2_es"]}</b>, con '
        f'<b>{top_category["participacion_pct"]:.2f}%</b> de las muertes representadas. '
        f'Las 5 categorías principales concentran <b>{top_5_categories:.2f}%</b> del total.</div>',
        unsafe_allow_html=True,
    )

st.subheader("Tabla de causas seleccionadas")
table_cols = [
        "ranking_calculado",
        "causa_original",
        "participacion_pct",
        "variacion_pp",
        "tendencia",
        "grupo_gbd_nivel1_es",
        "categoria_gbd_nivel2_es",
]
# El ranking de la tabla se recalcula sobre el conjunto actualmente filtrado.
# Así, el primer registro visible comienza en 1 y el orden responde a la selección del usuario.
table = filtered[table_cols].copy()
table["ranking_filtrado"] = (
    table["participacion_pct"]
    .rank(method="min", ascending=False)
    .astype(int)
)

table = table.sort_values(
    ["ranking_filtrado", "causa_original"]
).copy()

table = table[
    [
        "ranking_filtrado",
        "causa_original",
        "participacion_pct",
        "variacion_pp",
        "tendencia",
        "grupo_gbd_nivel1_es",
        "categoria_gbd_nivel2_es",
    ]
]

table.columns = [
    "Ranking",
    "Causa",
    "Participación 2017 (%)",
    "Variación 2010–2017 (pp)",
    "Tendencia",
    "Grupo GBD nivel 1",
    "Categoría GBD nivel 2",
]

st.dataframe(
    table,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Ranking": st.column_config.NumberColumn(
            "Ranking",
            help="Posición de la causa dentro de los registros que cumplen los filtros actuales.",
            format="%d",
        ),
        "Participación 2017 (%)": st.column_config.NumberColumn(
            "Participación 2017 (%)",
            format="%.2f%%",
        ),
        "Variación 2010–2017 (pp)": st.column_config.NumberColumn(
            "Variación 2010–2017 (pp)",
            format="%+.2f",
        ),
    },
)


# ---------- descarga ----------
csv = filtered.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "⬇️ Descargar datos procesados (CSV)",
    data=csv,
    file_name="causas_mortalidad_GBD2017_procesado.csv",
    mime="text/csv",
)

# ----------------------------
# Enriquecimiento / fuentes
# ----------------------------
st.subheader("Fuentes y trazabilidad")
st.markdown("""El dataset conserva la trazabilidad de clasificación GBD y las referencias metodológicas. Las fuentes externas se presentan como contexto para interpretar la información y documentar el origen de las clasificaciones utilizadas.""")
context_df = build_external_context()
st.dataframe(context_df, use_container_width=True, hide_index=True)
st.caption("Proyecto académico de visualización de datos. Las estimaciones de mortalidad deben interpretarse como datos epidemiológicos estimados y no como conteos directos de registros civiles.")
