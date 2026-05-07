import pandas as pd
import streamlit as st
import duckdb
import io
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
from config import parquet, CLIENTES

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from app.path_setup import require_auth
require_auth()

st.set_page_config(page_title="Operación Global", layout="wide")

# ─────────────────────────────────────────
# ESTILOS
# ─────────────────────────────────────────
st.markdown("""
<style>
    .metric-card { background:#ffffff; border:1px solid #E2E4E9; border-radius:12px;
                   padding:16px; text-align:center; }
    .metric-value { font-size:1.6rem; font-weight:700; margin:0; color:#1A1D23; }
    .metric-label { font-size:0.7rem; color:#6B7280; text-transform:uppercase;
                    letter-spacing:0.08em; margin:0 0 4px; }
    .badge { display:inline-block; padding:2px 8px; border-radius:20px;
             font-size:0.75rem; font-weight:600; }
    .badge-green  { background:#DCFCE7; color:#166534; }
    .badge-yellow { background:#FEF9C3; color:#854D0E; }
    .badge-red    { background:#FEE2E2; color:#991B1B; }
    .section-title { font-size:1.1rem; font-weight:600; color:#1A1D23;
                     border-left:4px solid #0057FF; padding-left:10px; margin-bottom:16px; }
    .table-header { background:#F8F9FA; font-weight:600; font-size:0.75rem;
                    color:#6B7280; text-transform:uppercase; letter-spacing:0.05em; }
    div[data-testid="stExpander"] { border:1px solid #E2E4E9; border-radius:8px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# CONEXIÓN
# ─────────────────────────────────────────
@st.cache_resource
def get_con():
    con = duckdb.connect()
    con.execute(f"CREATE OR REPLACE VIEW actividad  AS SELECT * FROM read_parquet('{parquet('actividad', 'global')}')")
    con.execute(f"CREATE OR REPLACE VIEW jornada    AS SELECT * FROM read_parquet('{parquet('jornada_diaria', 'global')}')")
    con.execute(f"CREATE OR REPLACE VIEW usuario    AS SELECT * FROM read_parquet('{parquet('user', 'global')}')")
    con.execute(f"CREATE OR REPLACE VIEW cuadrilla  AS SELECT * FROM read_parquet('{parquet('cuadrilla', 'global')}')")
    con.execute(f"CREATE OR REPLACE VIEW punto_venta AS SELECT * FROM read_parquet('{parquet('punto_venta', 'global')}')")
    return con

con = get_con()

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def safe_int(v):
    try:
        return int(v) if pd.notna(v) else 0
    except:
        return 0


def fmt_hhmm(seg_expr):
    return f"""
        LPAD(CAST(CAST(FLOOR(({seg_expr}) / 3600) AS INTEGER) AS VARCHAR), 2, '0') || ':' ||
        LPAD(CAST(CAST(FLOOR((({seg_expr}) % 3600) / 60) AS INTEGER) AS VARCHAR), 2, '0')
    """

def badge(valor, verde, amarillo):
    if valor is None or valor == '':
        return ''
    try:
        v = float(str(valor).replace('%',''))
    except:
        return str(valor)
    if v >= verde:
        cls = 'badge-green'
    elif v >= amarillo:
        cls = 'badge-yellow'
    else:
        cls = 'badge-red'
    return f'<span class="badge {cls}">{valor}</span>'

def metric_card(col, label, value, sub=None):
    sub_html = f'<p style="font-size:0.7rem;color:#9CA3AF;margin:2px 0 0">{sub}</p>' if sub else ''
    col.markdown(f"""
    <div class="metric-card">
        <p class="metric-label">{label}</p>
        <p class="metric-value">{value}</p>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────
st.sidebar.title("Operación Global")

clientes_opciones = {v: k for k, v in CLIENTES.items()}
cliente_sel = st.sidebar.selectbox("Cliente", list(clientes_opciones.keys()))
cliente_id  = clientes_opciones[cliente_sel]

@st.cache_data(ttl=600)
def ultimo_mes_con_datos(cliente_id):
    row = con.execute("""
                      SELECT MAX(CAST(fecha_planeada AS DATE))
                      FROM actividad WHERE cliente_id = ?
                          AND YEAR(CAST(fecha_planeada AS DATE)) BETWEEN 2015 AND 2026
                      """, [cliente_id]).fetchone()
    return row[0] if row and row[0] else date.today()

ultima    = ultimo_mes_con_datos(cliente_id)
fecha_ini = st.sidebar.date_input("Fecha inicio", ultima.replace(day=1))
fecha_fin = st.sidebar.date_input("Fecha fin",    ultima)

# ─────────────────────────────────────────
# QUERY PRINCIPAL DE KPIs
# ─────────────────────────────────────────
HORA_OBJ_INICIO = 8 * 3600   # 08:00
HORA_OBJ_JORNADA = 8 * 3600  # 8 horas

@st.cache_data(ttl=300)
def kpis_por_usuario(cliente_id, fecha_ini, fecha_fin):
    return con.execute(f"""
        WITH usuarios_sistema AS (
            -- Excluir usuarios con >50 visitas/día (usuarios sistema)
            -- o con username que contiene punto y no son promotores reales
            SELECT usuario_id
            FROM (
                SELECT usuario_id,
                       CAST(fecha_planeada AS DATE) as dia,
                       COUNT(*) as cnt
                FROM actividad
                WHERE cliente_id = {cliente_id}
                  AND CAST(fecha_planeada AS DATE) BETWEEN '{fecha_ini}' AND '{fecha_fin}'
                GROUP BY usuario_id, CAST(fecha_planeada AS DATE)
            )
            GROUP BY usuario_id HAVING MAX(cnt) > 50
            UNION
            -- Excluir usuarios con username tipo email (auditores/sistema)
            SELECT u.id FROM usuario u
            WHERE u.username LIKE '%.%'
              AND u.cliente_id = {cliente_id}
        ),
        visitas AS (
            SELECT
                a.usuario_id,
                u.username,
                u.user_real_name,
                c.entidad,
                CAST(a.fecha_planeada AS DATE)              AS dia,
                TRY_CAST(a.fecha_real_inicio AS TIMESTAMP)  AS inicio,
                TRY_CAST(a.fecha_real_final  AS TIMESTAMP)  AS fin,
                a.is_tarea,
                EPOCH(
                    TRY_CAST(a.fecha_real_final AS TIMESTAMP) -
                    TRY_CAST(a.fecha_real_inicio AS TIMESTAMP)
                ) / 60.0                                    AS min_en_pdv
            FROM actividad a
            LEFT JOIN usuario u   ON u.id = a.usuario_id
            LEFT JOIN (
                SELECT id,
                       FIRST(entidad ORDER BY entidad NULLS LAST) AS entidad
                FROM cuadrilla
                WHERE entidad IS NOT NULL AND TRIM(entidad) != ''
                GROUP BY id
            ) c ON c.id = TRY_CAST(a.cuadrilla_id AS DOUBLE)
            WHERE a.cliente_id = {cliente_id}
              AND CAST(a.fecha_planeada AS DATE) BETWEEN '{fecha_ini}' AND '{fecha_fin}'
              AND a.usuario_id NOT IN (SELECT usuario_id FROM usuarios_sistema)
        ),
        por_dia AS (
            SELECT
                usuario_id, username, user_real_name, entidad, dia,
                COUNT(*)                                        AS planeadas,
                COUNT(inicio)                                   AS realizadas,
                COUNT(CASE WHEN is_tarea = '1'
                    AND inicio IS NOT NULL THEN 1 END)          AS tareas_realizadas,
                COUNT(CASE WHEN is_tarea = '1'
                    THEN 1 END)                                 AS tareas_planeadas,
                MIN(EPOCH(inicio) % 86400)                      AS seg_inicio,
                MAX(EPOCH(fin)   % 86400)                       AS seg_fin,
                CASE WHEN MAX(fin) > MIN(inicio)
                     THEN EPOCH(MAX(fin) - MIN(inicio)) / 3600.0
                     ELSE NULL END                              AS horas_jornada,
                -- Clamp horas_en_pdv a máximo horas_jornada para evitar negativos
                LEAST(
                    SUM(CASE WHEN min_en_pdv > 0
                        THEN min_en_pdv ELSE 0 END) / 60.0,
                    CASE WHEN MAX(fin) > MIN(inicio)
                         THEN EPOCH(MAX(fin) - MIN(inicio)) / 3600.0
                         ELSE NULL END
                )                                               AS horas_en_pdv
            FROM visitas
            GROUP BY usuario_id, username, user_real_name, entidad, dia
        )
        SELECT
            usuario_id,
            username,
            user_real_name,
            COALESCE(entidad, 'Sin entidad')                    AS entidad,
            -- Promotores activos (días con al menos 1 visita)
            COUNT(DISTINCT CASE WHEN realizadas > 0
                THEN dia END)                                   AS dias_activos,
            -- Ausencias inferidas (días planeados sin ninguna visita realizada)
            COUNT(CASE WHEN realizadas = 0
                AND planeadas > 0 THEN 1 END)                   AS ausencias,
            -- Tareas realizadas
            SUM(tareas_realizadas)                              AS tareas_realizadas,
            SUM(tareas_planeadas)                               AS tareas_planeadas,
            -- Hora inicio promedio
            {fmt_hhmm('AVG(CASE WHEN seg_inicio IS NOT NULL AND realizadas > 0 THEN seg_inicio END)')} AS hora_inicio,
            -- % cumplimiento hora inicio (antes 8am)
            ROUND(COUNT(CASE WHEN seg_inicio <= {HORA_OBJ_INICIO}
                AND realizadas > 0 THEN 1 END) * 100.0 /
                NULLIF(COUNT(CASE WHEN realizadas > 0 THEN 1 END), 0), 0) AS pct_inicio,
            -- Hora fin promedio
            {fmt_hhmm('AVG(CASE WHEN seg_fin IS NOT NULL AND realizadas > 0 THEN seg_fin END)')} AS hora_fin,
            -- % jornada >= 8hrs
            ROUND(COUNT(CASE WHEN horas_jornada >= 8 THEN 1 END) * 100.0 /
                NULLIF(COUNT(CASE WHEN realizadas > 0 THEN 1 END), 0), 0) AS pct_fin,
            -- T. laborado promedio (HH:MM)
            {fmt_hhmm('AVG(CASE WHEN horas_jornada > 0 AND horas_jornada <= 16 THEN horas_jornada * 3600 END)')} AS t_laborado,
            -- T. traslados (HH:MM)
            {fmt_hhmm('AVG(CASE WHEN horas_jornada > 0 AND horas_jornada <= 16 THEN (horas_jornada - horas_en_pdv) * 3600 END)')} AS t_traslado,
            -- % traslados del total jornada
            ROUND(AVG(CASE WHEN horas_jornada > 0 AND horas_jornada <= 16
                THEN (horas_jornada - horas_en_pdv) / horas_jornada * 100 END), 0) AS pct_traslado,
            -- T. en PDV (HH:MM)
            {fmt_hhmm('AVG(CASE WHEN horas_en_pdv > 0 THEN horas_en_pdv * 3600 END)')} AS t_pdv,
            -- % PDV del total jornada
            ROUND(AVG(CASE WHEN horas_jornada > 0 AND horas_jornada <= 16
                THEN horas_en_pdv / horas_jornada * 100 END), 0) AS pct_pdv,
            -- Visitas promedio por día
            ROUND(AVG(CASE WHEN realizadas > 0 THEN realizadas END), 1) AS visitas_prom,
            -- Plan y cumplimiento
            SUM(planeadas)                                      AS plan,
            SUM(realizadas)                                     AS realizadas_total,
            ROUND(SUM(realizadas) * 100.0 /
                NULLIF(SUM(planeadas), 0), 0)                   AS pct_visitas
        FROM por_dia
        GROUP BY usuario_id, username, user_real_name, entidad
        ORDER BY entidad, username
    """).df()

@st.cache_data(ttl=300)
def ausencias_periodo(cliente_id, fecha_ini, fecha_fin):
    return con.execute(f"""
        SELECT COUNT(*) as ausencias
        FROM jornada
        WHERE cliente_id = {cliente_id}
          AND CAST(fecha AS DATE) BETWEEN '{fecha_ini}' AND '{fecha_fin}'
          AND ausencia_id IS NOT NULL
    """).fetchone()[0] or 0

# ─────────────────────────────────────────
# RENDER
# ─────────────────────────────────────────
st.title("📊 Operación Global")
st.caption(f"{cliente_sel}  ·  {fecha_ini.strftime('%d %b %Y')} — {fecha_fin.strftime('%d %b %Y')}")
st.divider()

with st.spinner("Cargando datos..."):
    df = kpis_por_usuario(cliente_id, fecha_ini, fecha_fin)
    ausencias = ausencias_periodo(cliente_id, fecha_ini, fecha_fin)

if df.empty:
    st.info("Sin datos para el período seleccionado.")
    st.stop()

# ─────────────────────────────────────────
# SECCIÓN GENERAL
# ─────────────────────────────────────────
st.markdown('<p class="section-title">Resumen general</p>', unsafe_allow_html=True)

total_plan       = int(df["plan"].sum())
total_real       = int(df["realizadas_total"].sum())
total_promotores = df["usuario_id"].nunique()
pct_visitas_gen  = round(total_real * 100 / total_plan, 0) if total_plan else 0

# Calcular promedios globales ponderados
avg_seg_inicio  = df[df["hora_inicio"].notna()]["hora_inicio"].apply(
    lambda x: int(x[:2])*3600 + int(x[3:5])*60 if x and len(x)==5 else None
).mean()
avg_seg_fin     = df[df["hora_fin"].notna()]["hora_fin"].apply(
    lambda x: int(x[:2])*3600 + int(x[3:5])*60 if x and len(x)==5 else None
).mean()

def seg_to_hhmm(seg):
    if seg is None or pd.isna(seg): return "—"
    s = int(seg)
    return f"{s//3600:02d}:{(s%3600)//60:02d}"

pct_inicio_gen = round(df["pct_inicio"].mean(), 0) if not df["pct_inicio"].isna().all() else 0
pct_fin_gen    = round(df["pct_fin"].mean(), 0)    if not df["pct_fin"].isna().all() else 0

col1, col2, col3, col4, col5, col6 = st.columns(6)
metric_card(col1, "Promotores activos",  f"{total_promotores:,}")
metric_card(col2, "Hora inicio prom",    seg_to_hhmm(avg_seg_inicio),
            sub=f"{int(pct_inicio_gen)}% cump.")
metric_card(col3, "Hora fin prom",       seg_to_hhmm(avg_seg_fin),
            sub=f"{int(pct_fin_gen)}% ≥8hrs")
metric_card(col4, "Visitas planeadas",   f"{total_plan:,}")
metric_card(col5, "Visitas realizadas",  f"{total_real:,}",
            sub=f"{int(pct_visitas_gen)}% cump.")
metric_card(col6, "Ausencias",           f"{ausencias:,}")

st.divider()

# Segunda fila de KPIs de tiempos
def safe_int(v):
    try:
        return int(v) if __import__('pandas').notna(v) else 0
    except:
        return 0

def hhmm_to_min(x):
    try:
        if not x or not isinstance(x, str) or len(x) != 5:
            return None
        return int(x[:2]) * 60 + int(x[3:5])
    except:
        return None

avg_lab  = df["t_laborado"].apply(hhmm_to_min).mean()
avg_tras = df["t_traslado"].apply(hhmm_to_min).mean()
avg_pdv  = df["t_pdv"].apply(hhmm_to_min).mean()
avg_prom = df["visitas_prom"].mean()

def min_to_hhmm(mins):
    if mins is None or pd.isna(mins): return "—"
    m = int(mins)
    return f"{m//60:02d}:{m%60:02d}"

col1, col2, col3, col4 = st.columns(4)
metric_card(col1, "T. laborado prom",   min_to_hhmm(avg_lab))
metric_card(col2, "T. traslados prom",  min_to_hhmm(avg_tras),
            sub=f"{safe_int(df['pct_traslado'].mean())}% de jornada")
metric_card(col3, "T. en PDV prom",     min_to_hhmm(avg_pdv),
            sub=f"{safe_int(df['pct_pdv'].mean())}% de jornada")
metric_card(col4, "Visitas prom/día",   f"{avg_prom:.1f}")

st.divider()

# ─────────────────────────────────────────
# DETALLE POR EQUIPO
# ─────────────────────────────────────────
st.markdown('<p class="section-title">Detalle por equipo</p>', unsafe_allow_html=True)

df_equipo = df.groupby("entidad").agg(
    promotores    =("usuario_id",       "nunique"),
    plan          =("plan",             "sum"),
    realizadas    =("realizadas_total", "sum"),
).reset_index()
df_equipo["pct_visitas"] = (df_equipo["realizadas"] / df_equipo["plan"] * 100).round(0)

# Calcular promedios de tiempos por equipo desde df
for col_t in ["hora_inicio","hora_fin","t_laborado","t_traslado","t_pdv"]:
    df_equipo[col_t] = df.groupby("entidad")[col_t].apply(
        lambda s: min_to_hhmm(s.apply(hhmm_to_min).mean())
    ).values

df_equipo["pct_inicio"] = df.groupby("entidad")["pct_inicio"].mean().round(0).values
df_equipo["pct_fin"]    = df.groupby("entidad")["pct_fin"].mean().round(0).values
df_equipo["pct_traslado"] = df.groupby("entidad")["pct_traslado"].mean().round(0).values
df_equipo["pct_pdv"]    = df.groupby("entidad")["pct_pdv"].mean().round(0).values
df_equipo["visitas_prom"] = df.groupby("entidad")["visitas_prom"].mean().round(1).values

# Renderizar tabla HTML de equipo
def render_tabla_equipo(df_eq):
    rows = ""
    for _, r in df_eq.iterrows():
        pct_v = safe_int(r["pct_visitas"]) if pd.notna(r["pct_visitas"]) else 0
        pct_i = safe_int(r["pct_inicio"])  if pd.notna(r["pct_inicio"])  else 0
        pct_f = safe_int(r["pct_fin"])     if pd.notna(r["pct_fin"])     else 0
        rows += f"""
        <tr style="border-bottom:1px solid #F3F4F6">
          <td style="padding:8px;font-weight:500">{r['entidad']}</td>
          <td style="padding:8px;text-align:center">{r['promotores']}</td>
          <td style="padding:8px;text-align:center">
            <b>{r['hora_inicio']}</b>
            <span class="badge {'badge-green' if pct_i>=70 else 'badge-yellow' if pct_i>=40 else 'badge-red'}">{pct_i}%</span>
          </td>
          <td style="padding:8px;text-align:center">
            {r['hora_fin']}
            <span class="badge {'badge-green' if pct_f>=50 else 'badge-yellow' if pct_f>=25 else 'badge-red'}">{pct_f}%</span>
          </td>
          <td style="padding:8px;text-align:center">{r['t_laborado']}</td>
          <td style="padding:8px;text-align:center">
            {r['t_traslado']}
            <span style="font-size:0.7rem;color:#9CA3AF">{safe_int(r['pct_traslado'] or 0)}%</span>
          </td>
          <td style="padding:8px;text-align:center">
            {r['t_pdv']}
            <span style="font-size:0.7rem;color:#9CA3AF">{safe_int(r['pct_pdv'] or 0)}%</span>
          </td>
          <td style="padding:8px;text-align:center">{r['visitas_prom']}</td>
          <td style="padding:8px;text-align:center">{safe_int(r['plan'])}</td>
          <td style="padding:8px;text-align:center">{safe_int(r['realizadas'])}</td>
          <td style="padding:8px;text-align:center">
            <span class="badge {'badge-green' if pct_v>=80 else 'badge-yellow' if pct_v>=60 else 'badge-red'}">{pct_v}%</span>
          </td>
          <td style="padding:8px;text-align:center">{safe_int(r.get('tareas_realizadas',0))}</td>
          <td style="padding:8px;text-align:center">{safe_int(r.get('ausencias',0))}</td>
        </tr>"""
    return f"""
    <table style="width:100%;border-collapse:collapse;font-size:0.82rem">
      <thead>
        <tr class="table-header" style="border-bottom:2px solid #E2E4E9">
          <th style="padding:8px;text-align:left">Entidad</th>
          <th style="padding:8px;text-align:center">Promotores</th>
          <th style="padding:8px;text-align:center">Inicio</th>
          <th style="padding:8px;text-align:center">Fin</th>
          <th style="padding:8px;text-align:center">T. Laborado</th>
          <th style="padding:8px;text-align:center">T. Traslados</th>
          <th style="padding:8px;text-align:center">T. x PDV</th>
          <th style="padding:8px;text-align:center">V. prom.</th>
          <th style="padding:8px;text-align:center">Plan</th>
          <th style="padding:8px;text-align:center">Realizadas</th>
          <th style="padding:8px;text-align:center">Cump.</th>
          <th style="padding:8px;text-align:center">Tareas</th>
          <th style="padding:8px;text-align:center">Ausencias</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>"""

st.markdown(render_tabla_equipo(df_equipo), unsafe_allow_html=True)

st.divider()

# ─────────────────────────────────────────
# DETALLE POR USUARIO
# ─────────────────────────────────────────
st.markdown('<p class="section-title">Detalle por usuario</p>', unsafe_allow_html=True)

entidades = sorted(
    [e for e in df["entidad"].unique().tolist() if e != "Sin entidad"]
) + (["Sin entidad"] if "Sin entidad" in df["entidad"].unique().tolist() else [])

for entidad in entidades:
    df_ent = df[df["entidad"] == entidad].copy()
    total_ent = df_ent["realizadas_total"].sum()
    plan_ent  = df_ent["plan"].sum()
    pct_ent   = round(total_ent * 100 / plan_ent, 0) if plan_ent else 0

    # Badge color según cumplimiento
    if pct_ent >= 80:
        icono = "🟢"
    elif pct_ent >= 60:
        icono = "🟡"
    else:
        icono = "🔴"

    with st.expander(f"{icono} {entidad}  —  {len(df_ent)} promotores  ·  {int(total_ent)}/{int(plan_ent)} visitas  ·  {int(pct_ent)}% cump."):
        rows = ""
        for _, r in df_ent.iterrows():
            pct_v = safe_int(r["pct_visitas"]) if pd.notna(r["pct_visitas"]) else 0
            pct_i = safe_int(r["pct_inicio"])  if pd.notna(r["pct_inicio"])  else 0
            pct_f = safe_int(r["pct_fin"])     if pd.notna(r["pct_fin"])     else 0
            # Puesto: S si username es PRC + número corto (supervisores)
            es_sup = bool(r["username"] and
                          __import__('re').match(r'^PRC0\d{2}$', str(r["username"])))
            puesto = "S" if es_sup else "—"
            rows += f"""
            <tr style="border-bottom:1px solid #F3F4F6;
                       {'background:#F0F7FF' if es_sup else ''}">
              <td style="padding:8px;font-family:monospace;font-size:0.8rem">{r['username']}</td>
              <td style="padding:8px">{r['user_real_name']}</td>
              <td style="padding:8px;text-align:center;color:#6B7280">{puesto}</td>
              <td style="padding:8px;text-align:center">
                <b>{r['hora_inicio'] or '—'}</b>
                <span class="badge {'badge-green' if pct_i>=70 else 'badge-yellow' if pct_i>=40 else 'badge-red'}">{pct_i}%</span>
              </td>
              <td style="padding:8px;text-align:center">
                {r['hora_fin'] or '—'}
                <span class="badge {'badge-green' if pct_f>=50 else 'badge-yellow' if pct_f>=25 else 'badge-red'}">{pct_f}%</span>
              </td>
              <td style="padding:8px;text-align:center">{r['t_laborado'] or '—'}</td>
              <td style="padding:8px;text-align:center">
                {r['t_traslado'] or '—'}
                <span style="font-size:0.7rem;color:#9CA3AF">{safe_int(r['pct_traslado'] or 0)}%</span>
              </td>
              <td style="padding:8px;text-align:center">
                {r['t_pdv'] or '—'}
                <span style="font-size:0.7rem;color:#9CA3AF">{safe_int(r['pct_pdv'] or 0)}%</span>
              </td>
              <td style="padding:8px;text-align:center">{r['visitas_prom'] or '—'}</td>
              <td style="padding:8px;text-align:center">{safe_int(r['plan'])}</td>
              <td style="padding:8px;text-align:center">{safe_int(r['realizadas_total'])}</td>
              <td style="padding:8px;text-align:center">
                <span class="badge {'badge-green' if pct_v>=80 else 'badge-yellow' if pct_v>=60 else 'badge-red'}">{pct_v}%</span>
              </td>
              <td style="padding:8px;text-align:center">{safe_int(r.get('tareas_realizadas',0))}</td>
              <td style="padding:8px;text-align:center">{safe_int(r.get('ausencias',0))}</td>
            </tr>"""

        st.markdown(f"""
        <table style="width:100%;border-collapse:collapse;font-size:0.8rem">
          <thead>
            <tr class="table-header" style="border-bottom:2px solid #E2E4E9">
              <th style="padding:8px;text-align:left">Usuario</th>
              <th style="padding:8px;text-align:left">Nombre</th>
              <th style="padding:8px;text-align:center">Puesto</th>
              <th style="padding:8px;text-align:center">Inicio</th>
              <th style="padding:8px;text-align:center">Fin</th>
              <th style="padding:8px;text-align:center">T. Laborado</th>
              <th style="padding:8px;text-align:center">T. Traslados</th>
              <th style="padding:8px;text-align:center">T. x PDV</th>
              <th style="padding:8px;text-align:center">V. prom.</th>
              <th style="padding:8px;text-align:center">Plan</th>
              <th style="padding:8px;text-align:center">Realizadas</th>
              <th style="padding:8px;text-align:center">Cump.</th>
              <th style="padding:8px;text-align:center">Tareas</th>
              <th style="padding:8px;text-align:center">Ausencias</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>""", unsafe_allow_html=True)

st.divider()

# ─────────────────────────────────────────
# EXPORTAR
# ─────────────────────────────────────────
st.markdown('<p class="section-title">Exportar</p>', unsafe_allow_html=True)

if st.button("📥 Generar Excel"):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        # General
        pd.DataFrame([{
            "Promotores activos":   total_promotores,
            "Visitas planeadas":    total_plan,
            "Visitas realizadas":   total_real,
            "% Cumplimiento":       pct_visitas_gen,
            "Ausencias":            ausencias,
        }]).to_excel(writer, sheet_name="Resumen general", index=False)
        # Por equipo
        df_equipo.to_excel(writer, sheet_name="Detalle por equipo", index=False)
        # Por usuario
        df.to_excel(writer, sheet_name="Detalle por usuario", index=False)

    buffer.seek(0)
    st.download_button(
        "⬇️ Descargar Excel",
        data=buffer,
        file_name=f"operacion_{cliente_sel}_{fecha_ini}_{fecha_fin}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )