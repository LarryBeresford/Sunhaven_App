# SunHaven Operations Intelligence

Plataforma de inteligencia operativa para una residencia de adultos mayores.
Consolida datos de asistencia biométrica, rondines nocturnos, evaluaciones de
operación y propuestas Kaizen para apoyar a Supervisión, Gerencia y Dirección.

## Módulos activos

- **Operaciones:** indicadores de cocina, lavandería, limpieza y enfermería.
- **Nómina:** incidencias, retardos, bonos y reporte mensual.
- **Rondines nocturnos:** cobertura, trazabilidad y alertas de integridad.
- **Kaizen:** propuestas mensuales de mejora continua.

El módulo de cumplimiento legal está fuera de alcance por el momento.

## Ejecutar localmente

1. Crea el archivo `.streamlit/secrets.toml` usando
   `.streamlit/secrets.toml.example` como plantilla.
2. Instala dependencias con `pip install -r requirements.txt`.
3. Ejecuta `streamlit run app.py`.

Nunca subas credenciales al repositorio.

## Estructura

```text
app.py                 Aplicación activa de Streamlit
assets/qr_codes/       QR y planillas listos para impresión
data/                  Datos locales temporales
scripts/               Generadores QR y diagnósticos de conexión
docs/                  Alcance, reglas y procedimientos
```

## Flujo de datos

`Biométrico / QR Forms / Kaizen → Google Sheets → Streamlit → KPIs y PDFs`

## Estado del proyecto

La aplicación se mantiene temporalmente en `app.py`. La siguiente mejora
estructural será separar el código en módulos sin cambiar su comportamiento.
