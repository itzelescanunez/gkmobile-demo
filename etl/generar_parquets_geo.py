import duckdb
import os

con = duckdb.connect()

clientes = {
    26:  "procesa",
    102: "castel",
    141: "clip",
    149: "eatics",
    1:   "philip_morris",
    132: "danone",
    142: "rabbit",
    127: "xiaomi",
}

def limpiar_encoding(col):
    return f"""regexp_replace(
        regexp_replace(
        regexp_replace(
        regexp_replace(
        regexp_replace(
        regexp_replace(
        regexp_replace(
        regexp_replace(
        regexp_replace(
        regexp_replace(
        regexp_replace(
        regexp_replace(
        regexp_replace(
        regexp_replace(
            {col},
            'Ã©',   'é'),
            'Ã³',   'ó'),
            'Ã¡',   'á'),
            'Ã­',   'í'),
            'Ãº',   'ú'),
            'Ã±',   'ñ'),
            'ÃÂ©',  'é'),
            'ÃÂ³',  'ó'),
            'ÃÂ¡',  'á'),
            'ÃÂ­',  'í'),
            'ÃÂº',  'ú'),
            'ÃÂ',   'Á'),
            'Ã',    'Á'),
            'Â',    '')"""

ESTADOS_NORM = {
    "DISTRITO FEDERAL":    "Ciudad de México",
    "Distrito Federal":    "Ciudad de México",
    "CIUDAD DE MEXICO":    "Ciudad de México",
    "Ciudad de Mexico":    "Ciudad de México",
    "CDMX":                "Ciudad de México",
    "cdmx":                "Ciudad de México",
    "CMDX":                "Ciudad de México",
    "CIDAD DE MEXICO":     "Ciudad de México",
    "EDO. DE MEXICO":      "Estado de México",
    "ESTADO DE MEXICO":    "Estado de México",
    "Estado de Mexico":    "Estado de México",
    "MEXICO":              "Estado de México",
    "Mexico":              "Estado de México",
    "México":              "Estado de México",
    "MÉXICO":              "Estado de México",
    "San Luis Potosi":     "San Luis Potosí",
    "Nuevo Leon":          "Nuevo León",
    "JALISCO":             "Jalisco",
    "GUANAJUATO":          "Guanajuato",
    "PUEBLA":              "Puebla",
    "CHIAPAS":             "Chiapas",
    "SINALOA":             "Sinaloa",
    "NAYARIT":             "Nayarit",
    "MORELOS":             "Morelos",
    "TABASCO":             "Tabasco",
    "SONORA":              "Sonora",
    "COLIMA":              "Colima",
    "QUINTANA ROO":        "Quintana Roo",
    "YUCATAN":             "Yucatán",
    "QUERETARO":           "Querétaro",
    "CAMPECHE":            "Campeche",
    "NUEVOLEON":           "Nuevo León",
    "BCS":                 "Baja California Sur",
}

CADENAS_NORM = {
    "WALMART":             "Walmart",
    "SORIANA":             "Soriana",
    "CHEDRAUI":            "Chedraui",
    "SAMS":                "Sam''s Club",
    "SAMS CLUB":           "Sam''s Club",
    "HEB":                 "HEB",
    "LA COMER":            "La Comer",
    "COMERCIAL MEXICANA":  "Comercial Mexicana",
    "COSTCO":              "Costco",
    "CASA LEY":            "Casa Ley",
    "ALSUPER":             "Alsuper",
    "CALIMAX":             "Calimax",
    "MI TIENDA":           "Mi Tienda",
    "OPERADORA MERCO":     "Operadora Merco",
    "TIENDA AMIGA":        "Tienda Amiga",
    "HOME OFFICE":         "Home Office",
    "AGENCIA":             "Agencia",
    "ACTIVIDAD":           "Actividad",
    "7 ELEVEN":            "7-Eleven",
}

MUNICIPIOS_NORM = {
    "TUXTLA GUTIERREZ":           "Tuxtla Gutiérrez",
    "Tuxtla Gutierrez":           "Tuxtla Gutiérrez",
    "CUAUHTEMOC":                 "Cuauhtémoc",
    "Cuauhtemoc":                 "Cuauhtémoc",
    "cuauhtemoc":                 "Cuauhtémoc",
    "CUAHTEMOC":                  "Cuauhtémoc",
    "Cuahtemoc":                  "Cuauhtémoc",
    "BENITO JUAREZ":              "Benito Juárez",
    "Benito Juarez":              "Benito Juárez",
    "benito juarez":              "Benito Juárez",
    "TONALA":                     "Tonalá",
    "Tonala":                     "Tonalá",
    "CUAJIMALPA DE MORELOS":      "Cuajimalpa de Morelos",
    "CUAJIMALPA":                 "Cuajimalpa",
    "NEZAHUALCOYOTL":             "Nezahualcóyotl",
    "Nezahualcoyotl":             "Nezahualcóyotl",
    "SAN CRISTOBAL DE LAS CASAS": "San Cristóbal de las Casas",
    "NAUCALPAN DE JUAREZ":        "Naucalpan de Juárez",
    "Naucalpan De Juarez":        "Naucalpan de Juárez",
    "GENERAL ESCOBEDO":           "General Escobedo",
    "LOS REYES LA PAZ":           "Los Reyes La Paz",
    "ATIZAPAN":                   "Atizapán",
    "Atizapan":                   "Atizapán",
    "SAN JOSE DEL CABO":          "San José del Cabo",
    "San Jose del Cabo":          "San José del Cabo",
    "San Jose del cabo":          "San José del Cabo",
    "GOMEZ PALACIO":              "Gómez Palacio",
    "Gomez Palacio":              "Gómez Palacio",
    "SAN ANDRES CHOLULA":         "San Andrés Cholula",
    "San Andres Cholula":         "San Andrés Cholula",
    "NICOLAS ROMERO":             "Nicolás Romero",
    "Nicolas Romero":             "Nicolás Romero",
    "NAUCALPAN":                  "Naucalpan",
    "CUAUTITLAN IZCALLI":         "Cuautitlán Izcalli",
    "Cuautitlan Izcalli":         "Cuautitlán Izcalli",
    "TECAMAC":                    "Tecámac",
    "Tecamac":                    "Tecámac",
    "SAN NICOLAS DE LOS GARZA":   "San Nicolás de los Garza",
    "San Nicolas De Los Garza":   "San Nicolás de los Garza",
    "SOLEDAD DE GRACIANO SANCHEZ":"Soledad de Graciano Sánchez",
    "Soledad de Graciano Sanchez":"Soledad de Graciano Sánchez",
    "CIUDAD DE MEXICO":           "Ciudad de México",
    "Ciudad De Mexico":           "Ciudad de México",
    "AZCAPOTZALCO":               "Azcapotzalco",
    "QUERETARO":                  "Querétaro",
    "CANCUN":                     "Cancún",
    "Cancun":                     "Cancún",
    "IXTAPALUCA":                 "Ixtapaluca",
    "ixtapaluca":                 "Ixtapaluca",
    "LOS CABOS":                  "Los Cabos",
    "Los cabos":                  "Los Cabos",
    "LEON":                       "León",
    "MERIDA":                     "Mérida",
}

def sql_estado(col):
    col_limpio = limpiar_encoding(col)
    cases = "\n".join([
        f"            WHEN TRIM({col_limpio}) = '{k}' THEN '{v}'"
        for k, v in ESTADOS_NORM.items()
    ])
    return f"""
        CASE
{cases}
            WHEN {col} IS NULL
              OR TRIM({col}) IN ('', 'nan', 'S/A')
              OR LENGTH(TRIM({col})) <= 2
              OR regexp_matches(TRIM({col}), '^[0-9]+$')
              THEN NULL
            ELSE TRIM({col_limpio})
        END"""

def sql_municipio(col):
    col_limpio = limpiar_encoding(col)
    cases = "\n".join([
        f"            WHEN TRIM({col_limpio}) = '{k}' THEN '{v}'"
        for k, v in MUNICIPIOS_NORM.items()
    ])
    return f"""
        CASE
{cases}
            WHEN {col} IS NULL
              OR TRIM({col}) IN ('', 'nan', 'S/A')
              THEN NULL
            ELSE TRIM({col_limpio})
        END"""

def sql_cadena(col):
    cases = "\n".join([
        f"            WHEN UPPER(TRIM({col})) = '{k}' THEN '{v}'"
        for k, v in CADENAS_NORM.items()
    ])
    return f"""
        CASE
{cases}
            WHEN {col} IS NULL
              OR TRIM({col}) IN ('', 'nan')
              THEN NULL
            ELSE TRIM({col})
        END"""

os.makedirs("data/parquet/geo", exist_ok=True)

print(f"\n{'Cliente':<20} {'Filas':>10} {'MB':>8} {'Min':>12} {'Max':>12}")
print("="*68)

total = 0
for cliente_id, nombre in clientes.items():
    path = f"data/parquet/geo/actividad_geo_{nombre}.parquet"
    con.execute(f"""
        COPY (
            SELECT
                a.cliente_id,
                a.usuario_id,
                a.cuadrilla_id,
                CAST(a.fecha_planeada AS DATE)             AS dia,
                a.punto_venta_id,
                TRY_CAST(a.fecha_real_inicio AS TIMESTAMP) AS hora_checkin,
                TRY_CAST(a.latitude_check_in AS DOUBLE)    AS lat_checkin,
                TRY_CAST(a.longitude_check_in AS DOUBLE)   AS lon_checkin,
                TRY_CAST(a.latitude_pdv AS DOUBLE)         AS lat_pdv,
                TRY_CAST(a.longitude_pdv AS DOUBLE)        AS lon_pdv,
                TRY_CAST(a.is_no_planeada AS INT)          AS es_fuera_ruta,
                pv.sucursal,
                {sql_cadena('pv.cadena_str')}               AS cadena,
                {sql_estado('pv.estado_str')}               AS estado,
                {sql_municipio('pv.municipio_str')}         AS municipio,
                COALESCE(NULLIF(TRIM(c.ruta),    ''), NULL) AS ruta,
                COALESCE(NULLIF(TRIM(c.entidad), ''), NULL) AS entidad,
                COALESCE(NULLIF(TRIM(c.region),  ''), NULL) AS region,
                COALESCE(NULLIF(TRIM(c.plaza),   ''), NULL) AS plaza
            FROM read_parquet('data/parquet/global/actividad.parquet') a
            LEFT JOIN read_parquet('data/parquet/global/punto_venta.parquet') pv
                ON pv.id = TRY_CAST(a.punto_venta_id AS BIGINT)
            LEFT JOIN read_parquet('data/parquet/global/cuadrilla.parquet') c
                ON c.id = a.cuadrilla_id
            WHERE a.cliente_id = {cliente_id}
              AND a.fecha_real_inicio IS NOT NULL
              AND YEAR(CAST(a.fecha_planeada AS DATE)) BETWEEN 2015 AND 2026
              AND TRY_CAST(a.latitude_check_in AS DOUBLE) IS NOT NULL
              AND NOT isnan(TRY_CAST(a.latitude_check_in AS DOUBLE))
              AND TRY_CAST(a.longitude_check_in AS DOUBLE) IS NOT NULL
              AND NOT isnan(TRY_CAST(a.longitude_check_in AS DOUBLE))
              AND TRY_CAST(a.latitude_pdv AS DOUBLE) IS NOT NULL
              AND TRY_CAST(a.longitude_pdv AS DOUBLE) IS NOT NULL
        ) TO '{path}'
        (FORMAT PARQUET, COMPRESSION SNAPPY)
    """)
    size = os.path.getsize(path) / 1_048_576
    r    = con.execute(f"""
        SELECT COUNT(*), MIN(dia), MAX(dia)
        FROM read_parquet('{path}')
    """).fetchone()
    total += size
    print(f"  {nombre:<18} {r[0]:>10,} {size:>7.1f} MB {str(r[1]):>12} {str(r[2]):>12}")

print("="*68)
print(f"  {'TOTAL':<18} {'':>10} {total:>7.1f} MB")

print("\n=== Verificación cadenas (procesa) ===")
print(con.execute("""
    SELECT cadena, COUNT(*) as visitas
    FROM read_parquet('data/parquet/geo/actividad_geo_procesa.parquet')
    WHERE cadena IS NOT NULL
    GROUP BY cadena ORDER BY visitas DESC LIMIT 15
""").df().to_string())

print("\n=== Verificación estados (procesa) ===")
print(con.execute("""
    SELECT estado, COUNT(*) as visitas
    FROM read_parquet('data/parquet/geo/actividad_geo_procesa.parquet')
    WHERE estado IS NOT NULL
    GROUP BY estado ORDER BY visitas DESC
""").df().to_string())

print("\n=== Municipios con encoding roto (procesa) ===")
print(con.execute("""
    SELECT COUNT(*) as municipios_rotos
    FROM (SELECT DISTINCT municipio
          FROM read_parquet('data/parquet/geo/actividad_geo_procesa.parquet'))
    WHERE municipio LIKE '%Ã%' OR municipio LIKE '%ÃÂ%'
""").df().to_string())
