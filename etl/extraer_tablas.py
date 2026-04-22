import sys
import re
import os
import subprocess

TABLAS = {
    'user_cliente', 'jornada_diaria', 'actividad',
    'ausencia', 'ausencia_usuario', 'cliente',
    'user', 'cuadrilla', 'punto_venta',
    # Procesa
    'detalle_sell_out_procesa',
    'detalle_inventario_procesa',
    'producto_procesa',
    'canal_procesa',
    'cadena',
}

os.makedirs("etl/sql_raw", exist_ok=True)

# Encuentra el tar
tar_path = "data/raw/" + os.listdir("data/raw")[0]
print(f"Leyendo: {tar_path}")

archivos = {}
tabla_actual = None
capturando = False

proc = subprocess.Popen(["tar", "-xOf", tar_path], stdout=subprocess.PIPE, text=True, errors="replace")

for i, line in enumerate(proc.stdout):
    if i % 500_000 == 0:
        print(f"  Líneas procesadas: {i:,}")

    match_create = re.match(r"CREATE TABLE `(\w+)`", line)
    if match_create:
        tabla_actual = match_create.group(1)
        capturando = tabla_actual in TABLAS
        if capturando and tabla_actual not in archivos:
            archivos[tabla_actual] = open(f"sql_raw/{tabla_actual}.sql", "w")

    match_insert = re.match(r"INSERT INTO `(\w+)`", line)
    if match_insert:
        tabla_actual = match_insert.group(1)
        capturando = tabla_actual in TABLAS
        if capturando and tabla_actual not in archivos:
            archivos[tabla_actual] = open(f"sql_raw/{tabla_actual}.sql", "w")

    if capturando and tabla_actual in TABLAS:
        archivos[tabla_actual].write(line)

for f in archivos.values():
    f.close()

print("\nTablas extraídas:")
for t in archivos:
    size = os.path.getsize(f"sql_raw/{t}.sql") / 1_048_576
    print(f"  {t}.sql  ({size:.1f} MB)")
