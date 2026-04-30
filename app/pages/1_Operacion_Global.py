
import pandas as pd
import streamlit as st
import duckdb
import io
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta
from config import parquet, CLIENTES


import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.path_setup import require_auth
require_auth()

INCIDENCIAS_MAP = {
    "SIN INCIDENCIAS": "Normal",
    "SIN INCIDENCIA": "Normal",
    "SIN INCIDENCIA.": "Normal",
    "OK": "Normal",
    "ASISTENCIA": "Normal",
    "FALTA": "Ausencia",
    "FALTA INJUSTIFICADA": "Ausencia",
    "BAJA": "Ausencia",
    "INCAPACIDAD": "Ausencia",
    "VACACIONES": "Ausencia",
    "VACANTE": "Ausencia",
    "SIN EQUIPO": "Operacional",
    "RETARDO": "Operacional",
    "SIN REPORTE AL CORTE": "Operacional",
    "SIN INFORMACION EN PLATAFORMA": "Operacional",
    "ESPERANDO ENVIO DE INFORMACION": "Operacional",
    "DESCANSO": "Descanso",
    "FESTIVO": "Descanso",
    "APOYO A RUTA FUERA DE PLAN": "Especial",
    "CHECK IN FUERA DE TIENDA": "Especial",
    # Extras
    "FI": "Ausencia",           # FALTA INJUSTIFICADA abreviada
    "FJ": "Ausencia",           # FALTA JUSTIFICADA abreviada
    "VACACNTE": "Ausencia",     # typo de VACANTE
    "INCAPACIAD": "Ausencia",   # typo de INCAPACIDAD
    "VACANTE ": "Ausencia",     # con espacio
    "FALTA ": "Ausencia",       # con espacio
    "DESCANSO ": "Descanso",    # con espacio
}

COLORES_INCIDENCIA = {
    "Normal":      "#22C55E",
    "Ausencia":    "#EF4444",
    "Operacional": "#F59E0B",
    "Descanso":    "#3B82F6",
    "Especial":    "#8B5CF6",
}

@st.cache_data(ttl=300)
def detalle_incidencias(cliente_id, fecha_ini, fecha_fin):
    return con.execute("""
                       SELECT
                           CAST(a.fecha_planeada AS DATE)     AS fecha,
                           u.user_real_name                    AS promotor,
                           u.username                          AS usuario,
                           COALESCE(c.ruta, 'Sin ruta')       AS ruta,
                           COALESCE(c.entidad, 'Sin entidad') AS entidad,
                           COALESCE(c.puesto, 'Sin puesto')   AS puesto,
                           j.incidencia                        AS incidencia_original,
                           UPPER(TRIM(j.incidencia))           AS incidencia_normalizada
                       FROM actividad_real a
                                LEFT JOIN usuario u   ON u.id = a.usuario_id
                                LEFT JOIN cuadrilla c ON c.id = a.cuadrilla_id
                                LEFT JOIN jornada j
                                          ON j.usuario_id = a.usuario_id
                                              AND CAST(j.fecha AS DATE) = CAST(a.fecha_planeada AS DATE)
                                              AND j.cliente_id = ?
                       WHERE a.cliente_id = ?
                         AND CAST(a.fecha_planeada AS DATE) BETWEEN ? AND ?
                         AND a.fecha_real_inicio IS NOT NULL
                         AND j.incidencia IS NOT NULL
                         AND TRIM(j.incidencia) != ''
                       ORDER BY a.fecha_planeada, u.user_real_name
                       """, [cliente_id, cliente_id, str(fecha_ini), str(fecha_fin)]).df()

@st.cache_data(ttl=300)
def detalle_jornada(cliente_id, fecha_ini, fecha_fin):
    return con.execute("""
                       SELECT
                           CAST(a.fecha_planeada AS DATE)             AS fecha,
                           u.user_real_name                            AS promotor,
                           u.username                                  AS usuario,
                           COALESCE(c.ruta, 'Sin ruta')               AS ruta,
                           COALESCE(c.entidad, 'Sin entidad')         AS entidad,
                           COALESCE(c.puesto, 'Sin puesto')           AS puesto,
                           TRY_CAST(MIN(a.fecha_real_inicio) AS TIMESTAMP) AS inicio_jornada,
                           TRY_CAST(MAX(a.fecha_real_final)  AS TIMESTAMP) AS fin_jornada,
                           ROUND(EPOCH(
                                         MAX(TRY_CAST(a.fecha_real_final AS TIMESTAMP)) -
                                         MIN(TRY_CAST(a.fecha_real_inicio AS TIMESTAMP))
                                 ) / 3600.0, 2)                             AS horas_trabajadas,
                           j.incidencia,
                           CASE WHEN UPPER(TRIM(j.incidencia))
                               IN ('FALTA','FALTA INJUSTIFICADA','BAJA','INCAPACIDAD',
                                   'VACACIONES','VACANTE','FI','FJ')
                                    THEN 'Sí' ELSE 'No'
                               END                                        AS es_ausencia
                       FROM actividad_real a
                                LEFT JOIN usuario u    ON u.id = a.usuario_id
                                LEFT JOIN cuadrilla c  ON c.id = a.cuadrilla_id
                                LEFT JOIN jornada j
                                          ON j.usuario_id = a.usuario_id
                                              AND CAST(j.fecha AS DATE) = CAST(a.fecha_planeada AS DATE)
                                              AND j.cliente_id = ?
                       WHERE a.cliente_id = ?
                         AND CAST(a.fecha_planeada AS DATE) BETWEEN ? AND ?
                         AND a.fecha_real_inicio IS NOT NULL
                       GROUP BY a.fecha_planeada, a.usuario_id, u.user_real_name, u.username,
                                c.ruta, c.entidad, c.puesto, j.incidencia
                       ORDER BY a.fecha_planeada, u.user_real_name
                       """, [cliente_id, cliente_id, str(fecha_ini), str(fecha_fin)]).df()


@st.cache_data(ttl=300)
def detalle_actividades(cliente_id, fecha_ini, fecha_fin):
    return con.execute("""
                       SELECT
                           CAST(a.fecha_planeada AS DATE)         AS fecha,
                           u.user_real_name                        AS promotor,
                           u.username                              AS usuario,
                           COALESCE(c.ruta, 'Sin ruta')            AS ruta,
                           COALESCE(c.entidad, 'Sin entidad')      AS entidad,
                           pv.sucursal                             AS punto_venta,
                           pv.cadena_str                           AS cadena,
                           pv.municipio_str                        AS municipio,
                           pv.estado_str                           AS estado,
                           TRY_CAST(a.fecha_real_inicio AS TIMESTAMP) AS hora_inicio,
                           TRY_CAST(a.fecha_real_final  AS TIMESTAMP) AS hora_fin,
                           ROUND(EPOCH(
                                         TRY_CAST(a.fecha_real_final AS TIMESTAMP) -
                                         TRY_CAST(a.fecha_real_inicio AS TIMESTAMP)
                                 ) / 60.0, 0)                            AS minutos_visita,
                           CASE WHEN a.is_no_planeada = 1
                                    THEN 'Fuera de ruta' ELSE 'En ruta'
                               END                                     AS tipo_visita,
                           CASE WHEN a.fecha_real_inicio IS NOT NULL
                                    THEN 'Ejecutada' ELSE 'No ejecutada'
                               END                                     AS estatus
                       FROM actividad_real a
                                LEFT JOIN usuario u    ON u.id = a.usuario_id
                                LEFT JOIN cuadrilla c  ON c.id = a.cuadrilla_id
                                LEFT JOIN punto_venta pv ON pv.id = a.punto_venta_id
                       WHERE a.cliente_id = ?
                         AND CAST(a.fecha_planeada AS DATE) BETWEEN ? AND ?
                       ORDER BY a.fecha_planeada, u.user_real_name
                       """, [cliente_id, str(fecha_ini), str(fecha_fin)]).df()


@st.cache_data(ttl=300)
def incidencias_resumen(cliente_id, fecha_ini, fecha_fin):
    return con.execute("""
                       SELECT
                           UPPER(TRIM(j.incidencia)) AS incidencia_norm,
                           COUNT(*)                  AS total
                       FROM actividad_real a
                                LEFT JOIN jornada j
                                          ON j.usuario_id = a.usuario_id
                                              AND CAST(j.fecha AS DATE) = CAST(a.fecha_planeada AS DATE)
                                              AND j.cliente_id = ?
                       WHERE a.cliente_id = ?
                         AND CAST(a.fecha_planeada AS DATE) BETWEEN ? AND ?
                         AND a.fecha_real_inicio IS NOT NULL
                         AND j.incidencia IS NOT NULL
                         AND TRIM(j.incidencia) != ''
                       GROUP BY UPPER(TRIM(j.incidencia))
                       ORDER BY total DESC
                       """, [cliente_id, cliente_id, str(fecha_ini), str(fecha_fin)]).df()


@st.cache_data(ttl=300)
def rutas_resumen(cliente_id, fecha_ini, fecha_fin, canal_sel):
    return con.execute("""
                       SELECT
                           COALESCE(c.ruta, 'Sin ruta')      AS ruta,
                           COALESCE(c.entidad, 'Sin entidad') AS entidad,
                           COUNT(DISTINCT ad.usuario_id)      AS promotores,
                           COUNT(*)                           AS dias_activos,
                           ROUND(AVG(ad.horas_laboradas), 1)  AS horas_promedio,
                           SUM(CASE WHEN j.ausencia_id IS NOT NULL THEN 1 ELSE 0 END) AS ausencias
                       FROM actividad_dia ad
                                LEFT JOIN cuadrilla c ON c.id = ad.cuadrilla_id
                                LEFT JOIN jornada j
                                          ON j.usuario_id = ad.usuario_id
                                              AND CAST(j.fecha AS DATE) = ad.dia
                                              AND j.cliente_id = ?
                       WHERE ad.cliente_id = ?
                         AND ad.dia BETWEEN ? AND ?
                       GROUP BY c.ruta, c.entidad
                       ORDER BY promotores DESC
                       """, [cliente_id, cliente_id, str(fecha_ini), str(fecha_fin)]).df()



st.set_page_config(page_title="Operación Global", layout="wide")

# ─────────────────────────────────────────
# ESTILOS
# ─────────────────────────────────────────
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
# CONEXIÓN DUCKDB
# ─────────────────────────────────────────
@st.cache_resource
def get_con():
    con = duckdb.connect()
    # Parquets condensados para KPIs y tendencia
    con.execute(f"CREATE OR REPLACE VIEW actividad_mes  AS SELECT * FROM read_parquet('{parquet('actividad_mes', 'global')}')")
    con.execute(f"CREATE OR REPLACE VIEW actividad_dia  AS SELECT * FROM read_parquet('{parquet('actividad_dia', 'global')}')")
    # Original solo para Monitor Geo (necesita coordenadas GPS)
    con.execute(f"CREATE OR REPLACE VIEW actividad      AS SELECT * FROM read_parquet('{parquet('actividad', 'global')}')")
    con.execute(f"CREATE OR REPLACE VIEW actividad_real AS SELECT * FROM read_parquet('{parquet('actividad', 'global')}')")
    con.execute(f"CREATE OR REPLACE VIEW jornada        AS SELECT * FROM read_parquet('{parquet('jornada_diaria', 'global')}')")
    con.execute(f"CREATE OR REPLACE VIEW usuario        AS SELECT * FROM read_parquet('{parquet('user', 'global')}')")
    con.execute(f"CREATE OR REPLACE VIEW cliente        AS SELECT * FROM read_parquet('{parquet('cliente', 'global')}')")
    con.execute(f"CREATE OR REPLACE VIEW cuadrilla      AS SELECT * FROM read_parquet('{parquet('cuadrilla', 'global')}')")
    con.execute(f"CREATE OR REPLACE VIEW ausencia       AS SELECT * FROM read_parquet('{parquet('ausencia', 'global')}')")
    con.execute(f"CREATE OR REPLACE VIEW aus_usuario    AS SELECT * FROM read_parquet('{parquet('ausencia_usuario', 'global')}')")
    con.execute(f"CREATE OR REPLACE VIEW user_cliente   AS SELECT * FROM read_parquet('{parquet('user_cliente', 'global')}')")
    con.execute(f"CREATE OR REPLACE VIEW punto_venta    AS SELECT * FROM read_parquet('{parquet('punto_venta', 'global')}')")
    return con

con = get_con()

# ─────────────────────────────────────────
# SIDEBAR — FILTROS
# ─────────────────────────────────────────
st.sidebar.title("Operación Global")

clientes_opciones = {v: k for k, v in CLIENTES.items()}
cliente_sel = st.sidebar.selectbox("Cliente", list(clientes_opciones.keys()))
cliente_id  = clientes_opciones[cliente_sel]

@st.cache_data(ttl=600)
def ultimo_mes_con_datos(cliente_id):
    row = con.execute("""
                      SELECT MAX(anio) as anio, MAX(mes) as mes
                      FROM actividad_mes
                      WHERE cliente_id = ?
                        AND anio BETWEEN 2015 AND 2030
                      """, [cliente_id]).fetchone()
    from datetime import date
    if row and row[0]:
        return date(int(row[0]), int(row[1]), 1)
    return date.today().replace(day=1)

ultima     = ultimo_mes_con_datos(cliente_id)
inicio_def = ultima.replace(day=1)
fecha_ini  = st.sidebar.date_input("Fecha inicio", inicio_def)
fecha_fin  = st.sidebar.date_input("Fecha fin", ultima)
canal_sel = None

# ─────────────────────────────────────────
# DATOS
# ─────────────────────────────────────────
@st.cache_data(ttl=300)
def kpis_operacion(cliente_id, fecha_ini, fecha_fin, canal_sel):
    anio_ini = fecha_ini.year
    mes_ini  = fecha_ini.month
    anio_fin = fecha_fin.year
    mes_fin  = fecha_fin.month
    return con.execute("""
                       SELECT
                           COUNT(DISTINCT am.usuario_id)                               AS promotores_activos,
                           ROUND(SUM(am.horas_totales), 1)                             AS total_horas,
                           ROUND(AVG(am.horas_totales / NULLIF(am.dias_activos,0)), 1) AS promedio_horas,
                           SUM(CASE WHEN j.ausencia_id IS NOT NULL THEN 1 END)         AS ausencias,
                           SUM(am.dias_activos)                                        AS dias_trabajados,
                           SUM(am.pdvs_visitados)                                      AS pdv_visitados
                       FROM actividad_mes am
                                LEFT JOIN jornada j
                                          ON j.usuario_id = am.usuario_id
                                              AND j.cliente_id = am.cliente_id
                                              AND CAST(j.fecha AS DATE) BETWEEN ? AND ?
                       WHERE am.cliente_id = ?
                         AND (am.anio * 100 + am.mes) BETWEEN ? AND ?
                       """, [str(fecha_ini), str(fecha_fin),
                             cliente_id,
                             anio_ini * 100 + mes_ini,
                             anio_fin * 100 + mes_fin]).fetchone()




@st.cache_data(ttl=300)
def tendencia_diaria(cliente_id, fecha_ini, fecha_fin, canal_sel):
    return con.execute("""
                       SELECT
                           ad.dia,
                           COUNT(DISTINCT ad.usuario_id)                           AS promotores,
                           ROUND(AVG(ad.horas_laboradas), 2)                       AS horas_promedio,
                           SUM(CASE WHEN j.ausencia_id IS NOT NULL THEN 1 ELSE 0 END) AS ausencias
                       FROM actividad_dia ad
                                LEFT JOIN jornada j
                                          ON j.usuario_id = ad.usuario_id
                                              AND TRY_CAST(j.fecha AS DATE) = ad.dia
                                              AND j.cliente_id = ?
                       WHERE ad.cliente_id = ?
                         AND ad.dia BETWEEN ? AND ?
                       GROUP BY ad.dia
                       ORDER BY ad.dia
                       """, [cliente_id, cliente_id, str(fecha_ini), str(fecha_fin)]).df()


@st.cache_data(ttl=300)
def itinerario_promotor(cliente_id, fecha_ini, fecha_fin):
    return con.execute("""
                       SELECT
                           ad.dia                                                  AS fecha,
                           u.user_real_name                                        AS promotor,
                           COALESCE(c.ruta, 'Sin ruta')                           AS ruta,
                           COALESCE(c.entidad, 'Sin entidad')                     AS entidad,
                           STRFTIME(ad.primer_checkin, '%H:%M')                   AS hora_entrada,
                           STRFTIME(ad.ultimo_checkout, '%H:%M')                  AS hora_salida,
                           ROUND(ad.horas_laboradas * 60, 0)                      AS minutos,
                           ad.total_visitas,
                           ad.visitas_planeadas,
                           ad.visitas_fuera_ruta,
                           ad.pdvs_visitados
                       FROM actividad_dia ad
                                LEFT JOIN usuario u   ON u.id = ad.usuario_id
                                LEFT JOIN cuadrilla c ON c.id = ad.cuadrilla_id
                       WHERE ad.cliente_id = ?
                         AND ad.dia BETWEEN ? AND ?
                       ORDER BY ad.dia, u.user_real_name
                       """, [cliente_id, str(fecha_ini), str(fecha_fin)]).df()

# ─────────────────────────────────────────
# RENDER
# ─────────────────────────────────────────
st.title("📊 Operación Global")
st.caption(f"{cliente_sel}  ·  {fecha_ini.strftime('%d %b %Y')} — {fecha_fin.strftime('%d %b %Y')}")
st.divider()

with st.spinner("Cargando KPIs..."):
    kpis  = kpis_operacion(cliente_id, fecha_ini, fecha_fin, canal_sel)

# KPIs principales
col1, col2, col3, col4, col5 = st.columns(5)

def metric_card(col, label, value):
    col.markdown(f"""
    <div class="metric-card">
        <p class="metric-label">{label}</p>
        <p class="metric-value">{value}</p>
    </div>
    """, unsafe_allow_html=True)

metric_card(col1, "Promotores activos", f"{int(kpis[0] or 0):,}")
metric_card(col2, "Horas trabajadas",   f"{kpis[1] or 0:,.1f}")
metric_card(col3, "Promedio hrs/día",   f"{kpis[2] or 0:.1f}")
metric_card(col4, "Ausencias",          f"{int(kpis[3] or 0):,}")
metric_card(col5, "PDV visitados",      f"{int(kpis[5] or 0):,}")

st.divider()

# Tendencia
st.markdown('<p class="section-title">Tendencia diaria</p>', unsafe_allow_html=True)

with st.spinner("Cargando tendencia..."):
    df_tend = tendencia_diaria(cliente_id, fecha_ini, fecha_fin, canal_sel)

if not df_tend.empty:
    tab1, tab2, tab3 = st.tabs(["Horas promedio", "Promotores activos", "Ausencias"])

    with tab1:
        fig = px.line(df_tend, x="dia", y="horas_promedio",
                      markers=True, title="Horas promedio por día")
        fig.update_traces(line_color="#0057FF")
        fig.update_layout(xaxis_title="", yaxis_title="Horas", height=350)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        fig = px.bar(df_tend, x="dia", y="promotores",
                     title="Promotores activos por día", color_discrete_sequence=["#0057FF"])
        fig.update_layout(xaxis_title="", yaxis_title="Promotores", height=350)
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        fig = px.bar(df_tend, x="dia", y="ausencias",
                     title="Ausencias por día", color_discrete_sequence=["#FF4B4B"])
        fig.update_layout(xaxis_title="", yaxis_title="Ausencias", height=350)
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Sin datos para el período seleccionado.")

    # ── INCIDENCIAS ──────────────────────────────────────
st.divider()
st.markdown('<p class="section-title">Incidencias</p>', unsafe_allow_html=True)

with st.spinner("Cargando incidencias..."):
    df_inc = incidencias_resumen(cliente_id, fecha_ini, fecha_fin)

if not df_inc.empty:
    # Mapear grupos
    df_inc["grupo"] = df_inc["incidencia_norm"].map(INCIDENCIAS_MAP).fillna("Otro")
    df_grupo = df_inc.groupby("grupo")["total"].sum().reset_index()
    df_grupo["color"] = df_grupo["grupo"].map(COLORES_INCIDENCIA)

    col1, col2 = st.columns([1, 2])

    with col1:
        fig = go.Figure(go.Pie(
            labels=df_grupo["grupo"],
            values=df_grupo["total"],
            marker_colors=df_grupo["color"].tolist(),
            hole=0.5,
            textinfo="label+percent"
        ))
        fig.update_layout(
            title="Distribución por grupo",
            showlegend=False,
            height=320,
            margin=dict(t=40, b=0, l=0, r=0)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Top incidencias detalle
        df_top = df_inc.head(10).copy()
        df_top["color"] = df_top["grupo"].map(COLORES_INCIDENCIA)
        fig = px.bar(
            df_top, x="total", y="incidencia_norm",
            orientation="h",
            color="grupo",
            color_discrete_map=COLORES_INCIDENCIA,
            title="Top 10 incidencias"
        )
        fig.update_layout(
            xaxis_title="", yaxis_title="",
            height=320, showlegend=False,
            yaxis=dict(autorange="reversed")
        )
        st.plotly_chart(fig, use_container_width=True)

# ── RUTAS ─────────────────────────────────────────────
st.divider()
st.markdown('<p class="section-title">Rutas</p>', unsafe_allow_html=True)

with st.spinner("Cargando rutas..."):
    df_rutas = rutas_resumen(cliente_id, fecha_ini, fecha_fin, canal_sel)

if not df_rutas.empty:
    col1, col2, col3 = st.columns(3)
    metric_card(col1, "Total rutas",       f"{len(df_rutas):,}")
    metric_card(col2, "Total promotores",  f"{int(df_rutas['promotores'].sum()):,}")
    metric_card(col3, "Días activos prom", f"{df_rutas['dias_activos'].mean():.1f}")

    st.divider()

    tab1, tab2 = st.tabs(["Promotores por ruta", "Ausencias por ruta"])

    with tab1:
        fig = px.bar(
            df_rutas.head(20), x="ruta", y="promotores",
            color="entidad", title="Promotores activos por ruta",
            height=380
        )
        fig.update_layout(xaxis_title="", yaxis_title="Promotores")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        fig = px.bar(
            df_rutas.head(20), x="ruta", y="ausencias",
            color="entidad", title="Ausencias por ruta",
            color_discrete_sequence=["#EF4444"],
            height=380
        )
        fig.update_layout(xaxis_title="", yaxis_title="Ausencias")
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        df_rutas[["ruta", "entidad", "promotores", "dias_activos", "horas_promedio", "ausencias"]],
        width='stretch',
        hide_index=True
    )

# ------- EXPORTAR EXCEL ----------
st.divider()
st.markdown('<p class="section-title">Exportar datos</p>', unsafe_allow_html=True)

if st.button("📥 Generar Excel"):
    with st.spinner("Generando archivo..."):

        # KPIs
        df_kpis = pd.DataFrame([{
            "Promotores activos":     int(kpis[0] or 0),
            "Total horas trabajadas": float(kpis[1] or 0),
            "Promedio horas/día":     float(kpis[2] or 0),
            "Ausencias":              int(kpis[3] or 0),
            "Días trabajados":        int(kpis[4] or 0),
            "PDV visitados":          int(kpis[5] or 0),
        }])

        # Tendencia
        df_tend_export = df_tend.rename(columns={
            "dia": "Día", "promotores": "Promotores",
            "horas_promedio": "Horas promedio", "ausencias": "Ausencias"
        })

        # Resumen incidencias
        df_grupo_export = df_inc.copy()
        df_grupo_export["Grupo"] = df_grupo_export["incidencia_norm"].map(INCIDENCIAS_MAP).fillna("Otro")
        df_grupo_export = df_grupo_export.rename(columns={
            "incidencia_norm": "Incidencia", "total": "Total"
        })[["Incidencia", "Total", "Grupo"]]

        # Rutas
        df_rutas_export = df_rutas.rename(columns={
            "ruta": "Ruta", "entidad": "Entidad", "promotores": "Promotores",
            "dias_activos": "Días activos", "horas_promedio": "Horas promedio",
            "ausencias": "Ausencias"
        })

        # Detalle incidencias
        df_detalle_inc = detalle_incidencias(cliente_id, fecha_ini, fecha_fin)
        df_detalle_inc["Grupo"] = df_detalle_inc["incidencia_normalizada"].map(INCIDENCIAS_MAP).fillna("Otro")

        # Detalle jornada
        df_detalle_jor = detalle_jornada(cliente_id, fecha_ini, fecha_fin)

        # Detalle actividades
        df_detalle_act = detalle_actividades(cliente_id, fecha_ini, fecha_fin)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_kpis.to_excel(writer,            sheet_name="KPIs",                index=False)
            df_tend_export.to_excel(writer,     sheet_name="Tendencia diaria",    index=False)
            df_grupo_export.to_excel(writer,    sheet_name="Resumen incidencias", index=False)
            df_detalle_inc.to_excel(writer,     sheet_name="Detalle incidencias", index=False)
            df_detalle_jor.to_excel(writer,     sheet_name="Detalle jornada",     index=False)
            df_detalle_act.to_excel(writer,     sheet_name="Detalle actividades", index=False)
            df_rutas_export.to_excel(writer,    sheet_name="Rutas",               index=False)

        buffer.seek(0)

    st.download_button(
        label="⬇️ Descargar Excel",
        data=buffer,
        file_name=f"operacion_{cliente_sel}_{fecha_ini}_{fecha_fin}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ── ITINERARIO ────────────────────────────────────────
st.divider()
st.markdown('<p class="section-title">Itinerario detallado por promotor</p>',
            unsafe_allow_html=True)

with st.spinner("Cargando itinerario..."):
    df_itin = itinerario_promotor(cliente_id, fecha_ini, fecha_fin)

if not df_itin.empty:
    promotores_disp = ["Todos"] + sorted(df_itin["promotor"].dropna().unique().tolist())
    promotor_sel = st.selectbox("Filtrar por promotor", promotores_disp)
    if promotor_sel != "Todos":
        df_itin = df_itin[df_itin["promotor"] == promotor_sel]

    fechas_disp = ["Todas"] + sorted(df_itin["fecha"].astype(str).unique().tolist())
    fecha_sel_itin = st.selectbox("Filtrar por día", fechas_disp)
    if fecha_sel_itin != "Todas":
        df_itin = df_itin[df_itin["fecha"].astype(str) == fecha_sel_itin]

    col1, col2, col3, col4 = st.columns(4)
    metric_card(col1, "Días con actividad",  f"{len(df_itin):,}")
    metric_card(col2, "Total visitas",       f"{int(df_itin['total_visitas'].sum()):,}")
    metric_card(col3, "Visitas fuera ruta",  f"{int(df_itin['visitas_fuera_ruta'].sum()):,}")
    metric_card(col4, "PDVs visitados",      f"{int(df_itin['pdvs_visitados'].sum()):,}")

    st.divider()

    st.dataframe(
        df_itin.rename(columns={
            "fecha":             "Fecha",
            "promotor":          "Promotor",
            "ruta":              "Ruta",
            "entidad":           "Entidad",
            "hora_entrada":      "Hora entrada",
            "hora_salida":       "Hora salida",
            "minutos":           "Minutos",
            "total_visitas":     "Total visitas",
            "visitas_planeadas": "En ruta",
            "visitas_fuera_ruta":"Fuera de ruta",
            "pdvs_visitados":    "PDVs",
        }),
        hide_index=True,
        width="stretch",
    )

    buffer = io.BytesIO()
    df_itin.to_excel(buffer, index=False)
    buffer.seek(0)
    st.download_button(
        "⬇️ Descargar itinerario Excel",
        data=buffer,
        file_name=f"itinerario_{cliente_sel}_{fecha_ini}_{fecha_fin}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Sin datos de itinerario para el período seleccionado.")
