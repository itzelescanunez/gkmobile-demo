import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import re
import os

OUTPUT_DIR = "parquet"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def parsear_insert(line):
    match = re.search(r"INSERT INTO `\w+` VALUES (.+);$", line.strip())
    if not match:
        return []
    values_str = match.group(1)
    rows = []
    for row_match in re.finditer(r"\(([^()]*(?:\([^()]*\)[^()]*)*)\)", values_str):
        raw = row_match.group(1)
        campos = re.findall(
            r"_binary\s+'[^']*'"   # _binary con cualquier byte
            r"|'(?:[^'\\]|\\.)*'"  # strings normales
            r"|NULL"               # NULL
            r"|-?\d+(?:\.\d+)?",   # números
            raw
        )
        fila = []
        for c in campos:
            c = c.strip()
            if c == "NULL":
                fila.append(None)
            elif c.startswith("_binary"):
                inner = c.split("'", 1)[1].rstrip("'")
                fila.append(0 if inner in ("", "\x00") else 1)
            elif c.startswith("'") and c.endswith("'"):
                fila.append(c[1:-1].replace("\\'", "'").replace("\\\\", "\\"))
            else:
                try:
                    fila.append(int(c))
                except ValueError:
                    try:
                        fila.append(float(c))
                    except ValueError:
                        fila.append(c)
        if fila:
            rows.append(fila)
    return rows

def extraer_columnas(sql_path):
    """Lee el CREATE TABLE y devuelve lista de columnas"""
    cols = []
    dentro = False
    with open(sql_path, "r", errors="replace") as f:
        for line in f:
            if "CREATE TABLE" in line:
                dentro = True
                continue
            if dentro:
                if line.strip().startswith(")"):
                    break
                col_match = re.match(r"\s+`(\w+)`\s+", line)
                if col_match and not any(k in line.upper() for k in ["PRIMARY", "KEY", "CONSTRAINT", "UNIQUE"]):
                    cols.append(col_match.group(1))
    return cols

def convertir(nombre, chunk_size=50_000):
    path = f"sql_raw/{nombre}.sql"
    print(f"\n📂 Procesando {nombre}.sql ({os.path.getsize(path)/1_048_576:.1f} MB)...")

    columnas = extraer_columnas(path)
    n_cols = len(columnas)
    print(f"  Columnas ({n_cols}): {columnas}")

    writer = None
    schema = None
    buffer = []
    total = 0
    descartadas = 0

    cols_numericas = [
        # Generales
        'id', 'version', 'cliente_id', 'usuario_id', 'cuadrilla_id',
        'ausencia_id', 'usuario_ultimo_id', 'cadena_id', 'estado_id',
        'municipio_id', 'formato_id', 'formato_cadena_id', 'status',
        'tipo_localizacion', 'is_proyecto', 'clasificacion', 'is_bimsa',
        'punto_venta_id', 'producto_id', 'canal_id',
        # Temporales
        'anio', 'mes',
        # Sell-out / Inventario Procesa
        'monto', 'piezas', 'precio', 'venta',
        'existencia', 'dias_inventario', 'dias_transcurridos',
        'agotados', 'cob_exh', 'frentes', 'frentes_lata', 'frentes_pouch',
        'frentes_comp_lata', 'frentes_comp_pouch',
        'sos_anaquel', 'sos_lata', 'sos_pouch',
        # Producto
        'peso', 'precio_unitario', 'cant_pza', 'padre_id',
    ]

    def chunk_a_parquet(buf):
        nonlocal writer, schema
        df = pd.DataFrame(buf, columns=columnas)

        for col in df.columns:
            if col in cols_numericas:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            else:
                df[col] = df[col].where(df[col].notna(), other=None)
                df[col] = df[col].apply(lambda x: str(x) if x is not None else None)

        if schema is None:
            tabla_tmp = pa.Table.from_pandas(df, preserve_index=False)
            new_fields = [
                pa.field(f.name, pa.large_utf8()) if f.type == pa.null() else f
                for f in tabla_tmp.schema
            ]
            schema = pa.schema(new_fields)
            writer = pq.ParquetWriter(f"{OUTPUT_DIR}/{nombre}.parquet", schema, compression="snappy")

        arrays = []
        for field in schema:
            col_data = df[field.name].tolist()
            arrays.append(pa.array(col_data, type=field.type, from_pandas=True))

        tabla = pa.table(dict(zip(schema.names, arrays)), schema=schema)
        writer.write_table(tabla)

    with open(path, "rb") as f:
        for line in f:
            line = line.decode("latin-1")
            if not line.startswith("INSERT"):
                continue
            rows = parsear_insert(line)
            for row in rows:
                if len(row) == n_cols:
                    buffer.append(row)
                else:
                    descartadas += 1

            if len(buffer) >= chunk_size:
                chunk_a_parquet(buffer)
                total += len(buffer)
                print(f"  ✓ {total:,} filas escritas...")
                buffer = []

    if buffer:
        chunk_a_parquet(buffer)
        total += len(buffer)

    if writer:
        writer.close()

    size_mb = os.path.getsize(f"{OUTPUT_DIR}/{nombre}.parquet") / 1_048_576
    print(f"  ✅ {nombre}.parquet — {total:,} filas · {size_mb:.1f} MB")
    if descartadas:
        print(f"  ⚠️  Filas descartadas: {descartadas:,}")

# Tablas pequeñas primero
for tabla in ["canal_procesa", "producto_procesa", "cadena"]:
    convertir(tabla)

# Tablas medianas
#for tabla in ["punto_venta"]:
    #convertir(tabla)

# Tabla grande
convertir("detalle_sell_out_procesa", chunk_size=100_000)
convertir("detalle_inventario_procesa", chunk_size=100_000)

print("\n✅ Todo listo en parquet/")
