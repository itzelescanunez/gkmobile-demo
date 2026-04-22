import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
from config import parquet
import io

st.set_page_config(page_title="Procesa — Sell Out", layout="wide")

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
                     border-left: 4px solid #0057FF; padding-left: 10px;
                     margin-bottom: 16px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# CONEXIÓN
# ─────────────────────────────────────────
@st.cache_resource
def get_con():
    con = duckdb.connect()
    con.execute(f"CREATE OR REPLACE VIEW sell_out    AS SELECT * FROM read_parquet('{parquet('detalle_sell_out_procesa', 'procesa')}')")
    con.execute(f"CREATE OR REPLACE VIEW inventario  AS SELECT * FROM read_parquet('{parquet('detalle_inventario_procesa', 'procesa')}')")
    con.execute(f"CREATE OR REPLACE VIEW producto    AS SELECT * FROM read_parquet('{parquet('producto_procesa', 'procesa')}')")
    con.execute(f"CREATE OR REPLACE VIEW canal       AS SELECT * FROM read_parquet('{parquet('canal_procesa', 'procesa')}')")
    con.execute(f"CREATE OR REPLACE VIEW punto_venta AS SELECT * FROM read_parquet('{parquet('punto_venta', 'global')}')")
    return con

con = get_con()

# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────
st.sidebar.title("Procesa — Sell Out")

CLIENTES_PROCESA = {"Procesa": 26, "Procesa Mayoreo": 138}
cliente_sel = st.sidebar.selectbox("Cliente", list(CLIENTES_PROCESA.keys()))
cliente_id  = CLIENTES_PROCESA[cliente_sel]

@st.cache_data(ttl=600)
def ultimo_mes_datos(cliente_id):
    row = con.execute("""
                      SELECT MAX(CAST(fecha AS DATE))
                      FROM sell_out WHERE cliente_id = ?
                      """, [cliente_id]).fetchone()
    return row[0] if row[0] else date.today()

ultima     = ultimo_mes_datos(cliente_id)
inicio_def = ultima.replace(day=1)
fecha_ini  = st.sidebar.date_input("Fecha inicio", inicio_def)
fecha_fin  = st.sidebar.date_input("Fecha fin", ultima)

@st.cache_data(ttl=600)
def cargar_canales(cliente_id):
    return con.execute("""
                       SELECT DISTINCT c.nombre
                       FROM sell_out s
                                JOIN canal c ON c.id = s.canal_id
                       WHERE s.cliente_id = ?
                       ORDER BY c.nombre
                       """, [cliente_id]).df()

df_canales   = cargar_canales(cliente_id)
canales_disp = ["Todos"] + df_canales["nombre"].tolist()
canal_sel    = st.sidebar.selectbox("Canal", canales_disp)

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def filtro_canal(alias="s"):
    if canal_sel == "Todos":
        return ""
    return f"AND EXISTS (SELECT 1 FROM canal c WHERE c.id = {alias}.canal_id AND c.nombre = '{canal_sel}')"

def metric_card(col, label, value, color="#1A1D23"):
    col.markdown(f"""
    <div class="metric-card">
        <p class="metric-label">{label}</p>
        <p class="metric-value" style="color:{color}">{value}</p>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────
# QUERIES
# ─────────────────────────────────────────
@st.cache_data(ttl=300)
def kpis_sellout(cliente_id, fecha_ini, fecha_fin, canal_sel):
    return con.execute(f"""
        SELECT
            ROUND(SUM(s.monto), 0)                                      AS monto_total,
            ROUND(SUM(s.piezas), 0)                                     AS piezas_total,
            COUNT(DISTINCT s.punto_venta_id)                            AS pdv_activos,
            COUNT(DISTINCT s.producto_id)                               AS productos_activos,
            ROUND(SUM(s.monto) /
                NULLIF(COUNT(DISTINCT s.punto_venta_id), 0), 0)         AS ticket_promedio_pdv
        FROM sell_out s
        WHERE s.cliente_id = ?
          AND CAST(s.fecha AS DATE) BETWEEN ? AND ?
          {filtro_canal()}
    """, [cliente_id, str(fecha_ini), str(fecha_fin)]).fetchone()

@st.cache_data(ttl=300)
def tendencia_mensual(cliente_id, fecha_ini, fecha_fin, canal_sel):
    return con.execute(f"""
        SELECT
            s.anio,
            s.mes,
            ROUND(SUM(s.monto), 0)           AS monto,
            ROUND(SUM(s.piezas), 0)          AS piezas,
            COUNT(DISTINCT s.punto_venta_id) AS pdv
        FROM sell_out s
        WHERE s.cliente_id = ?
          AND CAST(s.fecha AS DATE) BETWEEN ? AND ?
          {filtro_canal()}
        GROUP BY s.anio, s.mes
        ORDER BY s.anio, s.mes
    """, [cliente_id, str(fecha_ini), str(fecha_fin)]).df()

@st.cache_data(ttl=300)
def top_productos(cliente_id, fecha_ini, fecha_fin, canal_sel, top_n=15):
    return con.execute(f"""
        SELECT
            COALESCE(p.nombre, 'Sin nombre') AS producto,
            p.marca,
            p.sku,
            ROUND(SUM(s.monto), 0)           AS monto_total,
            ROUND(SUM(s.piezas), 0)          AS piezas_total,
            COUNT(DISTINCT s.punto_venta_id) AS pdv
        FROM sell_out s
        LEFT JOIN producto p ON p.id = s.producto_id
        WHERE s.cliente_id = ?
          AND CAST(s.fecha AS DATE) BETWEEN ? AND ?
          {filtro_canal()}
        GROUP BY p.nombre, p.marca, p.sku
        ORDER BY monto_total DESC
        LIMIT {top_n}
    """, [cliente_id, str(fecha_ini), str(fecha_fin)]).df()

@st.cache_data(ttl=300)
def top_cadenas(cliente_id, fecha_ini, fecha_fin, canal_sel, top_n=15):
    return con.execute(f"""
        SELECT
            COALESCE(pv.cadena_str, 'Sin cadena') AS cadena,
            ROUND(SUM(s.monto), 0)                AS monto_total,
            ROUND(SUM(s.piezas), 0)               AS piezas_total,
            COUNT(DISTINCT s.punto_venta_id)      AS pdv
        FROM sell_out s
        LEFT JOIN punto_venta pv ON pv.id = s.punto_venta_id
        WHERE s.cliente_id = ?
          AND CAST(s.fecha AS DATE) BETWEEN ? AND ?
          {filtro_canal()}
        GROUP BY pv.cadena_str
        ORDER BY monto_total DESC
        LIMIT {top_n}
    """, [cliente_id, str(fecha_ini), str(fecha_fin)]).df()

@st.cache_data(ttl=300)
def distribucion_canal(cliente_id, fecha_ini, fecha_fin):
    return con.execute("""
                       SELECT
                           COALESCE(c.nombre, 'Sin canal')      AS canal,
                           COALESCE(c.segmento, 'Sin segmento') AS segmento,
                           ROUND(SUM(s.monto), 0)               AS monto_total,
                           ROUND(SUM(s.piezas), 0)              AS piezas_total
                       FROM sell_out s
                                LEFT JOIN canal c ON c.id = s.canal_id
                       WHERE s.cliente_id = ?
                         AND CAST(s.fecha AS DATE) BETWEEN ? AND ?
                       GROUP BY c.nombre, c.segmento
                       ORDER BY monto_total DESC
                       """, [cliente_id, str(fecha_ini), str(fecha_fin)]).df()

@st.cache_data(ttl=300)
def comparativo_anual(cliente_id, mes_actual, canal_sel):
    return con.execute(f"""
        SELECT
            s.anio,
            ROUND(SUM(s.monto), 0)  AS monto,
            ROUND(SUM(s.piezas), 0) AS piezas
        FROM sell_out s
        WHERE s.cliente_id = ?
          AND s.mes = ?
          {filtro_canal()}
        GROUP BY s.anio
        ORDER BY s.anio
    """, [cliente_id, mes_actual]).df()

# ─────────────────────────────────────────
# RENDER
# ─────────────────────────────────────────
st.title("📦 Procesa — Sell Out")
st.caption(f"{cliente_sel}  ·  {fecha_ini} — {fecha_fin}"
           + (f"  ·  Canal: {canal_sel}" if canal_sel != "Todos" else ""))
st.divider()

with st.spinner("Cargando KPIs..."):
    kpis = kpis_sellout(cliente_id, fecha_ini, fecha_fin, canal_sel)

col1, col2, col3, col4, col5 = st.columns(5)
metric_card(col1, "Monto total",       f"${int(kpis[0] or 0):,}")
metric_card(col2, "Piezas vendidas",   f"{int(kpis[1] or 0):,}")
metric_card(col3, "PDV activos",       f"{int(kpis[2] or 0):,}")
metric_card(col4, "Productos activos", f"{int(kpis[3] or 0):,}")
metric_card(col5, "Ticket prom/PDV",   f"${int(kpis[4] or 0):,}")

st.divider()

# ── TENDENCIA ─────────────────────────────
st.markdown('<p class="section-title">Tendencia mensual</p>', unsafe_allow_html=True)

with st.spinner("Cargando tendencia..."):
    df_tend = tendencia_mensual(cliente_id, fecha_ini, fecha_fin, canal_sel)

if not df_tend.empty:
    df_tend["periodo"] = (df_tend["anio"].astype(str) + "-" +
                          df_tend["mes"].astype(str).str.zfill(2))

    tab1, tab2, tab3 = st.tabs(["Monto", "Piezas", "PDV activos"])

    with tab1:
        fig = px.bar(df_tend, x="periodo", y="monto",
                     title="Venta mensual (monto)",
                     color_discrete_sequence=["#0057FF"])
        fig.update_layout(xaxis_title="", yaxis_title="$",
                          height=350, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        fig = px.bar(df_tend, x="periodo", y="piezas",
                     title="Venta mensual (piezas)",
                     color_discrete_sequence=["#7C3AED"])
        fig.update_layout(xaxis_title="", yaxis_title="Piezas",
                          height=350, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        fig = px.line(df_tend, x="periodo", y="pdv",
                      markers=True, title="PDV activos por mes")
        fig.update_traces(line_color="#0057FF")
        fig.update_layout(xaxis_title="", yaxis_title="PDV",
                          height=350, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── PRODUCTOS Y CADENAS ───────────────────
st.markdown('<p class="section-title">Ranking</p>', unsafe_allow_html=True)

with st.spinner("Cargando rankings..."):
    df_prod   = top_productos(cliente_id, fecha_ini, fecha_fin, canal_sel)
    df_cadena = top_cadenas(cliente_id, fecha_ini, fecha_fin, canal_sel)
    df_canal  = distribucion_canal(cliente_id, fecha_ini, fecha_fin)

col1, col2 = st.columns(2)

with col1:
    fig = px.bar(df_prod, x="monto_total", y="producto",
                 orientation="h", title="Top productos por monto",
                 color_discrete_sequence=["#0057FF"])
    fig.update_layout(xaxis_title="$", yaxis_title="",
                      height=420, yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = px.bar(df_cadena, x="monto_total", y="cadena",
                 orientation="h", title="Top cadenas por monto",
                 color_discrete_sequence=["#7C3AED"])
    fig.update_layout(xaxis_title="$", yaxis_title="",
                      height=420, yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── DISTRIBUCIÓN CANAL ────────────────────
st.markdown('<p class="section-title">Distribución por canal</p>',
            unsafe_allow_html=True)

if not df_canal.empty:
    col1, col2 = st.columns(2)

    with col1:
        fig = go.Figure(go.Pie(
            labels=df_canal["canal"],
            values=df_canal["monto_total"],
            hole=0.5,
            textinfo="label+percent"
        ))
        fig.update_layout(title="Por canal (monto)", height=350,
                          showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(df_canal, x="canal", y=["monto_total", "piezas_total"],
                     barmode="group", title="Monto vs Piezas por canal")
        fig.update_layout(xaxis_title="", height=350)
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── COMPARATIVO ANUAL ─────────────────────
st.markdown('<p class="section-title">Comparativo mismo mes — histórico</p>',
            unsafe_allow_html=True)

with st.spinner("Cargando comparativo..."):
    df_comp = comparativo_anual(cliente_id, fecha_ini.month, canal_sel)

if not df_comp.empty:
    fig = px.bar(df_comp, x="anio", y="monto",
                 title=f"Venta mes {fecha_ini.month} por año",
                 color_discrete_sequence=["#0057FF"],
                 text="monto")
    fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
    fig.update_layout(xaxis_title="Año", yaxis_title="$", height=350)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── EXPORTAR ──────────────────────────────
st.markdown('<p class="section-title">Exportar datos</p>',
            unsafe_allow_html=True)

if st.button("📥 Generar Excel"):
    with st.spinner("Generando archivo..."):
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            pd.DataFrame([{
                "Monto total":        int(kpis[0] or 0),
                "Piezas vendidas":    int(kpis[1] or 0),
                "PDV activos":        int(kpis[2] or 0),
                "Productos activos":  int(kpis[3] or 0),
                "Ticket prom/PDV":    int(kpis[4] or 0),
            }]).to_excel(writer, sheet_name="KPIs",      index=False)
            df_tend.to_excel(writer,   sheet_name="Tendencia",        index=False)
            df_prod.to_excel(writer,   sheet_name="Productos",        index=False)
            df_cadena.to_excel(writer, sheet_name="Cadenas",          index=False)
            df_canal.to_excel(writer,  sheet_name="Canales",          index=False)
            df_comp.to_excel(writer,   sheet_name="Comparativo anual",index=False)
        buffer.seek(0)

    st.download_button(
        label="⬇️ Descargar Excel",
        data=buffer,
        file_name=f"procesa_sellout_{cliente_sel}_{fecha_ini}_{fecha_fin}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )