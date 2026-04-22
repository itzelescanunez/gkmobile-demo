import path_setup
import streamlit as st
import duckdb
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
from config import parquet, CLIENTES

st.set_page_config(page_title="Monitor Geolocalización", layout="wide")

st.markdown("""
<style>
    .metric-card {
        background: #ffffff;
        border: 1px solid #E2E4E9;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }
    .metric-value { font-size: 2rem; font-weight: 700; margin: 0; color: #1A1D23; }
    .metric-label { font-size: 0.75rem; color: #6B7280; text-transform: uppercase;
                    letter-spacing: 0.08em; margin: 0; }
    .section-title { font-size: 1.1rem; font-weight: 600; color: #1A1D23;
                     border-left: 4px solid #0057FF; padding-left: 10px; margin-bottom: 16px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# CONEXIÓN
# ─────────────────────────────────────────
@st.cache_resource
def get_con():
    con = duckdb.connect()
    con.execute(f"CREATE OR REPLACE VIEW actividad   AS SELECT * FROM read_parquet('{parquet('actividad')}')")
    con.execute(f"CREATE OR REPLACE VIEW punto_venta AS SELECT * FROM read_parquet('{parquet('punto_venta')}')")
    con.execute(f"CREATE OR REPLACE VIEW usuario     AS SELECT * FROM read_parquet('{parquet('user')}')")
    con.execute(f"CREATE OR REPLACE VIEW cuadrilla   AS SELECT * FROM read_parquet('{parquet('cuadrilla')}')")
    con.execute("""
                CREATE OR REPLACE VIEW actividad_real AS
        WITH visitas_por_dia AS (
            SELECT usuario_id, CAST(fecha_planeada AS DATE) as dia, COUNT(*) as visitas
            FROM actividad
            GROUP BY usuario_id, CAST(fecha_planeada AS DATE)
        ),
        usuarios_sistema AS (
            SELECT usuario_id FROM visitas_por_dia
            GROUP BY usuario_id HAVING MAX(visitas) > 50
        )
                SELECT a.* FROM actividad a
                WHERE a.usuario_id NOT IN (SELECT usuario_id FROM usuarios_sistema)
                """)
    return con

con = get_con()

# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────
st.sidebar.title("Monitor Geo")

clientes_con_geo = {
    "Clip":    141,
    "Procesa": 26,
    "Castel":  102,
    "Eatics":  149,
}
cliente_sel = st.sidebar.selectbox("Cliente", list(clientes_con_geo.keys()))
cliente_id  = clientes_con_geo[cliente_sel]

@st.cache_data(ttl=600)
def ultimo_mes(cliente_id):
    row = con.execute("""
                      SELECT MAX(CAST(fecha_planeada AS DATE))
                      FROM actividad_real WHERE cliente_id = ?
                      """, [cliente_id]).fetchone()
    from datetime import date
    return row[0] if row[0] else date.today()

from datetime import date
ultima     = ultimo_mes(cliente_id)
inicio_def = ultima.replace(day=1)
fecha_ini  = st.sidebar.date_input("Fecha inicio", inicio_def)
fecha_fin  = st.sidebar.date_input("Fecha fin", ultima)

umbral_amarillo = st.sidebar.slider("Umbral alerta (m)", 100, 1000, 300, step=50)
umbral_rojo     = st.sidebar.slider("Umbral crítico (m)", 500, 20000, 1000, step=500)

# ─────────────────────────────────────────
# DATOS
# ─────────────────────────────────────────
@st.cache_data(ttl=300)
def cargar_visitas_geo(cliente_id, fecha_ini, fecha_fin):
    return con.execute("""
                       SELECT
                           a.id,
                           CAST(a.fecha_planeada AS DATE)              AS fecha,
                           u.user_real_name                             AS promotor,
                           COALESCE(c.ruta, 'Sin ruta')                AS ruta,
                           pv.sucursal                                  AS punto_venta,
                           pv.cadena_str                                AS cadena,
                           pv.estado_str                                AS estado,
                           TRY_CAST(a.latitude_check_in  AS DOUBLE)    AS lat_promotor,
                           TRY_CAST(a.longitude_check_in AS DOUBLE)    AS lon_promotor,
                           TRY_CAST(pv.latitude          AS DOUBLE)    AS lat_pdv,
                           TRY_CAST(pv.longitude         AS DOUBLE)    AS lon_pdv,
                           ROUND(111320 * SQRT(
                                   POWER(TRY_CAST(a.latitude_check_in AS DOUBLE) - TRY_CAST(pv.latitude AS DOUBLE), 2) +
                                   POWER((TRY_CAST(a.longitude_check_in AS DOUBLE) - TRY_CAST(pv.longitude AS DOUBLE))
                                             * COS(RADIANS(TRY_CAST(pv.latitude AS DOUBLE))), 2)
                                          ), 0)                                        AS distancia_metros
                       FROM actividad_real a
                                LEFT JOIN usuario u      ON u.id  = a.usuario_id
                                LEFT JOIN cuadrilla c    ON c.id  = a.cuadrilla_id
                                LEFT JOIN punto_venta pv ON pv.id = a.punto_venta_id
                       WHERE a.cliente_id = ?
                         AND CAST(a.fecha_planeada AS DATE) BETWEEN ? AND ?
                         AND a.fecha_real_inicio IS NOT NULL
                         AND a.latitude_check_in IS NOT NULL
                         AND a.latitude_check_in NOT IN ('None', 'nan', '')
                         AND pv.latitude IS NOT NULL
                         AND CAST(pv.latitude AS VARCHAR) NOT IN ('nan', 'None', '')
                       """, [cliente_id, str(fecha_ini), str(fecha_fin)]).df()

# ─────────────────────────────────────────
# RENDER
# ─────────────────────────────────────────
st.title("📍 Monitor Geolocalización")
st.caption(f"{cliente_sel}  ·  {fecha_ini} — {fecha_fin}")
st.divider()

with st.spinner("Cargando datos..."):
    df = cargar_visitas_geo(cliente_id, fecha_ini, fecha_fin)

if df.empty:
    st.info("Sin datos de geolocalización para este cliente y período.")
    st.stop()

# Clasificar por distancia
def clasificar(d):
    if pd.isna(d):       return "Sin dato"
    if d <= umbral_amarillo: return "En rango"
    if d <= umbral_rojo:     return "Alerta"
    return "Crítico"

df["estado_geo"] = df["distancia_metros"].apply(clasificar)

COLORES_GEO = {
    "En rango": "#22C55E",
    "Alerta":   "#F59E0B",
    "Crítico":  "#EF4444",
    "Sin dato": "#9CA3AF",
}

# KPIs
total        = len(df)
en_rango     = (df["estado_geo"] == "En rango").sum()
alerta       = (df["estado_geo"] == "Alerta").sum()
critico      = (df["estado_geo"] == "Crítico").sum()
pct_en_rango = round(en_rango / total * 100, 1) if total else 0

col1, col2, col3, col4, col5 = st.columns(5)

def metric_card(col, label, value, color="#1A1D23"):
    col.markdown(f"""
    <div class="metric-card">
        <p class="metric-label">{label}</p>
        <p class="metric-value" style="color:{color}">{value}</p>
    </div>
    """, unsafe_allow_html=True)

metric_card(col1, "Total visitas geo",   f"{total:,}")
metric_card(col2, "En rango",            f"{en_rango:,}",  "#22C55E")
metric_card(col3, "% en rango",          f"{pct_en_rango}%", "#22C55E")
metric_card(col4, "Alerta",              f"{alerta:,}",    "#F59E0B")
metric_card(col5, "Crítico",             f"{critico:,}",   "#EF4444")

st.divider()

# ── MAPA ─────────────────────────────────
st.markdown('<p class="section-title">Mapa de visitas</p>', unsafe_allow_html=True)

df_mapa = df.dropna(subset=["lat_pdv", "lon_pdv"]).copy()

if not df_mapa.empty:
    centro_lat = df_mapa["lat_pdv"].median()
    centro_lon = df_mapa["lon_pdv"].median()

    mapa = folium.Map(location=[centro_lat, centro_lon], zoom_start=10,
                      tiles="CartoDB positron")

    color_map = {"En rango": "green", "Alerta": "orange",
                 "Crítico": "red", "Sin dato": "gray"}

    for _, row in df_mapa.iterrows():
        folium.CircleMarker(
            location=[row["lat_pdv"], row["lon_pdv"]],
            radius=6,
            color=color_map.get(row["estado_geo"], "gray"),
            fill=True,
            fill_opacity=0.7,
            popup=folium.Popup(
                f"<b>{row['punto_venta']}</b><br>"
                f"Promotor: {row['promotor']}<br>"
                f"Fecha: {row['fecha']}<br>"
                f"Distancia: {int(row['distancia_metros'] or 0):,} m<br>"
                f"Estado: {row['estado_geo']}",
                max_width=250
            )
        ).add_to(mapa)

    st_folium(mapa, width="100%", height=500)
else:
    st.info("Sin coordenadas de PDV para mostrar en el mapa.")

st.divider()

# ── ANÁLISIS ──────────────────────────────
st.markdown('<p class="section-title">Análisis de anomalías</p>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["Por promotor", "Por ruta", "Detalle críticos"])

with tab1:
    df_promotor = df.groupby("promotor").agg(
        visitas=("id", "count"),
        criticas=("estado_geo", lambda x: (x == "Crítico").sum()),
        alertas=("estado_geo",  lambda x: (x == "Alerta").sum()),
        dist_promedio=("distancia_metros", "mean")
    ).reset_index()
    df_promotor["pct_anomalas"] = round(
        (df_promotor["criticas"] + df_promotor["alertas"]) / df_promotor["visitas"] * 100, 1
    )
    df_promotor = df_promotor.sort_values("criticas", ascending=False)

    fig = px.bar(df_promotor.head(15), x="promotor", y=["criticas", "alertas"],
                 title="Visitas fuera de rango por promotor",
                 color_discrete_map={"criticas": "#EF4444", "alertas": "#F59E0B"},
                 barmode="stack", height=380)
    fig.update_layout(xaxis_title="", yaxis_title="Visitas", xaxis_tickangle=-35)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    df_ruta = df.groupby("ruta").agg(
        visitas=("id", "count"),
        criticas=("estado_geo", lambda x: (x == "Crítico").sum()),
        alertas=("estado_geo",  lambda x: (x == "Alerta").sum()),
    ).reset_index()
    df_ruta["pct_anomalas"] = round(
        (df_ruta["criticas"] + df_ruta["alertas"]) / df_ruta["visitas"] * 100, 1
    )
    df_ruta = df_ruta.sort_values("criticas", ascending=False)

    fig = px.bar(df_ruta.head(15), x="ruta", y=["criticas", "alertas"],
                 title="Visitas fuera de rango por ruta",
                 color_discrete_map={"criticas": "#EF4444", "alertas": "#F59E0B"},
                 barmode="stack", height=380)
    fig.update_layout(xaxis_title="", yaxis_title="Visitas", xaxis_tickangle=-35)
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    df_criticos = df[df["estado_geo"].isin(["Crítico", "Alerta"])].copy()
    df_criticos = df_criticos.sort_values("distancia_metros", ascending=False)
    df_criticos["distancia_metros"] = df_criticos["distancia_metros"].apply(
        lambda x: f"{int(x):,} m" if pd.notna(x) else "—"
    )
    st.dataframe(
        df_criticos[["fecha", "promotor", "ruta", "punto_venta",
                     "cadena", "estado", "distancia_metros", "estado_geo"]],
        hide_index=True,
        width="stretch"
    )