from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from api.database import SessionLocal
from models.model_operacion import Promotor, Cuadrilla, JornadaDiaria, Ausencia, Servicio
from services.catalogo import listar_catalogo, obtener_detalle

router_operacion = APIRouter(prefix="/operacion", tags=["Operacion"])
templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─────────────────────────────────────────
# PROMOTORES
# ─────────────────────────────────────────
@router_operacion.get("/promotores", response_class=HTMLResponse)
def vista_promotores(
        request: Request,
        q: Optional[str] = None,
        page: int = 1,
        db: Session = Depends(get_db),
):
    resultado = listar_catalogo(
        db, Promotor,
        campos_busqueda=["user_real_name", "username", "email"],
        q=q, page=page, page_size=50,
    )
    return templates.TemplateResponse(
        request=request,
        name="operacion/promotores_list.html",
        context={
            **resultado, "q": q,
            "titulo": "Promotores",
            "catalogo": "promotores",
        },
    )


@router_operacion.get("/promotores/{registro_id}", response_class=HTMLResponse)
def detalle_promotor(request: Request, registro_id: int, db: Session = Depends(get_db)):
    item = obtener_detalle(db, Promotor, registro_id)
    if not item:
        raise HTTPException(status_code=404, detail="Promotor no encontrado")
    return templates.TemplateResponse(
        request=request,
        name="operacion/detalle.html",
        context={
            "item": item, "titulo": "Detalle — Promotor", "catalogo": "promotores",
            "campos": [
                ("ID", item.id), ("Nombre", item.user_real_name),
                ("Usuario", item.username), ("Email", item.email),
                ("Teléfono", item.telefono), ("Perfil", item.perfil),
                ("Cuadrilla ID", item.cuadrilla_id),
                ("Último acceso", item.last_login),
                ("Fecha creación", item.fecha_creacion),
                ("Habilitado", item.enabled), ("Status", item.status),
            ],
        },
    )


# ─────────────────────────────────────────
# CUADRILLAS
# ─────────────────────────────────────────
@router_operacion.get("/cuadrillas", response_class=HTMLResponse)
def vista_cuadrillas(
        request: Request,
        q: Optional[str] = None,
        agencia: Optional[str] = None,
        entidad: Optional[str] = None,
        page: int = 1,
        db: Session = Depends(get_db),
):
    resultado = listar_catalogo(
        db, Cuadrilla,
        filtros={"agencia": agencia, "entidad": entidad},
        campos_busqueda=["nombre", "puesto", "agencia", "entidad", "region"],
        q=q, page=page, page_size=50,
    )
    return templates.TemplateResponse(
        request=request,
        name="operacion/cuadrillas_list.html",
        context={
            **resultado, "q": q, "agencia": agencia, "entidad": entidad,
            "titulo": "Cuadrillas",
            "catalogo": "cuadrillas",
        },
    )


@router_operacion.get("/cuadrillas/{registro_id}", response_class=HTMLResponse)
def detalle_cuadrilla(request: Request, registro_id: int, db: Session = Depends(get_db)):
    item = obtener_detalle(db, Cuadrilla, registro_id)
    if not item:
        raise HTTPException(status_code=404, detail="Cuadrilla no encontrada")
    return templates.TemplateResponse(
        request=request,
        name="operacion/detalle.html",
        context={
            "item": item, "titulo": "Detalle — Cuadrilla", "catalogo": "cuadrillas",
            "campos": [
                ("ID", item.id), ("Nombre", item.nombre),
                ("Entidad", item.entidad), ("Puesto", item.puesto),
                ("Agencia", item.agencia), ("Región", item.region),
                ("Plaza", item.plaza), ("Ruta", item.ruta),
                ("Tipo", item.tipo), ("Status", item.status),
                ("Fecha creación", item.fecha_creacion),
            ],
        },
    )


# ─────────────────────────────────────────
# JORNADAS
# ─────────────────────────────────────────
@router_operacion.get("/jornadas", response_class=HTMLResponse)
def vista_jornadas(
        request: Request,
        q: Optional[str] = None,
        fecha_ini: Optional[str] = None,
        fecha_fin: Optional[str] = None,
        page: int = 1,
        db: Session = Depends(get_db),
):
    from datetime import date
    from sqlalchemy import and_

    if not fecha_ini:
        fecha_ini = date.today().replace(day=1).strftime("%Y-%m-%d")
    if not fecha_fin:
        fecha_fin = date.today().strftime("%Y-%m-%d")

    query = db.query(JornadaDiaria).filter(
        JornadaDiaria.fecha >= fecha_ini,
        JornadaDiaria.fecha <= fecha_fin,
        )

    if q:
        query = query.filter(JornadaDiaria.incidencia.ilike(f"%{q}%"))

    total = query.count()
    page_size = 50
    offset = (page - 1) * page_size
    registros = query.order_by(JornadaDiaria.fecha.desc()).offset(offset).limit(page_size).all()

    return templates.TemplateResponse(
        request=request,
        name="operacion/jornadas_list.html",
        context={
            "registros": registros,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, -(-total // page_size)),
            "q": q,
            "fecha_ini": fecha_ini,
            "fecha_fin": fecha_fin,
            "titulo": "Jornadas diarias",
            "catalogo": "jornadas",
        },
    )


@router_operacion.get("/jornadas/{registro_id}", response_class=HTMLResponse)
def detalle_jornada(request: Request, registro_id: int, db: Session = Depends(get_db)):
    item = obtener_detalle(db, JornadaDiaria, registro_id)
    if not item:
        raise HTTPException(status_code=404, detail="Jornada no encontrada")
    tipo_label = {0: "Check-in", 1: "Check-out"}.get(item.tipo, str(item.tipo))
    return templates.TemplateResponse(
        request=request,
        name="operacion/detalle.html",
        context={
            "item": item, "titulo": "Detalle — Jornada", "catalogo": "jornadas",
            "campos": [
                ("ID", item.id), ("Usuario ID", item.usuario_id),
                ("Cuadrilla ID", item.cuadrilla_id), ("Cliente ID", item.cliente_id),
                ("Fecha", item.fecha), ("Tipo", tipo_label),
                ("Incidencia", item.incidencia), ("Ausencia ID", item.ausencia_id),
                ("Fecha creación", item.fecha_creacion), ("Status", item.status),
            ],
        },
    )


# ─────────────────────────────────────────
# AUSENCIAS
# ─────────────────────────────────────────
@router_operacion.get("/ausencias", response_class=HTMLResponse)
def vista_ausencias(
        request: Request,
        q: Optional[str] = None,
        page: int = 1,
        db: Session = Depends(get_db),
):
    resultado = listar_catalogo(
        db, Ausencia,
        campos_busqueda=["nombre"],
        q=q, page=page, page_size=50,
    )
    return templates.TemplateResponse(
        request=request,
        name="operacion/ausencias_list.html",
        context={
            **resultado, "q": q,
            "titulo": "Tipos de ausencia",
            "catalogo": "ausencias",
        },
    )


@router_operacion.get("/ausencias/{registro_id}", response_class=HTMLResponse)
def detalle_ausencia(request: Request, registro_id: int, db: Session = Depends(get_db)):
    item = obtener_detalle(db, Ausencia, registro_id)
    if not item:
        raise HTTPException(status_code=404, detail="Ausencia no encontrada")
    return templates.TemplateResponse(
        request=request,
        name="operacion/detalle.html",
        context={
            "item": item, "titulo": "Detalle — Ausencia", "catalogo": "ausencias",
            "campos": [
                ("ID", item.id), ("Nombre", item.nombre),
                ("Justificada", item.is_justificada), ("Status", item.status),
            ],
        },
    )


# ─────────────────────────────────────────
# SERVICIOS
# ─────────────────────────────────────────
@router_operacion.get("/servicios", response_class=HTMLResponse)
def vista_servicios(
        request: Request,
        q: Optional[str] = None,
        page: int = 1,
        db: Session = Depends(get_db),
):
    resultado = listar_catalogo(
        db, Servicio,
        campos_busqueda=["clave", "descripcion"],
        q=q, page=page, page_size=50,
    )
    return templates.TemplateResponse(
        request=request,
        name="operacion/servicios_list.html",
        context={
            **resultado, "q": q,
            "titulo": "Servicios",
            "catalogo": "servicios",
        },
    )


@router_operacion.get("/servicios/{registro_id}", response_class=HTMLResponse)
def detalle_servicio(request: Request, registro_id: int, db: Session = Depends(get_db)):
    item = obtener_detalle(db, Servicio, registro_id)
    if not item:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    return templates.TemplateResponse(
        request=request,
        name="operacion/detalle.html",
        context={
            "item": item, "titulo": "Detalle — Servicio", "catalogo": "servicios",
            "campos": [
                ("ID", item.id), ("Clave", item.clave),
                ("Descripción", item.descripcion),
                ("Productividad", item.productividad),
                ("Tiempo (min)", item.tiempo),
                ("PDV", item.pdv),
                ("Req. autorización", item.requiere_autorizacion),
                ("Cliente ID", item.cliente_id),
                ("Status", item.status),
            ],
        },
    )