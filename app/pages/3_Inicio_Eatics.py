import path_setup
import path_setup
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import duckdb
from datetime import date
from config import parquet

# ─────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Eatics — Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .metric-card {
        background: #ffffff;
        border: 1px solid #E2E4E9;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }
    .metric-value { font-size: 2rem; font-weight: 700; margin: 0; }
    .metric-label { font-size: 0.75rem; color: #6B7280; text-transform: uppercase;
                    letter-spacing: 0.08em; margin: 0; }
    .section-title { font-size: 1.1rem; font-weight: 600; color: #1A1D23;
                     border-left: 4px solid #0057FF; padding-left: 10px; margin-bottom: 16px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# CONEXIÓN DUCKDB
# ─────────────────────────────────────────
@st.cache_resource
def get_con():
    con = duckdb.connect()
    con.execute(f"CREATE OR REPLACE VIEW v_reporte_marca_pdv  AS SELECT * FROM read_parquet('{parquet('reporte_marca_pdv')}')")
    con.execute(f"CREATE OR REPLACE VIEW v_detalle_venta_cero AS SELECT * FROM read_parquet('{parquet('venta_cero')}')")
    con.execute(f"CREATE OR REPLACE VIEW v_precios_eatics     AS SELECT * FROM read_parquet('{parquet('precios_eatics')}')")
    return con

con = get_con()

# ─────────────────────────────────────────
# CARGA DE DATOS
# ─────────────────────────────────────────
@st.cache_data(ttl=300)
def cargar_ejecucion(fecha_ini, fecha_fin, marca, cadena):
    filtros = f"fecha >= '{fecha_ini}' AND fecha <= '{fecha_fin}'"
    if marca != "Todas":
        filtros += f" AND marca = '{marca}'"
    if cadena != "Todas":
        filtros += f" AND cadena = '{cadena}'"
    return con.execute(f"""
        SELECT cadena, punto_venta, municipio, estado, marca,
               SUM(total_visitas)           AS visitas,
               SUM(cant_sku)                AS sku,
               SUM(cumple_planograma)        AS planograma,
               SUM(visitas_con_agotados)     AS vis_agotados,
               SUM(cant_sku_agotados)        AS sku_agotados,
               SUM(visitas_con_preagotados)  AS vis_preagotados,
               SUM(cant_sku_preagotados)     AS sku_preagotados
        FROM v_reporte_marca_pdv
        WHERE {filtros}
        GROUP BY cadena, punto_venta, municipio, estado, marca
        ORDER BY cadena, punto_venta, marca
        LIMIT 2000
    """).df()

@st.cache_data(ttl=300)
def cargar_venta_cero(fecha_ini, fecha_fin, marca):
    filtros = f"fecha >= '{fecha_ini}' AND fecha <= '{fecha_fin}'"
    if marca != "Todas":
        filtros += f" AND marca = '{marca}'"
    return con.execute(f"""
        SELECT marca, producto, cadena, punto_venta, estado,
               inventario, ejecutada, fecha, promotor
        FROM v_detalle_venta_cero
        WHERE {filtros}
        ORDER BY marca, producto
        LIMIT 1000
    """).df()

@st.cache_data(ttl=300)
def cargar_precios(fecha_ini, fecha_fin, cadena):
    filtros = f"fecha >= '{fecha_ini}' AND fecha <= '{fecha_fin}'"
    if cadena != "Todas":
        filtros += f" AND cadena = '{cadena}'"
    df = con.execute(f"""
        SELECT producto, categoria, cadena, precio,
               CAST(is_propio AS INTEGER) AS is_propio,
               fecha, promotor
        FROM v_precios_eatics
        WHERE {filtros}
        ORDER BY producto, cadena
        LIMIT 2000
    """).df()
    df["tipo"] = df["is_propio"].apply(lambda x: "Propio" if int(x or 0) == 1 else "Competencia")
    return df

@st.cache_data(ttl=600)
def cargar_filtros():
    marcas  = con.execute("SELECT DISTINCT marca  FROM v_reporte_marca_pdv WHERE marca  IS NOT NULL ORDER BY marca").df()
    cadenas = con.execute("SELECT DISTINCT cadena FROM v_reporte_marca_pdv WHERE cadena IS NOT NULL ORDER BY cadena").df()
    return ["Todas"] + marcas["marca"].tolist(), ["Todas"] + cadenas["cadena"].tolist()

# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 Eatics Dashboard")
    st.markdown("---")
    hoy = date.today()
    fecha_ini = st.date_input("Fecha inicio", value=hoy.replace(day=1))
    fecha_fin = st.date_input("Fecha fin",    value=hoy)
    marcas_opts, cadenas_opts = cargar_filtros()
    marca_sel  = st.selectbox("Marca",  marcas_opts)
    cadena_sel = st.selectbox("Cadena", cadenas_opts)
    st.markdown("---")
    st.caption(f"GKMobile · Eatics · {hoy.year}")

fi, ff = str(fecha_ini), str(fecha_fin)

# ─────────────────────────────────────────
# TÍTULO
# ─────────────────────────────────────────
st.title("Dashboard Eatics")
st.caption(f"Periodo: {fi}  →  {ff}  |  Marca: {marca_sel}  |  Cadena: {cadena_sel}")

# ─────────────────────────────────────────
# CARGA
# ─────────────────────────────────────────
with st.spinner("Cargando datos..."):
    df_ejec = cargar_ejecucion(fi, ff, marca_sel, cadena_sel)
    df_cero = cargar_venta_cero(fi, ff, marca_sel)
    df_prec = cargar_precios(fi, ff, cadena_sel)

if df_ejec.empty:
    st.warning("Sin datos para el periodo y filtros seleccionados.")
    st.stop()

# ─────────────────────────────────────────
# KPIs GENERALES
# ─────────────────────────────────────────
st.markdown('<p class="section-title">KPIs generales</p>', unsafe_allow_html=True)

total_visitas     = int(df_ejec["visitas"].sum())
total_sku         = int(df_ejec["sku"].sum())
total_agotados    = int(df_ejec["sku_agotados"].sum())
total_preagotados = int(df_ejec["sku_preagotados"].sum())
pdvs_unicos       = df_ejec["punto_venta"].nunique()
pct_agotados      = round(total_agotados / total_sku * 100, 1) if total_sku else 0
pct_preagotados   = round(total_preagotados / total_sku * 100, 1) if total_sku else 0
pct_planograma    = round(df_ejec["planograma"].sum() / total_visitas * 100, 1) if total_visitas else 0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("PDVs visitados",    f"{pdvs_unicos:,}")
col2.metric("Total visitas",     f"{total_visitas:,}")
col3.metric("% Planograma",      f"{pct_planograma}%")
col4.metric("% SKU agotados",    f"{pct_agotados}%",    delta=f"{total_agotados:,} SKUs",    delta_color="inverse")
col5.metric("% SKU preagotados", f"{pct_preagotados}%", delta=f"{total_preagotados:,} SKUs", delta_color="inverse")

st.divider()

# ─────────────────────────────────────────
# EJECUCIÓN POR MARCA Y PDV
# ─────────────────────────────────────────
st.markdown('<p class="section-title">Ejecución por marca y PDV</p>', unsafe_allow_html=True)

col_a, col_b = st.columns(2)

with col_a:
    df_marca = df_ejec.groupby("marca")["visitas"].sum().reset_index().sort_values("visitas", ascending=True)
    fig1 = px.bar(df_marca, x="visitas", y="marca", orientation="h",
                  title="Visitas por marca", color="marca",
                  color_discrete_sequence=["#0057FF","#0D9488","#E55B4D","#D97706"])
    fig1.update_layout(showlegend=False, height=300, margin=dict(l=0,r=0,t=40,b=0),
                       plot_bgcolor="white", paper_bgcolor="white")
    fig1.update_xaxes(showgrid=True, gridcolor="#F4F5F7")
    st.plotly_chart(fig1, use_container_width=True)

with col_b:
    df_plan = df_ejec.groupby("marca").agg(planograma=("planograma","sum"), visitas=("visitas","sum")).reset_index()
    df_plan["pct"] = (df_plan["planograma"] / df_plan["visitas"] * 100).round(1)
    fig2 = px.bar(df_plan, x="marca", y="pct", title="% Cumplimiento planograma por marca",
                  color="marca", color_discrete_sequence=["#0057FF","#0D9488","#E55B4D","#D97706"], text="pct")
    fig2.update_traces(texttemplate="%{text}%", textposition="outside")
    fig2.update_layout(showlegend=False, height=300, margin=dict(l=0,r=0,t=40,b=0),
                       plot_bgcolor="white", paper_bgcolor="white", yaxis_range=[0,110])
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("**Top 10 PDVs por visitas**")
top_pdv = df_ejec.groupby(["cadena","punto_venta","estado"])["visitas"].sum().reset_index().sort_values("visitas", ascending=False).head(10)
fig3 = px.bar(top_pdv, x="visitas", y="punto_venta", orientation="h", color="cadena",
              color_discrete_sequence=px.colors.qualitative.Set2)
fig3.update_layout(height=320, margin=dict(l=0,r=0,t=10,b=0),
                   plot_bgcolor="white", paper_bgcolor="white",
                   legend=dict(orientation="h", yanchor="bottom", y=1.02))
st.plotly_chart(fig3, use_container_width=True)

st.divider()

# ─────────────────────────────────────────
# AGOTADOS Y PREAGOTADOS
# ─────────────────────────────────────────
st.markdown('<p class="section-title">Agotados y preagotados</p>', unsafe_allow_html=True)

col_c, col_d = st.columns(2)

with col_c:
    df_agot = df_ejec.groupby("marca").agg(
        sku_agotados=("sku_agotados","sum"), sku_preagotados=("sku_preagotados","sum"), sku=("sku","sum")
    ).reset_index()
    df_agot["pct_agotados"]    = (df_agot["sku_agotados"]    / df_agot["sku"] * 100).round(1)
    df_agot["pct_preagotados"] = (df_agot["sku_preagotados"] / df_agot["sku"] * 100).round(1)
    df_melt = df_agot.melt(id_vars="marca", value_vars=["pct_agotados","pct_preagotados"], var_name="tipo", value_name="pct")
    df_melt["tipo"] = df_melt["tipo"].map({"pct_agotados":"Agotados","pct_preagotados":"Preagotados"})
    fig4 = px.bar(df_melt, x="marca", y="pct", color="tipo", barmode="group",
                  title="% SKU agotados y preagotados por marca",
                  color_discrete_map={"Agotados":"#E55B4D","Preagotados":"#D97706"}, text="pct")
    fig4.update_traces(texttemplate="%{text}%", textposition="outside")
    fig4.update_layout(height=320, margin=dict(l=0,r=0,t=40,b=0),
                       plot_bgcolor="white", paper_bgcolor="white", legend=dict(title=""))
    st.plotly_chart(fig4, use_container_width=True)

with col_d:
    top_agot = df_ejec.groupby("punto_venta")["sku_agotados"].sum().reset_index().sort_values("sku_agotados", ascending=False).head(10)
    fig5 = px.bar(top_agot, x="sku_agotados", y="punto_venta", orientation="h",
                  title="Top 10 PDVs con más SKU agotados", color_discrete_sequence=["#E55B4D"])
    fig5.update_layout(height=320, showlegend=False, margin=dict(l=0,r=0,t=40,b=0),
                       plot_bgcolor="white", paper_bgcolor="white")
    st.plotly_chart(fig5, use_container_width=True)

if not df_cero.empty:
    st.markdown("**Productos con venta cero**")
    col_e, col_f = st.columns(2)
    with col_e:
        ejec_counts = df_cero["ejecutada"].value_counts()
        fig6 = go.Figure(go.Pie(
            labels=["Ejecutada","Pendiente"],
            values=[ejec_counts.get(1,0), ejec_counts.get(0,0)],
            hole=0.55, marker_colors=["#0D9488","#E55B4D"]
        ))
        fig6.update_layout(title="Estatus ejecución — venta cero", height=280,
                           margin=dict(l=0,r=0,t=40,b=0), paper_bgcolor="white")
        st.plotly_chart(fig6, use_container_width=True)
    with col_f:
        df_cero_marca = df_cero.groupby("marca").size().reset_index(name="registros")
        fig7 = px.bar(df_cero_marca, x="marca", y="registros", title="Registros venta cero por marca",
                      color="marca", color_discrete_sequence=["#0057FF","#0D9488","#E55B4D","#D97706","#888780"])
        fig7.update_layout(showlegend=False, height=280, margin=dict(l=0,r=0,t=40,b=0),
                           plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig7, use_container_width=True)

st.divider()

# ─────────────────────────────────────────
# PRECIOS
# ─────────────────────────────────────────
st.markdown('<p class="section-title">Precios — propio vs competencia</p>', unsafe_allow_html=True)

if not df_prec.empty:
    col_g, col_h = st.columns(2)
    with col_g:
        df_tipo = df_prec.groupby("tipo")["precio"].mean().reset_index()
        df_tipo["precio"] = df_tipo["precio"].round(2)
        fig8 = px.bar(df_tipo, x="tipo", y="precio", title="Precio promedio — propio vs competencia",
                      color="tipo", color_discrete_map={"Propio":"#0D9488","Competencia":"#D97706"}, text="precio")
        fig8.update_traces(texttemplate="$%{text:.2f}", textposition="outside")
        fig8.update_layout(showlegend=False, height=300, margin=dict(l=0,r=0,t=40,b=0),
                           plot_bgcolor="white", paper_bgcolor="white",
                           yaxis_range=[0, df_tipo["precio"].max()*1.2])
        st.plotly_chart(fig8, use_container_width=True)
    with col_h:
        fig9 = px.box(df_prec[df_prec["precio"].notna()], x="tipo", y="precio",
                      title="Distribución de precios", color="tipo",
                      color_discrete_map={"Propio":"#0D9488","Competencia":"#D97706"})
        fig9.update_layout(showlegend=False, height=300, margin=dict(l=0,r=0,t=40,b=0),
                           plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig9, use_container_width=True)

    df_cat = df_prec[df_prec["categoria"].notna()].groupby(["categoria","tipo"])["precio"].mean().round(2).reset_index()
    if not df_cat.empty:
        fig10 = px.bar(df_cat, x="categoria", y="precio", color="tipo", barmode="group",
                       title="Precio promedio por categoría",
                       color_discrete_map={"Propio":"#0D9488","Competencia":"#D97706"}, text="precio")
        fig10.update_traces(texttemplate="$%{text:.2f}", textposition="outside")
        fig10.update_layout(height=320, margin=dict(l=0,r=0,t=40,b=0),
                            plot_bgcolor="white", paper_bgcolor="white", legend=dict(title=""))
        st.plotly_chart(fig10, use_container_width=True)

st.divider()

# ─────────────────────────────────────────
# TABLA DETALLADA
# ─────────────────────────────────────────
with st.expander("Ver datos detallados de ejecución"):
    df_tabla = df_ejec.copy()
    df_tabla["% planograma"]  = (df_tabla["planograma"]      / df_tabla["visitas"] * 100).round(1)
    df_tabla["% agotados"]    = (df_tabla["sku_agotados"]    / df_tabla["sku"]     * 100).round(1)
    df_tabla["% preagotados"] = (df_tabla["sku_preagotados"] / df_tabla["sku"]     * 100).round(1)
    st.dataframe(
        df_tabla[["cadena","punto_venta","estado","marca","visitas","sku",
                  "% planograma","sku_agotados","% agotados","sku_preagotados","% preagotados"]],
        use_container_width=True, hide_index=True
    )
