# pyflus-corregido 0.3.0

Implementación Python del módulo de autómata celular (CA) de `FLUS_console`.
Consume un mapa inicial y un GeoTIFF multibanda de probabilidades de ocurrencia.
No entrena la red neuronal original de `nntrain.cpp`; las probabilidades pueden
provenir de FLUS, FT-Transformer u otro modelo de idoneidad.

## Correcciones de esta versión

- DAREA está desactivado por defecto, igual que en el proyecto Visual C++ entregado.
- Criterio de parada alineado con `simulationprocess.cpp`.
- Verificación de CRS, transformación, dimensiones y número de bandas.
- Validación de códigos contiguos `1..n_types`, matrices y vecindad impar.
- Rechazo de probabilidades negativas, NaN o infinitas.
- Control real del número de hilos de Numba mediante `simulation.thread`.
- Demanda multihorizonte opcional mediante `simulation.demand_schedule`.
- Registro del período en el CSV de historia.
- DAREA permanece disponible como variante explícita.

Los resultados no serán idénticos píxel a píxel al C++ porque NumPy/Numba y
`rand()` usan generadores aleatorios diferentes. Sí se conserva la estructura
algorítmica: idoneidad, vecindad, inercia adaptativa, matriz de conversión,
ruleta y control de demanda.

`enclaves_for_landuse_type` se conserva para compatibilidad con los logs, pero
el `simulationprocess.cpp` suministrado tampoco lo usa en la asignación CA.

## Instalación

```powershell
cd C:\ruta\a\pyflus_corregido
python -m pip install -e .
```

Para instalar y ejecutar las pruebas:

```powershell
python -m pip install -e ".[test]"
pytest -q
```

## Uso

Copie `flus_config_template.yml`, edite rutas, demanda, matriz y pesos, y ejecute:

```powershell
flus-ca inspect --config C:\ruta\flus_config.yml
flus-ca run --config C:\ruta\flus_config.yml
```

También funciona sin el comando instalado:

```powershell
python -m flus_ca.cli run --config C:\ruta\flus_config.yml
```

## Bandas de probabilidades

El GeoTIFF debe contener exactamente `n_types` bandas. La banda 1 corresponde
a la clase 1, la banda 2 a la clase 2, y así sucesivamente. Todos los rásteres
deben compartir la misma grilla geoespacial.

## Demanda multihorizonte

Si `demand_schedule` existe y no está vacío, reemplaza `future_pixels`:

```yaml
simulation:
  demand_schedule:
    - period: 2025
      future_pixels: [1000, 2000, 3000]
    - period: 2030
      future_pixels: [900, 2100, 3000]
```

Cada horizonte parte del mapa obtenido en el anterior y reinicia la inercia.
Se usa `seed + índice_del_período` para que la ejecución sea reproducible.

## DAREA

El proyecto `FLUS_console.vcxproj` revisado no define la macro `DAREA`; use:

```yaml
hyperparameters:
  darea:
    enabled: false
```

Actívela solamente si desea la variante que favorece una clase objetivo cuando
el ráster restringido contiene un valor especial.
