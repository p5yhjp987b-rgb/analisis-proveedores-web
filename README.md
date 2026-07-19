# Análisis educativo de ventas y proveedores

Aplicación sencilla en Python y Streamlit para cargar uno o varios Excel/CSV,
comparar un producto entre proveedores con stock y calcular un precio de venta
que considere logística, plataforma digital, promoción, margen e IVA. El programa
trabaja con copias en memoria: no modifica ni elimina los archivos originales.

## Qué archivo revisar

- `LEEME_PRIMERO.txt`: instrucciones de doble clic para el cliente.
- `INICIAR_MAC.command`: inicia la aplicación en macOS.
- `INICIAR_WINDOWS.bat`: inicia la aplicación en Windows.
- `app.py`: pantalla, controles, filtros, tablas, gráficas y descargas.
- `analisis.py`: carga, limpieza, cálculos y exportación.
- `GUIA_PARA_EXPLICAR.md`: explicación para enseñar el proyecto desde cero.
- `requirements.txt`: bibliotecas que necesita Python.
- `datos/`: lugar opcional para colocar los archivos originales.
- `resultados/`: lugar sugerido para guardar las descargas.
- `tests/`: pruebas automáticas del comportamiento principal.

## Requisitos

- Python 3.14.
- Una terminal con acceso a Internet durante la instalación.
- Para practicar no necesitas un archivo propio: se incluye un CSV ficticio. En
  Excel se lee la primera hoja.

## Abrir con doble clic

Después de descomprimir completamente el proyecto:

- En **Mac**, abre `INICIAR_MAC.command`. Si macOS lo bloquea la primera vez,
  haz clic derecho y selecciona **Abrir**.
- En **Windows**, abre `INICIAR_WINDOWS.bat`.

Los iniciadores crean `.venv`, instalan las dependencias cuando hace falta y
abren Streamlit en el navegador. La primera ejecución necesita Internet y puede
tardar algunos minutos. Las instrucciones para una persona no técnica están en
`LEEME_PRIMERO.txt`.

## Instalación exacta en macOS o Linux

Abre Terminal y ejecuta cada línea:

```bash
cd "/Users/irvinda/Documents/Codex/2026-07-18/quiero-crear-un-proyecto-educativo-en-2/outputs/analisis-proveedores"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

El entorno virtual `.venv` mantiene las bibliotecas de este proyecto separadas
de otros programas. Solo es necesario crearlo e instalar las dependencias una
vez.

## Abrir el programa

Desde la carpeta del proyecto ejecuta:

```bash
.venv/bin/python -m streamlit run app.py
```

Streamlit mostrará una dirección parecida a `http://localhost:8501`. Normalmente
también abrirá el navegador de forma automática. Para detenerlo, vuelve a la
terminal y presiona `Control + C`.

## Instalación y ejecución en Windows

Abre PowerShell dentro de `analisis-proveedores` y ejecuta:

```powershell
py -3.14 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
.venv\Scripts\python -m streamlit run app.py
```

## Cómo usar la aplicación

Si todavía no tienes datos reales, abre la aplicación normalmente. Se seleccionan
automáticamente tres Excel ficticios de enero, febrero y marzo dentro de `datos/`.
Contienen productos Estándar y LTL con varios proveedores, stock y dimensiones.
Sus columnas se asignan automáticamente y el envío se interpreta como costo total
del pedido. Puedes cambiar cualquier selección para practicar.

Cuando recibas datos reales, la pantalla se divide en tres pestañas:

1. **Datos:** carga uno o varios archivos, revisa los nombres reales y corrige la
   asignación automática únicamente si hace falta.
2. **Costos y venta:** elige un producto, captura las unidades, el peso si falta en
   el Excel, el envío cobrado al cliente, la comisión de plataforma, la promoción
   digital, el margen y el IVA.
3. **Recomendación:** consulta el proveedor económico con stock, el desglose del
   precio de venta más envío, la comparación final y Monte Carlo. La tabla muestra
   para cada proveedor: tipo de envío, compra, envío interno, venta sugerida por
   unidad, envío al cliente y total final.

La tarifa fija empieza en `$100` para Estándar (`≤20 kg`) y `$500` para LTL
(`>20 kg`). Si el Excel no contiene peso, la segunda pestaña permite capturarlo
solo para el producto seleccionado; ese valor no se escribe en el archivo original.

### Excel con una pestaña por proveedor

También puedes usar un solo libro donde cada pestaña se llame `proveedor 1`,
`proveedor 2`, etc. Si las hojas contienen columnas como `codigo`, `producto`,
`categoria`, `precio` e `inv`, el programa:

- combina las filas de todas las pestañas de productos;
- crea la columna `Proveedor` usando el nombre de la hoja;
- interpreta `precio` como precio de compra e `inv` como stock;
- conserva `Hoja de origen` para saber de dónde salió cada fila;
- excluye de la recomendación las ofertas cuyo `inv` sea cero.

Si el libro contiene una hoja llamada `Datos`, esa hoja se considera la tabla
principal y no se mezclan hojas auxiliares como resumen o instrucciones.

Si los archivos no tienen exactamente las mismas columnas, pandas conserva la
unión de todos los encabezados y coloca celdas vacías donde una fuente no incluye
un campo. La aplicación muestra un aviso antes del análisis.

No hay nombres de columnas obligatorios. Una columna llamada ` PRODUCTO `,
`Producto` o `producto` se puede reconocer automáticamente. La aplicación siempre
muestra el nombre real detectado y permite corregir la selección.

## Qué necesita cada análisis

| Resultado | Columnas que se deben elegir |
| --- | --- |
| Producto más vendido | Producto y cantidad |
| Ventas por producto | Producto y un importe, o producto + cantidad + precio de venta |
| Ventas por proveedor | Proveedor y un importe, o proveedor + cantidad + precio de venta |
| Precio promedio por proveedor | Proveedor y precio de compra |
| Comparación de proveedores | Producto, proveedor y precio de compra |
| Utilidad | Precio de compra y precio de venta; cantidad para utilidad total |
| Costo real con envío | Producto, proveedor, precio de compra y envío; cantidad si el envío es por pedido |
| Utilidad después del envío | Compra, venta y envío; cantidad para utilidad total |
| Clasificación Estándar/LTL | Peso y su unidad: kg o g |
| Disponibilidad | Stock; valores cero o vacíos se excluyen de decisiones |
| Tarifa de envío por gramaje | Peso, unidad y tarifa fija para Estándar y LTL |
| Volumen y costo por dimensiones | Largo, ancho, alto, unidad y tarifa por m³ |
| Cotización por número de unidades | Producto, proveedor, compra y envío; número, comisión, promoción, margen, envío cobrado e IVA |
| Monte Carlo | Los datos de cotización; además stock, variaciones e iteraciones |

El costo real se calcula así:

```text
Envío por unidad = envío ÷ cantidad       (solo cuando el envío es por pedido)
Costo real por unidad = compra + envío por unidad
Utilidad por unidad = venta − costo real por unidad
```

Cuando se configura el gramaje:

```text
Tarifa por gramaje = 100 si es Estándar; 500 si es LTL
Volumen en m³ = largo en m × ancho en m × alto en m
Costo por dimensiones = volumen en m³ × tarifa por m³
Costo real por unidad = compra + envío + tarifa fija + costo por dimensiones
```

La cotización usa este modelo educativo:

```text
Precio producto sin IVA = costo de compra total ÷ (1 − comisión − promoción − margen)
Precio de venta antes del envío = precio producto sin IVA × (1 + tasa de IVA)
Envío que se suma = envío interno total + envío adicional al cliente con IVA
Precio total cliente = precio de venta antes del envío + envío que se suma
Precio por unidad = precio total cliente ÷ número de unidades
```

Por diseño, el tercer cuadro muestra el precio de venta antes del envío y el cuarto
es la suma exacta del segundo y el tercero. Las tarifas fijas de `$100` y `$500`
se agregan en el envío; no quedan escondidas dentro del precio del producto.

La comisión, la promoción digital y el margen se calculan sobre el precio del
producto antes del IVA. Su suma debe ser menor que 100%. Confirma si la plataforma
usa esa misma base. El valor inicial de IVA es 16%, que es la tasa general del
artículo 1 de la Ley del IVA; puede cambiarse para productos a tasa 0%, exentos u
otros casos. Fuente oficial:
https://wwwmat.sat.gob.mx/articulo/19848/articulo-1

Monte Carlo repite entre 100 y 50,000 escenarios. En cada escenario varían compra
y logística —envío, gramaje y dimensiones— según los porcentajes escritos, se recalcula el precio total y se
registra qué proveedor fue más económico. La probabilidad resultante es una medida
económica basada en supuestos; no evalúa calidad, entrega, garantías o condiciones
de pago. Los proveedores con stock cero o con menos unidades que las solicitadas
no participan.

Si falta una columna, la aplicación explica qué dato necesita y aun así genera una
recomendación provisional cuando existe al menos un proveedor identificable. La
prioridad es: menor precio disponible, después mayor stock y, si tampoco existe
esa información, una selección alfabética marcada con confianza muy baja. Los
costos desconocidos de envío, peso o dimensiones se muestran como no incluidos;
no se presentan como datos reales. Si el archivo afirma que el stock es cero, ese
proveedor continúa excluido.

## Ejecutar las pruebas

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Las pruebas crean datos solamente en memoria. No agregan ni cambian archivos en
`datos/`.

## Problemas frecuentes

- **`No module named streamlit`:** ejecuta la instalación de `requirements.txt`
  y usa el Python que está dentro de `.venv`.
- **El CSV no abre:** confirma que realmente sea texto separado por comas o punto
  y coma y que tenga una fila de encabezados.
- **Un cálculo dice “no disponible”:** vuelve a la sección 3 y elige las columnas
  que ese cálculo necesita.
- **Un número quedó vacío:** el texto original no pudo convertirse con seguridad;
  corrígelo en una copia del archivo y vuelve a cargarla.
- **El navegador no aparece:** copia la dirección que muestra Streamlit en la
  terminal y pégala en el navegador.
