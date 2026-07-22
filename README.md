# Proveedor Claro — versión web para Vercel

Aplicación educativa para cargar uno o varios archivos Excel/CSV, limpiar sus
datos y comparar proveedores. La interfaz es HTML, CSS y JavaScript; los
cálculos siguen escritos en Python con pandas. La conexión web usa el estándar
WSGI incluido en Python, así que no depende de un framework adicional.

## Qué incluye

- lectura de `.xlsx`, `.xls` y `.csv`;
- detección de nombres reales de columnas, ignorando acentos y mayúsculas;
- limpieza de espacios, texto, números y duplicados;
- exclusión de proveedores con stock cero o insuficiente;
- tarifas fijas de `$100` para Estándar (hasta 20 kg) y `$500` para LTL;
- dimensiones y costo opcional por metro cúbico;
- comisión de plataforma, promoción, margen e IVA;
- precio de venta antes del envío y total final después del envío;
- comparación individual por producto;
- simulación Monte Carlo;
- descarga de resultados en Excel y CSV.

Los archivos se procesan en memoria. La aplicación no modifica ni guarda los
originales.

## Archivos principales

- `app.py`: aplicación WSGI, API y rutas de la página.
- `analisis.py`: carga, limpieza, cálculos, Monte Carlo y exportación.
- `index.html`: estructura de la interfaz.
- `styles.css`: diseño visual adaptable a computadora y celular.
- `app.js`: conexión entre la pantalla y Python.
- `datos_demostracion.csv`: datos ficticios para practicar.
- `tests/test_api.py`: pruebas del recorrido principal.

## Ejecutar localmente

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Abre `http://127.0.0.1:8000`.

En Windows, activa el entorno con:

```powershell
.venv\Scripts\Activate.ps1
```

## Ejecutar pruebas

```bash
python -m unittest discover -s tests -v
```

## Publicar en Vercel

Vercel reconoce la variable WSGI `app` dentro de `app.py`. La versión de Python
se declara en `.python-version` y las dependencias en `requirements.txt`.

1. Sube estos archivos a un repositorio de GitHub.
2. En Vercel selecciona **Add New → Project**.
3. Importa el repositorio.
4. Conserva la configuración automática y pulsa **Deploy**.

La aplicación no necesita variables secretas ni base de datos.

## Nota importante

El resultado recomienda una alternativa con la información disponible. Un
precio menor no significa automáticamente que sea el mejor proveedor: también
deben revisarse calidad, entrega, garantías y condiciones de pago.
