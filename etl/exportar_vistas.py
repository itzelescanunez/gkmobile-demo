import csv
from api.database import engine
from sqlalchemy import text

# Lista exacta de tus vistas obtenida de la terminal
VISTAS = [
    "v_agotados_con_producto",
    "v_agotados_eatics",
    "v_detalle_venta_cero",
    "v_ejecucion_eatics",
    "v_operacion_promotores",
    "v_precios_eatics",
    "v_reporte_marca_pdv"
]

def exportar_vistas_especificas():
    try:
        # Iniciamos la conexión con el engine de tu database.py
        with engine.connect() as connection:
            print(f"🚀 Iniciando exportación masiva de {len(VISTAS)} vistas...\n")

            for vista in VISTAS:
                archivo_csv = f"{vista}.csv"
                print(f"⏳ Procesando: {vista}...", end=" ", flush=True)

                try:
                    # Ejecutamos la consulta a la vista
                    # Usamos text() para asegurar compatibilidad con SQLAlchemy
                    result = connection.execute(text(f"SELECT * FROM {vista}"))

                    # Abrimos el archivo para escribir
                    with open(archivo_csv, 'w', newline='', encoding='utf-8-sig') as f:
                        writer = csv.writer(f)

                        # 1. Escribir encabezados
                        writer.writerow(result.keys())

                        # 2. Escribir datos por bloques de 10,000 para cuidar la RAM
                        contador_filas = 0
                        while True:
                            chunk = result.fetchmany(10000)
                            if not chunk:
                                break
                            writer.writerows(chunk)
                            contador_filas += len(chunk)

                    print(f"✅ [OK] {contador_filas} filas guardadas.")

                except Exception as e_vista:
                    print(f"❌ [ERROR] No se pudo exportar {vista}: {e_vista}")

            print("\n✨ ¡Proceso finalizado! Todos los archivos CSV están en tu carpeta.")

    except Exception as e_global:
        print(f"❌ Error crítico de conexión: {e_global}")

if __name__ == "__main__":
    exportar_vistas_especificas()