from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, Integer, Numeric, Text
from api.database import Base


class EjecucionMarcaEatics(Base):
    __tablename__ = "ejecucion_marca_eatics"

    id                  = Column(BigInteger, primary_key=True, index=True)
    nombre_marca        = Column(String(255))
    fecha               = Column(DateTime)
    user_real_name      = Column(String(255))
    supervisor          = Column(String(255))
    agotados            = Column(String(255))
    preagotados         = Column(String(255))
    cant_sku            = Column(Integer)
    cant_agotados       = Column(Integer)
    cant_preagotados    = Column(Integer)
    con_agotados        = Column(Boolean)
    con_preagotados     = Column(Boolean)
    planograma          = Column(Boolean)
    negocicacion        = Column(Boolean)
    is_degustacion      = Column(Boolean)
    caducidad           = Column(Boolean)
    retiro              = Column(Boolean)
    punto_venta_id      = Column(BigInteger)
    cadena_id           = Column(BigInteger)
    cuadrilla_id        = Column(BigInteger)
    cliente_id          = Column(BigInteger)
    status              = Column(Boolean)


class EjecucionPdvEatics(Base):
    __tablename__ = "ejecucion_pdv_eatics"

    id                  = Column(BigInteger, primary_key=True, index=True)
    fecha               = Column(DateTime)
    user_real_name      = Column(String(255))
    supervisor          = Column(String(255))
    acomodo             = Column(Boolean)
    incidencias         = Column(String(255))
    ini_degus           = Column(Boolean)
    is_degustacion      = Column(Boolean)
    material_degus      = Column(String(255))
    piezas_degus        = Column(Integer)
    sepresento          = Column(Boolean)
    sedespidio          = Column(Boolean)
    telson              = Column(Boolean)
    punto_venta_id      = Column(BigInteger)
    cadena_id           = Column(BigInteger)
    cuadrilla_id        = Column(BigInteger)
    cliente_id          = Column(BigInteger)
    status              = Column(Boolean)


class AuditoriaMarcaEatics(Base):
    __tablename__ = "auditoria_marca_eatics"

    id                  = Column(BigInteger, primary_key=True, index=True)
    fecha               = Column(DateTime)
    nombre_marca        = Column(String(255))
    user_real_name      = Column(String(255))
    supervisor          = Column(String(255))
    cumple_reportado    = Column(Boolean)
    planograma          = Column(Boolean)
    is_degustacion      = Column(Boolean)
    punto_venta_id      = Column(BigInteger)
    cadena_id           = Column(BigInteger)
    cuadrilla_id        = Column(BigInteger)
    cliente_id          = Column(BigInteger)
    marca_id            = Column(BigInteger)
    status              = Column(Boolean)


class PreciosEatics(Base):
    __tablename__ = "precios_eatics"

    id                  = Column(BigInteger, primary_key=True, index=True)
    fecha               = Column(DateTime)
    user_real_name      = Column(String(255))
    supervisor          = Column(String(255))
    precio              = Column(Numeric(19, 2))
    is_propio           = Column(Boolean)
    producto_id         = Column(BigInteger)
    categoria_id        = Column(BigInteger)
    presentacion_id     = Column(BigInteger)
    punto_venta_id      = Column(BigInteger)
    cadena_id           = Column(BigInteger)
    cuadrilla_id        = Column(BigInteger)
    cliente_id          = Column(BigInteger)
    status              = Column(Boolean)


class CompetenciaEatics(Base):
    __tablename__ = "competencia_eatics"

    id                  = Column(BigInteger, primary_key=True, index=True)
    fecha               = Column(DateTime)
    user_real_name      = Column(String(255))
    supervisor          = Column(String(255))
    marca               = Column(String(255))
    precio_obs          = Column(String(255))
    tipo_promo          = Column(String(255))
    desc_promo          = Column(String(255))
    frentes             = Column(String(255))
    comentario          = Column(String(255))
    punto_venta_id      = Column(BigInteger)
    cadena_id           = Column(BigInteger)
    cuadrilla_id        = Column(BigInteger)
    cliente_id          = Column(BigInteger)
    status              = Column(Boolean)

