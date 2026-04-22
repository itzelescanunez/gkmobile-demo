import path_setup
import pandas as pd
import streamlit as st
import duckdb
import io
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta
from config import parquet, CLIENTES

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
def rutas_resumen(cliente_id, fecha_ini, fecha_fin):
    return con.execute("""
                       SELECT
                           COALESCE(c.ruta, 'Sin ruta')          AS ruta,
                           COALESCE(c.entidad, 'Sin entidad')     AS entidad,
                           COUNT(DISTINCT a.usuario_id)           AS promotores,
                           COUNT(DISTINCT CAST(a.fecha_planeada AS DATE)) AS dias_activos,
                           ROUND(AVG(sub.horas_laboradas), 1)     AS horas_promedio,
                           SUM(CASE WHEN UPPER(TRIM(j.incidencia))
                               IN ('FALTA','FALTA INJUSTIFICADA','BAJA','INCAPACIDAD',
                                   'VACACIONES','VACANTE','FI','FJ')
                                        THEN 1 ELSE 0 END)                 AS ausencias
                       FROM actividad_real a
                                LEFT JOIN cuadrilla c ON c.id = a.cuadrilla_id
                                LEFT JOIN jornada j
                                          ON j.usuario_id = a.usuario_id
                                              AND CAST(j.fecha AS DATE) = CAST(a.fecha_planeada AS DATE)
                                              AND j.cliente_id = ?
                                LEFT JOIN (
                           SELECT
                               a2.usuario_id,
                               CAST(a2.fecha_planeada AS DATE) AS dia,
                               ROUND(EPOCH(
                                             MAX(TRY_CAST(a2.fecha_real_final AS TIMESTAMP)) -
                                             MIN(TRY_CAST(a2.fecha_real_inicio AS TIMESTAMP))
                                     ) / 3600.0, 2) AS horas_laboradas
                           FROM actividad_real a2
                           WHERE a2.cliente_id = ?
                             AND CAST(a2.fecha_planeada AS DATE) BETWEEN ? AND ?
                             AND a2.fecha_real_inicio IS NOT NULL
                           GROUP BY a2.usuario_id, CAST(a2.fecha_planeada AS DATE)
                       ) sub ON sub.usuario_id = a.usuario_id
                           AND sub.dia = CAST(a.fecha_planeada AS DATE)
                       WHERE a.cliente_id = ?
                         AND CAST(a.fecha_planeada AS DATE) BETWEEN ? AND ?
                         AND a.fecha_real_inicio IS NOT NULL
                       GROUP BY c.ruta, c.entidad
                       ORDER BY promotores DESC
                       """, [cliente_id, cliente_id, str(fecha_ini), str(fecha_fin),
                             cliente_id, str(fecha_ini), str(fecha_fin)]).df()



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
    con.execute(f"CREATE OR REPLACE VIEW actividad     AS SELECT * FROM read_parquet('{parquet('actividad')}')")
    con.execute(f"CREATE OR REPLACE VIEW jornada       AS SELECT * FROM read_parquet('{parquet('jornada_diaria')}')")
    con.execute(f"CREATE OR REPLACE VIEW usuario       AS SELECT * FROM read_parquet('{parquet('user')}')")
    con.execute(f"CREATE OR REPLACE VIEW cliente       AS SELECT * FROM read_parquet('{parquet('cliente')}')")
    con.execute(f"CREATE OR REPLACE VIEW cuadrilla     AS SELECT * FROM read_parquet('{parquet('cuadrilla')}')")
    con.execute(f"CREATE OR REPLACE VIEW ausencia      AS SELECT * FROM read_parquet('{parquet('ausencia')}')")
    con.execute(f"CREATE OR REPLACE VIEW aus_usuario   AS SELECT * FROM read_parquet('{parquet('ausencia_usuario')}')")
    con.execute(f"CREATE OR REPLACE VIEW user_cliente  AS SELECT * FROM read_parquet('{parquet('user_cliente')}')")
    con.execute(f"CREATE OR REPLACE VIEW punto_venta   AS SELECT * FROM read_parquet('{parquet('punto_venta')}')")

    # Vista de actividad filtrada — excluye cuentas de sistema
    con.execute("""
                CREATE OR REPLACE VIEW actividad_real AS
        WITH visitas_por_dia AS (
            SELECT usuario_id, CAST(fecha_planeada AS DATE) as dia, COUNT(*) as visitas
            FROM actividad
            GROUP BY usuario_id, CAST(fecha_planeada AS DATE)
        ),
        usuarios_sistema AS (
            SELECT usuario_id
            FROM visitas_por_dia
            GROUP BY usuario_id
            HAVING MAX(visitas) > 50
        )
                SELECT a.*
                FROM actividad a
                WHERE a.usuario_id NOT IN (SELECT usuario_id FROM usuarios_sistema)
                """)
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
                      SELECT MAX(CAST(fecha AS DATE)) as ultima
                      FROM jornada
                      WHERE cliente_id = ?
                      """, [cliente_id]).fetchone()
    return row[0] if row[0] else date.today()

ultima     = ultimo_mes_con_datos(cliente_id)
inicio_def = ultima.replace(day=1)
fecha_ini  = st.sidebar.date_input("Fecha inicio", inicio_def)
fecha_fin  = st.sidebar.date_input("Fecha fin", ultima)

# ─────────────────────────────────────────
# DATOS
# ─────────────────────────────────────────
@st.cache_data(ttl=300)
def kpis_operacion(cliente_id, fecha_ini, fecha_fin):
    return con.execute("""
                       SELECT
                           COUNT(DISTINCT usuario_id)                        AS promotores_activos,
                           ROUND(SUM(horas_laboradas), 1)                    AS total_horas,
                           ROUND(AVG(horas_laboradas), 1)                    AS promedio_horas,
                           SUM(CASE WHEN ausencia_id IS NOT NULL THEN 1 END) AS ausencias,
                           SUM(CASE WHEN ausencia_id IS NULL THEN 1 END)     AS dias_trabajados
                       FROM (
                                SELECT
                                    a.usuario_id,
                                    CAST(a.fecha_planeada AS DATE)                  AS dia,
                                    j.ausencia_id,
                                    ROUND(EPOCH(
                                                  MAX(TRY_CAST(a.fecha_real_final AS TIMESTAMP)) -
                                                  MIN(TRY_CAST(a.fecha_real_inicio AS TIMESTAMP))
                                          ) / 3600.0, 2)                                  AS horas_laboradas
                                FROM actividad_real a
                                         LEFT JOIN jornada j
                                                   ON j.usuario_id = a.usuario_id
                                                       AND CAST(j.fecha AS DATE) = CAST(a.fecha_planeada AS DATE)
                                                       AND j.cliente_id = ?
                                WHERE a.cliente_id = ?
                                  AND CAST(a.fecha_planeada AS DATE) BETWEEN ? AND ?
                                  AND a.fecha_real_inicio IS NOT NULL
                                GROUP BY a.usuario_id, CAST(a.fecha_planeada AS DATE), j.ausencia_id
                            )
                       """, [cliente_id, cliente_id, str(fecha_ini), str(fecha_fin)]).fetchone()


@st.cache_data(ttl=300)
def rutas_operacion(cliente_id, fecha_ini, fecha_fin):
    return con.execute("""
                       SELECT
                           COUNT(DISTINCT a.usuario_id)              AS promotores,
                           COUNT(*)                                   AS total_actividades,
                           COUNT(DISTINCT CAST(a.fecha_planeada AS DATE)) AS dias_con_ruta,
                           COUNT(DISTINCT a.punto_venta_id)           AS pdv_visitados,
                           ROUND(AVG(visitas_dia), 1)                 AS promedio_visitas_dia
                       FROM actividad_real a
                                JOIN (
                           SELECT usuario_id, CAST(fecha_planeada AS DATE) AS dia,
                                  COUNT(*) AS visitas_dia
                           FROM actividad_real
                           WHERE cliente_id = ?
                             AND CAST(fecha_planeada AS DATE) BETWEEN ? AND ?
                             AND fecha_real_inicio IS NOT NULL
                           GROUP BY usuario_id, CAST(fecha_planeada AS DATE)
                       ) sub ON sub.usuario_id = a.usuario_id
                       WHERE a.cliente_id = ?
                         AND CAST(a.fecha_planeada AS DATE) BETWEEN ? AND ?
                         AND a.fecha_real_inicio IS NOT NULL
                       """, [cliente_id, str(fecha_ini), str(fecha_fin),
                             cliente_id, str(fecha_ini), str(fecha_fin)]).fetchone()

@st.cache_data(ttl=300)
def tendencia_diaria(cliente_id, fecha_ini, fecha_fin):
    return con.execute("""
                       SELECT
                           dia,
                           COUNT(DISTINCT usuario_id)                                AS promotores,
                           ROUND(AVG(horas_laboradas), 2)                            AS horas_promedio,
                           SUM(CASE WHEN ausencia_id IS NOT NULL THEN 1 ELSE 0 END)  AS ausencias
                       FROM (
                                SELECT
                                    a.usuario_id,
                                    CAST(a.fecha_planeada AS DATE)                  AS dia,
                                    j.ausencia_id,
                                    ROUND(EPOCH(
                                                  MAX(TRY_CAST(a.fecha_real_final AS TIMESTAMP)) -
                                                  MIN(TRY_CAST(a.fecha_real_inicio AS TIMESTAMP))
                                          ) / 3600.0, 2)                                  AS horas_laboradas
                                FROM actividad_real a
                                         LEFT JOIN jornada j
                                                   ON j.usuario_id = a.usuario_id
                                                       AND CAST(j.fecha AS DATE) = CAST(a.fecha_planeada AS DATE)
                                                       AND j.cliente_id = ?
                                WHERE a.cliente_id = ?
                                  AND CAST(a.fecha_planeada AS DATE) BETWEEN ? AND ?
                                  AND a.fecha_real_inicio IS NOT NULL
                                GROUP BY a.usuario_id, CAST(a.fecha_planeada AS DATE), j.ausencia_id
                            )
                       GROUP BY dia
                       ORDER BY dia
                       """, [cliente_id, cliente_id, str(fecha_ini), str(fecha_fin)]).df()

# ─────────────────────────────────────────
# RENDER
# ─────────────────────────────────────────
st.title("📊 Operación Global")
st.caption(f"{cliente_sel}  ·  {fecha_ini.strftime('%d %b %Y')} — {fecha_fin.strftime('%d %b %Y')}")
st.divider()

with st.spinner("Cargando KPIs..."):
    kpis  = kpis_operacion(cliente_id, fecha_ini, fecha_fin)
    rutas = rutas_operacion(cliente_id, fecha_ini, fecha_fin)

# KPIs principales
col1, col2, col3, col4, col5 = st.columns(5)

def metric_card(col, label, value):
    col.markdown(f"""
    <div class="metric-card">
        <p class="metric-label">{label}</p>
        <p class="metric-value">{value}</p>
    </div>
    """, unsafe_allow_html=True)

metric_card(col1, "Promotores activos",  f"{int(kpis[0] or 0):,}")
metric_card(col2, "Horas trabajadas",    f"{kpis[1] or 0:,.1f}")
metric_card(col3, "Promedio hrs/día",    f"{kpis[2] or 0:.1f}")
metric_card(col4, "Ausencias",           f"{int(kpis[3] or 0):,}")
metric_card(col5, "PDV visitados",       f"{int(rutas[3] or 0):,}")

st.divider()

# Tendencia
st.markdown('<p class="section-title">Tendencia diaria</p>', unsafe_allow_html=True)

with st.spinner("Cargando tendencia..."):
    df_tend = tendencia_diaria(cliente_id, fecha_ini, fecha_fin)

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
    df_rutas = rutas_resumen(cliente_id, fecha_ini, fecha_fin)

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
            "PDV visitados":          int(rutas[3] or 0),
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