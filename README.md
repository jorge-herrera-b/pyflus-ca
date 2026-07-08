# flus-ca-unificado

Librería Python para correr el módulo CA de FLUS con **un solo archivo YAML**.

## Instalación

```cmd
cd C:\JORGE_HERRERA\PHD\LUC_MODELS\cambio_uso_2030\flus_ca_unificado
pip install -e .
```

## Opción A: crear el YAML desde tus archivos de FLUS GUI

```cmd
python -m flus_ca.cli convert-logs ^
  --log-simulation "C:\JORGE_HERRERA\PHD\LUC_MODELS\cambio_uso_2030\logFileSimulation.log" ^
  --config-mp "C:\JORGE_HERRERA\PHD\LUC_MODELS\cambio_uso_2030\FilesGenerate\config_mp.log" ^
  --output-yaml "C:\JORGE_HERRERA\PHD\LUC_MODELS\cambio_uso_2030\flus_config.yml"
```

## Opción B: usar la plantilla

Copia y edita:

```text
flus_config_template.yml
```

## Revisar que lee bien los parámetros

```cmd
python -m flus_ca.cli inspect --config "C:\JORGE_HERRERA\PHD\LUC_MODELS\cambio_uso_2030\flus_config.yml"
```

## Correr una simulación

```cmd
python -m flus_ca.cli run --config "C:\JORGE_HERRERA\PHD\LUC_MODELS\cambio_uso_2030\flus_config.yml"
```

## Correr lotes

Edita en el YAML:

```yaml
batch:
  enabled: true
```

y define los valores en:

```yaml
batch:
  vary:
    neighborhood_weights:
      Landuse3: [0.1, 0.5, 1.0]
      Landuse7: [0.1, 0.5, 1.0]
```

Luego:

```cmd
python -m flus_ca.cli batch --config "C:\JORGE_HERRERA\PHD\LUC_MODELS\cambio_uso_2030\flus_config.yml"
```

## Qué parámetros considera

- land use raster
- probability raster
- restricted raster
- output raster
- número de clases
- demanda futura por clase
- matriz de costo/conversión
- pesos de vecindad
- máximo de iteraciones
- tamaño de vecindad
- factor de aceleración
- enclaves
- thread, guardado como metadata aunque Numba maneja paralelización de otra forma
- seed
- tolerancia de parada
- iteraciones estables
- política DAREA/restricted value
- historia de iteraciones
- lotes de pesos de vecindad
