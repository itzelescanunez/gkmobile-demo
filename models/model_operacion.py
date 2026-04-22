from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, Integer, Numeric
from api.database import Base


class Promotor(Base):
    __tablename__ = "user"

    id                  = Column(BigInteger, primary_key=True)
    username            = Column(String(255))
    user_real_name      = Column(String(255))
    email               = Column(String(255))
    perfil              = Column(Integer)
    cuadrilla_id        = Column(BigInteger)
    cliente_id          = Column(BigInteger)
    telefono            = Column(String(255))
    last_login          = Column(DateTime)
    fecha_creacion      = Column(DateTime)
    enabled             = Column(Boolean)
    status              = Column(Boolean)


class Cuadrilla(Base):
    __tablename__ = "cuadrilla"

    id                  = Column(BigInteger, primary_key=True)
    nombre              = Column(String(255))
    entidad             = Column(String(255))
    puesto              = Column(String(255))
    agencia             = Column(String(255))
    region              = Column(String(255))
    plaza               = Column(String(255))
    ruta                = Column(String(255))
    tipo                = Column(Integer)
    fecha_creacion      = Column(DateTime)
    fecha_actualizacion = Column(DateTime)
    status              = Column(Boolean)


class JornadaDiaria(Base):
    __tablename__ = "jornada_diaria"

    id                  = Column(BigInteger, primary_key=True)
    usuario_id          = Column(BigInteger)
    cuadrilla_id        = Column(BigInteger)
    cliente_id          = Column(BigInteger)
    fecha               = Column(DateTime)
    incidencia          = Column(String(255))
    tipo                = Column(Integer)
    ausencia_id         = Column(BigInteger)
    fecha_creacion      = Column(DateTime)
    fecha_actualizacion = Column(DateTime)
    status              = Column(Boolean)


class Ausencia(Base):
    __tablename__ = "ausencia"

    id              = Column(BigInteger, primary_key=True)
    nombre          = Column(String(255))
    is_justificada  = Column(Boolean)
    status          = Column(Boolean)


class Servicio(Base):
    __tablename__ = "servicio"

    id                      = Column(BigInteger, primary_key=True)
    clave                   = Column(String(255))
    descripcion             = Column(String(255))
    productividad           = Column(Numeric(19, 5))
    tiempo                  = Column(Integer)
    pdv                     = Column(Boolean)
    requiere_autorizacion   = Column(Boolean)
    cliente_id              = Column(BigInteger)
    fecha_creacion          = Column(DateTime)
    fecha_actualizacion     = Column(DateTime)
    status                  = Column(Boolean)