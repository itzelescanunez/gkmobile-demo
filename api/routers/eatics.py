from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text  # Para consultas directas
from typing import Optional, List
from sqlalchemy.orm import joinedload

from api import models
from api import schemas
from api.database import SessionLocal
from services.catalogo import listar_catalogo, obtener_detalle

#SERVICIES-ANALYTICS
from services.analytics import procesar_reporte_gerencial
router = APIRouter(prefix="/eatics", tags=["Eatics"])
templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─────────────────────────────────────────
# EJECUCIÓN MARCA
# ─────────────────────────────────────────
@router.get("/ejecucion-marca", response_class=HTMLResponse)
def vista_ejecucion_marca(
        request: Request,
        q: Optional[str] = None,
        marca: Optional[str] = None,
        supervisor: Optional[str] = None,
        page: int = 1,
        db: Session = Depends(get_db),
):
    resultado = listar_catalogo(
        db, models.EjecucionMarcaEatics,
        filtros={"nombre_marca": marca, "supervisor": supervisor},
        campos_busqueda=["nombre_marca", "user_real_name", "supervisor"],
        q=q, page=page,
    )
    return templates.TemplateResponse(request=request, name="eatics/ejecucion_marca_list.html", context={
        **resultado, "q": q, "marca": marca, "supervisor": supervisor,
        "titulo": "Ejecución por Marca",
        "catalogo": "ejecucion_marca",
    })


@router.get("/ejecucion-marca/{registro_id}", response_class=HTMLResponse)
def detalle_ejecucion_marca(request: Request, registro_id: int, db: Session = Depends(get_db)):
    item = obtener_detalle(db, models.EjecucionMarcaEatics, registro_id)
    if not item:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return templates.TemplateResponse(request=request, name="eatics/detalle.html", context={
        "item": item, "titulo": "Detalle — Ejecución Marca", "catalogo": "ejecucion-marca",
        "campos": [
            ("ID", item.id), ("Marca", item.nombre_marca), ("Promotor", item.user_real_name),
            ("Supervisor", item.supervisor), ("Fecha", item.fecha),
            ("SKUs", item.cant_sku), ("Agotados", item.cant_agotados),
            ("Preagotados", item.cant_preagotados), ("Planograma", item.planograma),
            ("Degustación", item.is_degustacion), ("Caducidad", item.caducidad),
            ("PDV ID", item.punto_venta_id), ("Cadena ID", item.cadena_id),
            ("Status", item.status),
        ]
    })


# ─────────────────────────────────────────
# EJECUCIÓN PDV
# ─────────────────────────────────────────
@router.get("/ejecucion-pdv", response_class=HTMLResponse)
def vista_ejecucion_pdv(
        request: Request,
        q: Optional[str] = None,
        supervisor: Optional[str] = None,
        page: int = 1,
        db: Session = Depends(get_db),
):
    resultado = listar_catalogo(
        db, models.EjecucionPdvEatics,
        filtros={"supervisor": supervisor},
        campos_busqueda=["user_real_name", "supervisor", "incidencias"],
        q=q, page=page,
    )
    return templates.TemplateResponse(request=request, name="eatics/ejecucion_pdv_list.html", context={
        **resultado, "q": q, "supervisor": supervisor,
        "titulo": "Ejecución por PDV",
        "catalogo": "ejecucion-pdv",
    })


@router.get("/ejecucion-pdv/{registro_id}", response_class=HTMLResponse)
def detalle_ejecucion_pdv(request: Request, registro_id: int, db: Session = Depends(get_db)):
    item = obtener_detalle(db, models.EjecucionPdvEatics, registro_id)
    if not item:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return templates.TemplateResponse(request=request, name="eatics/detalle.html", context={
        "item": item, "titulo": "Detalle — Ejecución PDV", "catalogo": "ejecucion-pdv",
        "campos": [
            ("ID", item.id), ("Promotor", item.user_real_name), ("Supervisor", item.supervisor),
            ("Fecha", item.fecha), ("Acomodo", item.acomodo), ("Incidencias", item.incidencias),
            ("Degustación", item.is_degustacion), ("Material degus", item.material_degus),
            ("Piezas degus", item.piezas_degus), ("Se presentó", item.sepresento),
            ("Se despidió", item.sedespidio), ("Telson", item.telson),
            ("PDV ID", item.punto_venta_id), ("Cadena ID", item.cadena_id), ("Status", item.status),
        ]
    })


# ─────────────────────────────────────────
# AUDITORÍA MARCA
# ─────────────────────────────────────────
@router.get("/auditoria-marca", response_class=HTMLResponse)
def vista_auditoria_marca(
        request: Request,
        q: Optional[str] = None,
        marca: Optional[str] = None,
        supervisor: Optional[str] = None,
        page: int = 1,
        db: Session = Depends(get_db),
):
    resultado = listar_catalogo(
        db, models.AuditoriaMarcaEatics,
        filtros={"nombre_marca": marca, "supervisor": supervisor},
        campos_busqueda=["nombre_marca", "user_real_name", "supervisor"],
        q=q, page=page,
    )
    return templates.TemplateResponse(request=request, name="eatics/auditoria_marca_list.html", context={
        **resultado, "q": q, "marca": marca, "supervisor": supervisor,
        "titulo": "Auditoría por Marca",
        "catalogo": "auditoria-marca",
    })


@router.get("/auditoria-marca/{registro_id}", response_class=HTMLResponse)
def detalle_auditoria_marca(request: Request, registro_id: int, db: Session = Depends(get_db)):
    item = obtener_detalle(db, models.AuditoriaMarcaEatics, registro_id)
    if not item:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return templates.TemplateResponse(request=request, name="eatics/detalle.html", context={
        "item": item, "titulo": "Detalle — Auditoría Marca", "catalogo": "auditoria-marca",
        "campos": [
            ("ID", item.id), ("Marca", item.nombre_marca), ("Promotor", item.user_real_name),
            ("Supervisor", item.supervisor), ("Fecha", item.fecha),
            ("Cumple reportado", item.cumple_reportado), ("Planograma", item.planograma),
            ("Degustación", item.is_degustacion), ("PDV ID", item.punto_venta_id),
            ("Cadena ID", item.cadena_id), ("Marca ID", item.marca_id), ("Status", item.status),
        ]
    })


# ─────────────────────────────────────────
# PRECIOS
# ─────────────────────────────────────────
#@router.get("/precios", response_class=HTMLResponse)
#def vista_precios(
#        request: Request,
#        q: Optional[str] = None,
#        supervisor: Optional[str] = None,
#        page: int = 1,
#        db: Session = Depends(get_db),
#):
#    resultado = listar_catalogo(
#        db, models.PreciosEatics,
#        filtros={"supervisor": supervisor},
#        campos_busqueda=["user_real_name", "supervisor"],
#        q=q, page=page,
#    )
#    return templates.TemplateResponse(request=request, name="eatics/precios_list.html", context={
#        **resultado, "q": q, "supervisor": supervisor,
#        "titulo": "Precios",
#        "catalogo": "precios",
#    })


#@router.get("/precios/{registro_id}", response_class=HTMLResponse)
#def detalle_precio(request: Request, registro_id: int, db: Session = Depends(get_db)):
#    item = obtener_detalle(db, models.PreciosEatics, registro_id)
#    if not item:
#        raise HTTPException(status_code=404, detail="Registro no encontrado")
#    return templates.TemplateResponse(request=request, name="eatics/detalle.html", context={
#        "item": item, "titulo": "Detalle — Precio", "catalogo": "precios",
#        "campos": [
#            ("ID", item.id), ("Promotor", item.user_real_name), ("Supervisor", item.supervisor),
#            ("Fecha", item.fecha), ("Precio", item.precio), ("Es propio", item.is_propio),
#            ("Producto ID", item.producto_id), ("Categoría ID", item.categoria_id),
#            ("PDV ID", item.punto_venta_id), ("Cadena ID", item.cadena_id), ("Status", item.status),
#        ]
#    })


# ─────────────────────────────────────────
# COMPETENCIA
# ─────────────────────────────────────────
@router.get("/competencia", response_class=HTMLResponse)
def vista_competencia(
        request: Request,
        q: Optional[str] = None,
        marca: Optional[str] = None,
        supervisor: Optional[str] = None,
        page: int = 1,
        db: Session = Depends(get_db),
):
    resultado = listar_catalogo(
        db, models.CompetenciaEatics,
        filtros={"marca": marca, "supervisor": supervisor},
        campos_busqueda=["marca", "user_real_name", "supervisor", "tipo_promo"],
        q=q, page=page,
    )
    return templates.TemplateResponse(request=request, name="eatics/competencia_list.html", context={
        **resultado, "q": q, "marca": marca, "supervisor": supervisor,
        "titulo": "Competencia",
        "catalogo": "competencia",
    })


@router.get("/competencia/{registro_id}", response_class=HTMLResponse)
def detalle_competencia(request: Request, registro_id: int, db: Session = Depends(get_db)):
    item = obtener_detalle(db, models.CompetenciaEatics, registro_id)
    if not item:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return templates.TemplateResponse(request=request, name="eatics/detalle.html", context={
        "item": item, "titulo": "Detalle — Competencia", "catalogo": "competencia",
        "campos": [
            ("ID", item.id), ("Marca competencia", item.marca), ("Promotor", item.user_real_name),
            ("Supervisor", item.supervisor), ("Fecha", item.fecha),
            ("Precio observado", item.precio_obs), ("Tipo promo", item.tipo_promo),
            ("Desc. promo", item.desc_promo), ("Frentes", item.frentes),
            ("Comentario", item.comentario), ("PDV ID", item.punto_venta_id),
            ("Cadena ID", item.cadena_id), ("Status", item.status),
        ]
    })


#------------

@router.get("/reporte-pdv")
def vista_reporte_pdv(
        request: Request,
        db: Session = Depends(get_db),
        f_inicio: str = None,
        f_fin: str = None,
        vista: str = "pdv"
):
    # 1. Obtener registros de la tabla principal
    registros = db.query(models.EjecucionMarcaEatics).all()

    # --- 2. MOTOR DE BÚSQUEDA AUTOMÁTICA DE TABLAS (PARA NOMBRES) ---
    cadenas_map = {}
    pdvs_map = {}

    try:
        # Obtenemos todas las tablas disponibles en la base de datos gkmobile
        todas_las_tablas = db.execute(text("SHOW TABLES")).fetchall()
        lista_tablas = [t[0] for t in todas_las_tablas]

        # A. Buscar tabla de Cadenas
        tabla_cadena = next((t for t in lista_tablas if any(x in t.lower() for x in ['cadena', 'cat_cad'])), None)
        if tabla_cadena:
            res = db.execute(text(f"SELECT id, nombre FROM {tabla_cadena}")).fetchall()
            cadenas_map = {row[0]: row[1] for row in res}

        # B. Buscar tabla de Puntos de Venta / Sucursales
        tabla_pdv = next((t for t in lista_tablas if any(x in t.lower() for x in ['punto', 'pdv', 'sucursal'])), None)
        if tabla_pdv:
            res = db.execute(text(f"SELECT id, nombre FROM {tabla_pdv}")).fetchall()
            pdvs_map = {row[0]: row[1] for row in res}

    except Exception as e:
        print(f"DEBUG: Error en búsqueda automática: {e}")

    # --- 3. CONSTRUCCIÓN DE DATOS PARA PANDAS ---
    data_para_pandas = []
    for r in registros:
        # Convertimos el objeto SQLAlchemy a diccionario
        item = {c.name: getattr(r, c.name) for c in r.__table__.columns}

        # Inyectamos nombres reales. Si no existen en el mapa, usamos el ID como respaldo.
        item['nombre_cadena'] = cadenas_map.get(r.cadena_id, f"ID: {r.cadena_id}")
        item['nombre_pdv'] = pdvs_map.get(r.punto_venta_id, f"ID: {r.punto_venta_id}")

        data_para_pandas.append(item)

    # --- 4. PROCESAMIENTO ANALÍTICO ---
    # La función ahora devuelve un dict con {'filas': [...], 'totales': {...}}
    resultado = procesar_reporte_gerencial(
        data_para_pandas,
        fecha_inicio=f_inicio,
        fecha_fin=f_fin,
        agrupar_por=vista
    )

    # --- 5. RENDERIZADO DE LA VISTA ---
    return templates.TemplateResponse(
        request=request,
        name="eatics/reporte_pdv_list.html",
        context={
            "request": request,
            "datos": resultado["filas"],
            "resumen": resultado["totales"],
            "vista_actual": vista,
            "catalogo": "reporte-gerencial"
        }
    )