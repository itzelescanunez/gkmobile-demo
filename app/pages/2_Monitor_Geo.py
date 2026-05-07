import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.path_setup import require_auth
require_auth()

import streamlit as st
import duckdb
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
from config import parquet, CLIENTES
import io

st.set_page_config(page_title="Monitor Geolocalización", layout="wide")

st.markdown("""
<style>
    .metric-card { background:#ffffff; border:1px solid #E2E4E9; border-radius:12px;
                   padding:20px; text-align:center; }
    .metric-value { font-size:2rem; font-weight:700; margin:0; color:#1A1D23; }
    .metric-label { font-size:0.75rem; color:#6B7280; text-transform:uppercase;
                    letter-spacing:0.08em; margin:0; }
    .section-title { font-size:1.1rem; font-weight:600; color:#1A1D23;
                     border-left:4px solid #0057FF; padding-left:10px; margin-bottom:16px; }
</style>
""", unsafe_allow_html=True)

def metric_card(col, label, value, color="#1A1D23"):
    col.markdown(f"""
    <div class="metric-card">
        <p class="metric-label">{label}</p>
        <p class="metric-value" style="color:{color}">{value}</p>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────
# CLIENTES CON GEO
# ─────────────────────────────────────────
CLIENTES_GEO = {
    "Clip":          141,
    "Procesa":        26,
    "Castel":        102,
    "Eatics":        149,
    "Philip Morris":   1,
    "Danone":        132,
    "Rabbit":        142,
    "Xiaomi":        127,
}

PARQUET_GEO = {
    141: "actividad_geo_clip",
    26:  "actividad_geo_procesa",
    102: "actividad_geo_castel",
    149: "actividad_geo_eatics",
    1:   "actividad_geo_philip_morris",
    132: "actividad_geo_danone",
    142: "actividad_geo_rabbit",
    127: "actividad_geo_xiaomi",
}

# ─────────────────────────────────────────
# CARGA DINÁMICA DEL PARQUET GEO
# ─────────────────────────────────────────
@st.cache_resource
def get_con_geo(cliente_id):
    nombre = PARQUET_GEO[cliente_id]
    path   = parquet(nombre, "geo")
    con    = duckdb.connect()
    con.execute(f"CREATE OR REPLACE VIEW geo      AS SELECT * FROM read_parquet('{path}')")
    con.execute(f"CREATE OR REPLACE VIEW usuario  AS SELECT * FROM read_parquet('{parquet('user', 'global')}')")
    return con

# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────
st.sidebar.title("Monitor Geo")

cliente_sel = st.sidebar.selectbox("Cliente", list(CLIENTES_GEO.keys()))
cliente_id  = CLIENTES_GEO[cliente_sel]
con         = get_con_geo(cliente_id)

# ── Fechas ────────────────────────────────
@st.cache_data(ttl=600)
def rango_fechas(cliente_id):
    row = con.execute("SELECT MIN(dia), MAX(dia) FROM geo").fetchone()
    from datetime import date
    return row[0] or date.today().replace(day=1), row[1] or date.today()

fecha_min, fecha_max = rango_fechas(cliente_id)
fecha_ini = st.sidebar.date_input("Fecha inicio", fecha_max.replace(day=1),
                                  min_value=fecha_min, max_value=fecha_max)
fecha_fin = st.sidebar.date_input("Fecha fin", fecha_max,
                                  min_value=fecha_min, max_value=fecha_max)

# ── Filtros encadenados ───────────────────
@st.cache_data(ttl=600)
def opciones_estados(cliente_id, fecha_ini, fecha_fin):
    r = con.execute("""
                    SELECT COALESCE(LIST(DISTINCT estado ORDER BY estado), []) as estados
                    FROM geo
                    WHERE dia BETWEEN ? AND ?
                      AND estado IS NOT NULL
                    """, [str(fecha_ini), str(fecha_fin)]).fetchone()
    return r[0] or []

@st.cache_data(ttl=600)
def opciones_municipios(cliente_id, fecha_ini, fecha_fin, estado_sel):
    filtro = f"AND estado = '{estado_sel}'" if estado_sel != "Todos" else ""
    r = con.execute(f"""
        SELECT COALESCE(LIST(DISTINCT municipio ORDER BY municipio), []) as municipios
        FROM geo
        WHERE dia BETWEEN ? AND ?
          AND municipio IS NOT NULL
          {filtro}
    """, [str(fecha_ini), str(fecha_fin)]).fetchone()
    return r[0] or []

@st.cache_data(ttl=600)
def opciones_cadenas(cliente_id, fecha_ini, fecha_fin, estado_sel, municipio_sel):
    conds = [f"dia BETWEEN '{fecha_ini}' AND '{fecha_fin}'", "cadena IS NOT NULL"]
    if estado_sel    != "Todos": conds.append(f"estado = '{estado_sel}'")
    if municipio_sel != "Todos": conds.append(f"municipio = '{municipio_sel}'")
    r = con.execute(f"""
        SELECT COALESCE(LIST(DISTINCT cadena ORDER BY cadena), []) as cadenas
        FROM geo WHERE {" AND ".join(conds)}
    """).fetchone()
    return r[0] or []

@st.cache_data(ttl=600)
def opciones_rutas(cliente_id, fecha_ini, fecha_fin, estado_sel, municipio_sel):
    conds = [f"dia BETWEEN '{fecha_ini}' AND '{fecha_fin}'", "ruta IS NOT NULL"]
    if estado_sel    != "Todos": conds.append(f"estado = '{estado_sel}'")
    if municipio_sel != "Todos": conds.append(f"municipio = '{municipio_sel}'")
    r = con.execute(f"""
        SELECT COALESCE(LIST(DISTINCT ruta ORDER BY ruta), []) as rutas
        FROM geo WHERE {" AND ".join(conds)}
    """).fetchone()
    return r[0] or []

with st.spinner("Cargando filtros..."):
    estados_list = opciones_estados(cliente_id, fecha_ini, fecha_fin)

estado_sel = st.sidebar.selectbox("Estado", ["Todos"] + [e for e in estados_list if e])

municipios_list = opciones_municipios(cliente_id, fecha_ini, fecha_fin, estado_sel)
municipio_sel   = st.sidebar.selectbox("Municipio", ["Todos"] + [m for m in municipios_list if m])

cadenas_list = opciones_cadenas(cliente_id, fecha_ini, fecha_fin, estado_sel, municipio_sel)
cadena_sel   = st.sidebar.selectbox("Cadena", ["Todos"] + [c for c in cadenas_list if c])

rutas_list = opciones_rutas(cliente_id, fecha_ini, fecha_fin, estado_sel, municipio_sel)
ruta_sel   = st.sidebar.selectbox("Ruta", ["Todos"] + [r for r in rutas_list if r])

umbral_amarillo = st.sidebar.slider("Umbral alerta (m)",  100,  1000,  300, step=50)
umbral_rojo     = st.sidebar.slider("Umbral crítico (m)", 500, 20000, 1000, step=500)

if st.sidebar.button("🗺️ Cargar mapa", type="primary", use_container_width=True):
    st.session_state["mapa_cargado"]    = True
    st.session_state["mapa_cliente_id"] = cliente_id
    st.session_state["mapa_fecha_ini"]  = fecha_ini
    st.session_state["mapa_fecha_fin"]  = fecha_fin
    st.session_state["mapa_estado"]     = estado_sel
    st.session_state["mapa_municipio"]  = municipio_sel
    st.session_state["mapa_cadena"]     = cadena_sel
    st.session_state["mapa_ruta"]       = ruta_sel

# ─────────────────────────────────────────
# RENDER
# ─────────────────────────────────────────
st.title("📍 Monitor Geolocalización")
st.caption(f"{cliente_sel}  ·  {fecha_ini} — {fecha_fin}"
           + (f"  ·  {estado_sel}"   if estado_sel   != "Todos" else "")
           + (f"  ·  {municipio_sel}" if municipio_sel != "Todos" else ""))

if not st.session_state.get("mapa_cargado"):
    st.info("Selecciona los filtros en el sidebar y haz click en **Cargar mapa**.")
    st.stop()

st.divider()

# ─────────────────────────────────────────
# QUERY PRINCIPAL
# ─────────────────────────────────────────
def filtro_where(fecha_ini, fecha_fin, estado_sel, municipio_sel, cadena_sel, ruta_sel):
    conds = [f"dia BETWEEN '{fecha_ini}' AND '{fecha_fin}'"]
    if estado_sel    != "Todos": conds.append(f"estado = '{estado_sel}'")
    if municipio_sel != "Todos": conds.append(f"municipio = '{municipio_sel}'")
    if cadena_sel    != "Todos": conds.append(f"cadena = '{cadena_sel}'")
    if ruta_sel      != "Todos": conds.append(f"ruta = '{ruta_sel}'")
    return " AND ".join(conds)

@st.cache_data(ttl=300)
def cargar_visitas(cliente_id, fecha_ini, fecha_fin,
                   estado_sel, municipio_sel, cadena_sel, ruta_sel):
    where = filtro_where(fecha_ini, fecha_fin,
                         estado_sel, municipio_sel, cadena_sel, ruta_sel)
    return con.execute(f"""
        SELECT
            g.usuario_id,
            u.user_real_name                                    AS promotor,
            g.dia                                               AS fecha,
            g.punto_venta_id,
            g.sucursal                                          AS punto_venta,
            g.cadena,
            g.estado,
            g.municipio,
            g.ruta,
            g.lat_pdv,
            g.lon_pdv,
            g.lat_checkin                                       AS lat_promotor,
            g.lon_checkin                                       AS lon_promotor,
            g.es_fuera_ruta,
            ROUND(111320 * SQRT(
                POWER(g.lat_checkin - g.lat_pdv, 2) +
                POWER((g.lon_checkin - g.lon_pdv)
                    * COS(RADIANS(g.lat_pdv)), 2)
            ), 0)                                               AS distancia_metros
        FROM geo g
        LEFT JOIN usuario u ON u.id = g.usuario_id
        WHERE {where}
    """).df()

with st.spinner("Cargando datos..."):
    df = cargar_visitas(
        st.session_state["mapa_cliente_id"],
        st.session_state["mapa_fecha_ini"],
        st.session_state["mapa_fecha_fin"],
        st.session_state["mapa_estado"],
        st.session_state["mapa_municipio"],
        st.session_state["mapa_cadena"],
        st.session_state["mapa_ruta"],
    )

if df.empty:
    st.warning("Sin datos para los filtros seleccionados.")
    st.stop()

# ── Clasificar distancias ─────────────────
def clasificar(d):
    if pd.isna(d):               return "Sin dato"
    if d <= umbral_amarillo:     return "En rango"
    if d <= umbral_rojo:         return "Alerta"
    return "Crítico"

df["estado_geo"] = df["distancia_metros"].apply(clasificar)

# ── KPIs ──────────────────────────────────
total        = len(df)
en_rango     = (df["estado_geo"] == "En rango").sum()
alerta       = (df["estado_geo"] == "Alerta").sum()
critico      = (df["estado_geo"] == "Crítico").sum()
pct_en_rango = round(en_rango / total * 100, 1) if total else 0

col1, col2, col3, col4, col5 = st.columns(5)
metric_card(col1, "Total visitas geo", f"{total:,}")
metric_card(col2, "En rango",          f"{en_rango:,}",    "#22C55E")
metric_card(col3, "% en rango",        f"{pct_en_rango}%", "#22C55E")
metric_card(col4, "Alerta",            f"{alerta:,}",      "#F59E0B")
metric_card(col5, "Crítico",           f"{critico:,}",     "#EF4444")

st.divider()

# ── MAPA ──────────────────────────────────
st.markdown('<p class="section-title">Mapa de visitas</p>', unsafe_allow_html=True)

df_mapa = df.dropna(subset=["lat_pdv", "lon_pdv"]).copy()

if not df_mapa.empty:
    color_map = {"En rango": "green", "Alerta": "orange",
                 "Crítico": "red",    "Sin dato": "gray"}

    centro_lat = df_mapa["lat_pdv"].median()
    centro_lon = df_mapa["lon_pdv"].median()
    mapa = folium.Map(location=[centro_lat, centro_lon],
                      zoom_start=10, tiles="CartoDB positron")

    for _, row in df_mapa.iterrows():
        folium.CircleMarker(
            location=[row["lat_pdv"], row["lon_pdv"]],
            radius=6,
            color=color_map.get(row["estado_geo"], "gray"),
            fill=True, fill_opacity=0.7,
            popup=folium.Popup(
                f"<b>{row['punto_venta']}</b><br>"
                f"Promotor: {row['promotor']}<br>"
                f"Fecha: {row['fecha']}<br>"
                f"Distancia: {int(row['distancia_metros']) if pd.notna(row['distancia_metros']) else 0:,} m<br>"
                f"Estado: {row['estado_geo']}",
                max_width=250
            )
        ).add_to(mapa)

    st_folium(mapa, width="stretch", height=500)
else:
    st.info(f"Sin coordenadas de PDV para mostrar en el mapa.")
    st.caption(f"Total visitas cargadas: {total:,} · Con coordenadas PDV: {len(df_mapa):,}")

st.divider()

# ── ANÁLISIS ──────────────────────────────
st.markdown('<p class="section-title">Análisis de anomalías</p>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["Por promotor", "Por ruta", "Detalle críticos"])

with tab1:
    df_prom = df.groupby("promotor").agg(
        visitas      =("usuario_id",       "count"),
        criticas     =("estado_geo", lambda x: (x=="Crítico").sum()),
        alertas      =("estado_geo", lambda x: (x=="Alerta").sum()),
        dist_promedio=("distancia_metros", "mean")
    ).reset_index()
    df_prom["pct_anomalas"] = round(
        (df_prom["criticas"] + df_prom["alertas"]) / df_prom["visitas"] * 100, 1
    )
    df_prom = df_prom.sort_values("criticas", ascending=False)
    fig = px.bar(df_prom.head(15), x="promotor", y=["criticas", "alertas"],
                 color_discrete_map={"criticas":"#EF4444", "alertas":"#F59E0B"},
                 barmode="stack", height=380)
    fig.update_layout(xaxis_title="", yaxis_title="Visitas", xaxis_tickangle=-35)
    st.plotly_chart(fig, width="stretch")

with tab2:
    df_ruta = df.groupby("ruta").agg(
        visitas =("usuario_id", "count"),
        criticas=("estado_geo", lambda x: (x=="Crítico").sum()),
        alertas =("estado_geo", lambda x: (x=="Alerta").sum()),
    ).reset_index()
    df_ruta = df_ruta.sort_values("criticas", ascending=False)
    fig = px.bar(df_ruta.head(15), x="ruta", y=["criticas", "alertas"],
                 color_discrete_map={"criticas":"#EF4444", "alertas":"#F59E0B"},
                 barmode="stack", height=380)
    fig.update_layout(xaxis_title="", yaxis_title="Visitas", xaxis_tickangle=-35)
    st.plotly_chart(fig, width="stretch")

with tab3:
    df_crit = df[df["estado_geo"].isin(["Crítico", "Alerta"])].copy()
    df_crit = df_crit.sort_values("distancia_metros", ascending=False)
    df_crit["distancia_metros"] = df_crit["distancia_metros"].apply(
        lambda x: f"{int(x):,} m" if pd.notna(x) else "—"
    )
    st.dataframe(
        df_crit[["fecha", "promotor", "ruta", "punto_venta",
                 "cadena", "estado", "municipio", "distancia_metros", "estado_geo"]],
        hide_index=True, width="stretch"
    )

st.divider()

# ── LISTADO DETALLADO ─────────────────────
st.markdown('<p class="section-title">Listado detallado de visitas</p>',
            unsafe_allow_html=True)

@st.cache_data(ttl=300)
def detalle_visitas(cliente_id, fecha_ini, fecha_fin,
                    estado_sel, municipio_sel, cadena_sel, ruta_sel):
    where = filtro_where(fecha_ini, fecha_fin,
                         estado_sel, municipio_sel, cadena_sel, ruta_sel)
    return con.execute(f"""
        SELECT
            g.dia                                               AS fecha,
            u.user_real_name                                    AS promotor,
            g.ruta,
            g.estado,
            g.municipio,
            g.sucursal                                          AS punto_venta,
            g.cadena,
            STRFTIME(g.hora_checkin, '%H:%M')                   AS hora_checkin,
            ROUND(111320 * SQRT(
                POWER(g.lat_checkin - g.lat_pdv, 2) +
                POWER((g.lon_checkin - g.lon_pdv)
                    * COS(RADIANS(g.lat_pdv)), 2)
            ), 0)                                               AS distancia_metros,
            CASE
                WHEN ROUND(111320 * SQRT(
                    POWER(g.lat_checkin - g.lat_pdv, 2) +
                    POWER((g.lon_checkin - g.lon_pdv)
                        * COS(RADIANS(g.lat_pdv)), 2)
                ), 0) <= {umbral_amarillo} THEN 'En rango'
                WHEN ROUND(111320 * SQRT(
                    POWER(g.lat_checkin - g.lat_pdv, 2) +
                    POWER((g.lon_checkin - g.lon_pdv)
                        * COS(RADIANS(g.lat_pdv)), 2)
                ), 0) <= {umbral_rojo} THEN 'Alerta'
                ELSE 'Crítico'
            END                                                 AS estado_geo,
            g.es_fuera_ruta
        FROM geo g
        LEFT JOIN usuario u ON u.id = g.usuario_id
        WHERE {where}
        ORDER BY g.dia DESC, u.user_real_name
    """).df()

col1, col2, col3 = st.columns(3)
solo_anomalos = col1.checkbox("Solo alertas y críticos", value=False)
exportar      = col2.button("📥 Exportar Excel")

with st.spinner("Cargando listado..."):
    df_det = detalle_visitas(
        st.session_state["mapa_cliente_id"],
        st.session_state["mapa_fecha_ini"],
        st.session_state["mapa_fecha_fin"],
        st.session_state["mapa_estado"],
        st.session_state["mapa_municipio"],
        st.session_state["mapa_cadena"],
        st.session_state["mapa_ruta"],
    )

if solo_anomalos:
    df_det = df_det[df_det["estado_geo"].isin(["Alerta", "Crítico"])]

col3.markdown(f"**{len(df_det):,}** visitas")

st.dataframe(
    df_det.rename(columns={
        "fecha":           "Fecha",
        "promotor":        "Promotor",
        "ruta":            "Ruta",
        "estado":          "Estado",
        "municipio":       "Municipio",
        "punto_venta":     "Punto de venta",
        "cadena":          "Cadena",
        "hora_checkin":    "Hora check-in",
        "distancia_metros":"Distancia (m)",
        "estado_geo":      "Estatus",
        "es_fuera_ruta":   "Fuera de ruta",
    }),
    hide_index=True,
    width="stretch",
    column_config={
        "Estatus":       st.column_config.TextColumn(width="small"),
        "Distancia (m)": st.column_config.NumberColumn(width="small"),
        "Fuera de ruta": st.column_config.NumberColumn(width="small"),
    }
)

if exportar:
    buffer = io.BytesIO()
    df_det.to_excel(buffer, index=False)
    buffer.seek(0)
    st.download_button(
        "⬇️ Descargar Excel",
        data=buffer,
        file_name=f"geo_{cliente_sel}_{fecha_ini}_{fecha_fin}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )