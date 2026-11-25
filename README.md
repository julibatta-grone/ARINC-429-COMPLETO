# ARINC-429-completo

Primera etapa de un banco de pruebas de instrumentos aeronáuticos: interfaz web,
API en Python y persistencia SQLite. La comunicación serial con Arduino queda
fuera de esta etapa.

## Estructura

```text
frontend/
  index.html       Interfaz de instrumentos y envíos
  styles.css       Estilos
  app.js           Consumo de la API y acciones de la interfaz
backend/
  app/
    main.py        Aplicación FastAPI y montaje de archivos estáticos
    database.py    Conexiones y esquema SQLite
    models.py      Esquemas de entrada y salida
    routers/       Endpoints de instrumentos y envíos
    services/      Validación y generación de palabras ARINC 429
  tests/           Pruebas unitarias
  data/            Base SQLite creada al iniciar
requirements.txt
```

## Requisitos e inicio

Se requiere Python 3.10 o superior.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

Abrir <http://127.0.0.1:8000>. La documentación interactiva de la API está en
<http://127.0.0.1:8000/docs>.

La base de datos se crea en `backend/data/arinc429.db`. Se puede elegir otra
ruta con la variable de entorno `ARINC429_DATABASE`.

## Configuración ARINC por instrumento

Cada instrumento se guarda con su propia configuración JSON. Esta queda vacía
por defecto: no se asignan labels, escalas, SDI, SSM ni otros parámetros de
instrumentos automáticamente.

En esta etapa, el codificador BNR necesita una configuración explícita con esta
forma:

```json
{
  "sdi": 0,
  "ssm": 0,
  "resolution": 1.0,
  "offset": 0.0,
  "sign_mode": "twos_complement"
}
```

Los valores del ejemplo describen el formato de la configuración, no son una
configuración recomendada para ningún instrumento. `sign_mode` acepta
`twos_complement` o `sign_magnitude`. La etiqueta del instrumento se ingresa
como número octal de 1 a 3 dígitos. La palabra se expone como 32 bits binarios.
La generación usa etiqueta transmitida con bits invertidos, campos SDI/datos/SSM
y paridad impar.

Los envíos fuera de rango se guardan como `rejected_range`. Los valores en rango
sin configuración completa o con un tipo aún no soportado quedan como
`pending_configuration`, sin palabra generada. Una configuración completa BNR
produce un envío `generated`. Ninguna comunicación con Arduino se realiza.

## Pruebas

```bash
python -m unittest discover -s backend/tests -v
```
