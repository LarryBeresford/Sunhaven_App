# Alcance MVP — SunHaven Operations Intelligence

## Incluido

- Dashboard de Operaciones.
- Gestión de Nómina e incidencias.
- Auditoría de rondines nocturnos y alertas de integridad.
- Propuestas Kaizen mensuales.
- Reportes PDF de Operaciones, Nómina y Rondines.

## Fuera de alcance por ahora

- Cumplimiento legal y normativo.
- Inicio de sesión y roles.
- Alertas automáticas por correo.
- Regla de personal evaluado exclusivamente por horas semanales.

## Fuente de verdad

Mientras se realiza la modularización, `app.py` es el único punto de entrada
de la aplicación. Los scripts dentro de `scripts/` son herramientas manuales
de soporte y no forman parte del servidor Streamlit.
