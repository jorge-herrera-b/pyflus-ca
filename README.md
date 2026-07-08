# pyflus-ca

Python implementation of the cellular automata (CA)-based self-adaptive inertia and competition mechanism module of the land-use simulation model (FLUS; Liu et al., 2017): a model for future land-use allocation. The source code is available at: https://geosimulation.cn/FLUS-source-code.html

This repository provides a research-oriented Python workflow to run land-use change simulations without opening the GeoSOS-FLUS graphical interface.

The model reads:

- initial land-use raster;
- probability-of-occurrence raster;
- restricted-area raster;
- future land-use demand;
- conversion / cost matrix;
- neighborhood weights;
- CA simulation parameters;
- output path.

## Important note

This is **not an official GeoSOS-FLUS release**.

This implementation is inspired by the FLUS CA simulation workflow and by inspection of the original FLUS CA source-code structure. It is intended for research, experimentation, reproducibility, and batch simulations.

It does **not** implement the ANN probability-of-occurrence module. Therefore, the probability raster must already exist before running the CA simulation.

Because the original FLUS implementation uses C++ and its own random process, this Python version should not be expected to reproduce GeoSOS-FLUS outputs pixel-by-pixel. The recommended validation is to compare:

- final class counts;
- changed pixels;
- transition matrix;
- spatial agreement against a reference raster, if available.

## Methodological basis

The implementation follows the structure of the GeoSOS-FLUS self-adaptive inertia and competition mechanism CA module. In the original FLUS workflow, the CA module uses:

- land-use pattern;
- probability-of-occurrence data;
- restricted-area data;
- future land-use demand;
- cost / conversion matrix;
- neighborhood weights;
- maximum number of iterations;
- neighborhood size;
- acceleration factor.

The original GeoSOS-FLUS model is described in:

```text
Liu, X., Liang, X., Li, X., Xu, X., Ou, J., Chen, Y., Li, S., Wang, S., & Pei, F. (2017).
A future land use simulation model (FLUS) for simulating multiple land use scenarios
by coupling human and natural effects.
Landscape and Urban Planning, 168, 94–116.
```
Furthermore, this Python implementation was used for the following publication:
```text
Herrera-Benavides, J., Galleguillos, M., & O’Ryan, R. (2026). A spatial simulation framework for afforestation policy assessment in Chile: accounting for uncertainty in projected land-use change and hydrological risk. Research Square. https://doi.org/10.21203/rs.3.rs-9520764/v1
```
