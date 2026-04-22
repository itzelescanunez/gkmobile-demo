from sqlalchemy import Column, BigInteger, String, Numeric, DateTime, Boolean, Integer, Date
from api.database import Base


class PreciosEatics(Base):
    __tablename__ = "v_precios_eatics"

    id              = Column(BigInteger, primary_key=True)
    promotor        = Column(String(255))
    supervisor      = Column(String(255))
    fecha           = Column(DateTime)
    anio_mes        = Column(String(7))
    producto        = Column(String(255))
    upc             = Column(String(255))
    categoria       = Column(String(255))
    presentacion    = Column(String(255))
    cadena          = Column(String(255))
    punto_venta     = Column(String(255))
    estado          = Column(String(255))
    precio          = Column(Numeric(19, 2))
    is_propio       = Column(Integer)
    producto_id     = Column(BigInteger)
    punto_venta_id  = Column(BigInteger)
    cadena_id       = Column(BigInteger)
    status          = Column(Boolean)


class AgotadosConProducto(Base):
    __tablename__ = "v_agotados_con_producto"

    ejecucion_id        = Column(BigInteger, primary_key=True)
    marca               = Column(String(255), primary_key=True)
    punto_venta_id      = Column(BigInteger, primary_key=True)
    producto_en_riesgo  = Column(String(255), primary_key=True)
    punto_venta         = Column(String(255))
    estado              = Column(String(255))
    cadena              = Column(String(255))
    fecha               = Column(Date)
    cant_agotados       = Column(Integer)
    cant_preagotados    = Column(Integer)
    inventario          = Column(Numeric(19, 2))
    marca_producto      = Column(String(255))