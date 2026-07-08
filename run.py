from pathlib import Path
import sys

# Carpeta donde está la librería
ruta_libreria = r"C:\JORGE_HERRERA\PHD\LUC_MODELS\pyflus\flus_ca_unificado"

# Agregar la librería manualmente al path de Python
sys.path.insert(0, ruta_libreria)

# Ahora sí importar
from flus_ca import FLUSCA

# YAML ya creado
yaml_path = Path(r"C:\JORGE_HERRERA\PHD\LUC_MODELS\pyflus\flus_ca_unificado\flus_config_template.yml")

# Crear modelo
model = FLUSCA(yaml_path)

# Revisar qué está leyendo
model.print_inspect()

# Correr simulación
model.run(verbose=True)

# Guardar raster
model.save()

# Guardar historia de iteraciones si está definida en el YAML
model.save_history_csv()

print("Simulación terminada")
print("Conteos finales:", model.counts.tolist())
#%%
from pathlib import Path
import numpy as np
import rasterio
import pandas as pd

# Rutas
entrada = Path(r"C:\JORGE_HERRERA\PHD\LUC_MODELS\cambio_uso_2030\input_flus\LC_2018_ND.tif")
salida = Path(r"C:\JORGE_HERRERA\PHD\LUC_MODELS\cambio_uso_2030\simulaciones_python\sim_test.tif")

# Leer rasters
with rasterio.open(entrada) as src:
    arr_in = src.read(1)
    profile = src.profile

with rasterio.open(salida) as src:
    arr_out = src.read(1)

# Verificar dimensiones
print("Dimensión entrada:", arr_in.shape)
print("Dimensión salida:", arr_out.shape)

if arr_in.shape != arr_out.shape:
    raise ValueError("Los raster no tienen la misma dimensión")

# Máscara de píxeles válidos
validos = arr_in > 0

# Comparar cambios
cambios = (arr_in != arr_out) & validos

n_validos = np.sum(validos)
n_cambios = np.sum(cambios)
porcentaje_cambio = n_cambios / n_validos * 100

print("Píxeles válidos:", n_validos)
print("Píxeles cambiados:", n_cambios)
print("Porcentaje cambiado:", round(porcentaje_cambio, 4), "%")

# Conteo por clase antes y después
clases = sorted(np.unique(arr_in[validos]))

tabla = []

for clase in clases:
    inicial = np.sum(arr_in == clase)
    final = np.sum(arr_out == clase)
    diferencia = final - inicial
    
    tabla.append({
        "clase": int(clase),
        "inicial": int(inicial),
        "final": int(final),
        "diferencia": int(diferencia)
    })

df = pd.DataFrame(tabla)

print("\nConteo por clase:")
print(df)

# Guardar tabla
df.to_csv(
    r"C:\JORGE_HERRERA\PHD\LUC_MODELS\cambio_uso_2030\simulaciones_python\comparacion_entrada_salida.csv",
    index=False
)