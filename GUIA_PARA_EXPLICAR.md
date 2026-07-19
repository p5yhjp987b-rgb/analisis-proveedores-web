# Guía para explicar el proyecto desde cero

Esta guía propone una presentación gradual. La idea central es enseñar primero
qué forma tienen los datos y después cómo se transforman en una conclusión.

## 1. Qué es Python

Python es un lenguaje para escribir instrucciones que una computadora puede
seguir. En este proyecto le pedimos que lea una tabla, quite errores sencillos,
haga operaciones y muestre resultados. Los archivos terminados en `.py` contienen
esas instrucciones.

Abre primero `app.py`: allí está el orden de la pantalla. Después abre
`analisis.py`: allí están las operaciones con los datos.

## 2. Qué es pandas

`pandas` es una biblioteca de Python especializada en tablas. Una biblioteca es
un conjunto de herramientas ya construidas. La línea:

```python
import pandas as pd
```

permite usar pandas con el nombre corto `pd`. Así evitamos programar desde cero
la lectura de Excel, los filtros y las sumas agrupadas.

## 3. Qué es un DataFrame

Un `DataFrame` es la tabla de pandas. Se parece a una hoja de Excel:

- cada fila representa un registro;
- cada columna representa un dato;
- cada celda contiene un valor o puede estar vacía.

En el proyecto las variables `datos_originales`, `datos_limpios` y
`datos_filtrados` son DataFrames en momentos diferentes del proceso. Se conserva
el primero y se crean copias para no cambiar el archivo original.

## 4. Cómo se cargan uno o varios archivos

Busca `cargar_archivo` y `cargar_varios_archivos` en `analisis.py`. Cada archivo
se abre por separado. Primero se obtiene la extensión:

- para `.csv` usa `pd.read_csv`;
- para `.xlsx` o `.xls` usa `pd.read_excel`.

El CSV intenta detectar si usa coma o punto y coma. El Excel se abre sin escribir
sobre él. `pd.concat` coloca las filas de todas las tablas una debajo de otra y
relaciona columnas por el texto exacto de sus encabezados. Si un archivo no tiene
una columna, sus filas quedan vacías en ese campo y aparece un aviso.

Un Excel también puede guardar un proveedor en cada pestaña. En ese caso, la
función `_cargar_hojas_excel` busca hojas con producto y precio, combina sus filas
y usa el nombre de la pestaña para crear la columna `Proveedor`. Por ejemplo,
`proveedor 1` y `proveedor 2` se convierten en valores de esa columna. `inv` se
reconoce como stock. El archivo original permanece intacto.

La pantalla muestra un resumen por archivo antes de `describir_columnas`, que
recorre los encabezados de la unión y muestra tipo, vacíos y un ejemplo. El programa
propone qué columna corresponde a producto, proveedor, precios, stock y dimensiones.
Para comparar ignora mayúsculas, espacios y acentos, pero conserva el encabezado
original. Si dos columnas pueden representar lo mismo, no adivina y pide revisión
mediante los desplegables de `app.py`.

## 5. Cómo funciona la limpieza

Busca `limpiar_datos` en `analisis.py`. La función recibe una tabla y devuelve dos
cosas: una copia limpia y un reporte.

1. `str.strip()` quita espacios al inicio y al final.
2. Una expresión sencilla cambia varios espacios seguidos por uno solo.
3. Los textos `""` se marcan como celdas vacías.
4. Producto y proveedor pueden convertirse a Tipo Título, minúsculas o mayúsculas.
5. Solo las columnas elegidas como numéricas pasan por `pd.to_numeric`.
6. `drop_duplicates()` elimina filas repetidas si la opción está activada.

No se rellenan vacíos inventando productos, proveedores o precios. Un vacío se
reporta y los cálculos que lo necesitan omiten ese registro.

## 6. Qué hace `groupby`

`groupby` significa “agrupar por”. Imagina que una tabla tiene muchas filas del
mismo producto. Esta idea reúne esas filas antes de calcular algo:

```python
datos.groupby(columna_producto)
```

`columna_producto` contiene el nombre real que la persona eligió. No aparece un
encabezado fijo inventado en el código.

## 7. Qué hacen `sum`, `mean`, `idxmax` e `idxmin`

- `sum` suma números. Después de agrupar, permite sumar cantidades o importes por
  producto y proveedor.
- `mean` calcula el promedio. Se usa para comparar el precio promedio registrado
  de cada proveedor.
- `idxmax` devuelve la posición donde está el valor más alto. Se usa para encontrar
  el producto con mayor cantidad.
- `idxmin` devuelve la posición donde está el valor más bajo. Se usa para localizar
  el menor precio promedio.

La posición no es todavía la respuesta. Después de obtenerla, el programa busca
la fila y lee el nombre del producto o proveedor correspondiente.

## 8. Cómo se obtiene el producto más vendido

Abre `calcular_producto_mas_vendido` en `analisis.py` y explica estos pasos:

1. Comprobar que se eligieron producto y cantidad.
2. Quitar filas sin alguno de esos dos datos.
3. Agrupar las filas por producto.
4. Aplicar `sum` a la cantidad.
5. Usar `idxmax` para ubicar la cantidad total más alta.
6. Mostrar el producto y su cantidad.

“Más vendido” significa aquí **mayor cantidad acumulada**, no mayor ingreso. Un
producto puede vender muchas unidades económicas y otro pocas unidades costosas.

## 9. Cómo se calculan las ventas totales

Hay dos caminos válidos:

1. Si el archivo ya contiene un importe total por fila, se suma esa columna.
2. Si no existe importe, pero sí cantidad y precio de venta, se calcula:

```text
venta de la fila = cantidad × precio de venta
```

Después se usa `groupby` y `sum`. El programa no suma precios unitarios como si
fueran ventas, porque eso produciría una conclusión incorrecta.

## 10. Cómo comparar correctamente los precios

Para comparar proveedores de forma justa:

1. elegir un solo producto;
2. conservar únicamente las filas de ese producto y tipo logístico;
3. agrupar por proveedor y tipo logístico;
4. calcular promedio, mínimo, máximo y cantidad de registros;
5. revisar si las compras comparadas tienen condiciones semejantes.

No es correcto comparar el precio de dos productos distintos. Tampoco es correcto
decir que el proveedor más barato es automáticamente el mejor. Además del precio
se deberían considerar calidad, tiempos de entrega, disponibilidad, garantía,
volumen mínimo y condiciones de pago. Este archivo no contiene necesariamente
esos datos, por eso la conclusión es prudente.

## 11. Cómo se incorpora el costo de envío

El envío debe convertirse a costo por unidad antes de comparar proveedores. La
pantalla pregunta cómo viene registrado:

- **Por unidad:** se usa el valor tal como aparece.
- **Por pedido completo:** se divide el envío entre la cantidad del pedido.

```text
envío por unidad = envío total del pedido ÷ cantidad
costo real por unidad = precio de compra + envío por unidad
```

Esta comparación puede cambiar la decisión. Un proveedor con compra barata puede
terminar con mayor costo real si cobra un envío alto. La tabla
`costo_real_proveedores_producto` ordena los proveedores del mismo producto por
costo real promedio.

## 12. Cómo se clasifica el gramaje

La persona selecciona la columna real de peso y dice si usa kilogramos o gramos.
Si usa gramos, primero se divide entre 1000. Después se aplica esta regla solicitada
por el cliente:

```text
Estándar = peso mayor que 0 y menor o igual a 20 kg
LTL = peso mayor a 20 kg
```

El valor de exactamente 20 kg es Estándar. Un peso de 20.01 kg es LTL. Los pesos
vacíos, cero o negativos no se clasifican y generan un aviso.

La pantalla aplica una tarifa fija de envío distinta para cada categoría:

```text
tarifa por gramaje = 100 si es Estándar; 500 si es LTL
costo real por unidad = compra + envío por unidad + tarifa fija
```

Las tarifas comienzan en 100 y 500 porque son los supuestos configurados para este
proyecto. La persona puede cambiarlas cuando reciba una cotización real.

## 13. Cómo se calculan las dimensiones

La persona puede seleccionar columnas reales de largo, ancho y alto, además de su
unidad: milímetros, centímetros o metros. Primero se convierten a metros y después:

```text
volumen en m³ = largo en m × ancho en m × alto en m
costo por dimensiones = volumen en m³ × tarifa por m³
```

Las tres dimensiones son necesarias. Una dimensión vacía, cero o negativa impide
calcular el volumen de esa fila, pero no detiene los demás análisis. La tarifa por
m³ es un supuesto editable y debe reemplazarse con la tarifa real del transportista.

## 14. Cómo se usa el stock

El stock es opcional y se elige usando su nombre real. El programa no borra filas
históricas ni cambia el archivo original. Solo aplica estas reglas al decidir:

1. una fila con stock cero o vacío no participa en comparaciones ni recomendaciones;
2. un proveedor debe tener al menos las unidades solicitadas para cotizar y entrar
   en Monte Carlo;
3. cuando un proveedor aparece varias veces, se conserva el mayor stock registrado,
   no se suman valores que podrían representar el mismo inventario.

Sin una fecha de actualización no se puede saber si el stock sigue vigente. Antes
de comprar se debe confirmar directamente con el proveedor.

### Qué ocurre cuando faltan datos

El programa evita quedarse sin conclusión. Usa esta jerarquía:

1. si existen proveedor y precio, elige el menor precio disponible;
2. si falta precio pero existe stock, propone el proveedor con mayor stock;
3. si solo existen nombres, selecciona el primero alfabéticamente y marca la
   confianza como muy baja.

Cuando faltan envío, peso o dimensiones, esos costos no se inventan: se usa cero
provisional únicamente para completar la operación y se muestra un aviso. La
recomendación indica confianza alta, media, baja o muy baja según las columnas
reales disponibles. Una recomendación provisional sirve para orientar la captura
de datos, no para ocultar que faltan costos.

## 15. Cómo se calcula la cotización

La pestaña “Costos y venta” recibe estos datos principales:

1. número de unidades;
2. peso, cuando el Excel no lo incluye;
3. envío que se cobrará al cliente por toda la cotización;
4. comisión porcentual de la plataforma;
5. porcentaje destinado a promoción y publicidad digital;
6. margen de ganancia deseado;
7. tasa de IVA.

El modelo usado es:

```text
costo de compra total = compra por unidad × número de unidades
precio producto sin IVA = costo de compra total ÷ (1 − comisión − promoción − margen)
precio de venta antes del envío = precio producto sin IVA × (1 + tasa de IVA)
envío que se suma = envío interno total + envío adicional al cliente con IVA
precio total cliente = precio de venta antes del envío + envío que se suma
precio por unidad = precio total cliente ÷ número de unidades
```

La comisión, la promoción y la ganancia objetivo se presentan por separado para
poder explicar el cálculo. La suma de esos tres porcentajes debe ser menor que 100%.

En “Comparativa: precio de venta según el envío”, cada fila representa un
proveedor. El envío incluye el valor del archivo, la tarifa Estándar/LTL y el costo
por dimensiones que aplique. La venta antes del envío corresponde únicamente al
producto con plataforma, promoción, margen e IVA. El total final es la suma visible
de esa venta y el envío; por eso ambos valores solo pueden coincidir cuando el envío
realmente es cero.

La pantalla propone 16% porque es la tasa general indicada en el artículo 1 de la
Ley del IVA. Esto no significa que todos los productos tengan esa tasa: hay actos
a tasa 0% y exentos. La persona debe confirmar el tratamiento de su producto. La
tasa puede editarse en la pantalla. Fuente oficial:
https://wwwmat.sat.gob.mx/articulo/19848/articulo-1

## 16. Cómo funciona Monte Carlo

Monte Carlo no adivina el futuro. Es una técnica para repetir miles de escenarios
posibles usando variaciones configuradas por la persona:

1. cambia aleatoriamente el precio de compra alrededor de su promedio;
2. cambia el costo logístico, formado por envío, gramaje y dimensiones;
3. recalcula el precio total con la misma cantidad, comisión, promoción, margen e IVA;
4. busca el precio más bajo de ese escenario;
5. cuenta cuántas veces ganó cada proveedor.

```text
probabilidad económica = escenarios ganados ÷ total de simulaciones × 100
```

El percentil 5 muestra un escenario favorable y el percentil 95 uno desfavorable.
La semilla fija permite repetir exactamente el ejercicio. El resultado depende de
los porcentajes escritos y no sustituye información real sobre calidad, puntualidad,
garantías o condiciones de pago.

## 17. Cómo se obtiene la utilidad histórica

La utilidad por unidad se calcula solamente si existen ambos precios:

```text
utilidad por unidad = venta − compra − envío − costo por gramaje − costo por dimensiones
```

Si también existe cantidad:

```text
utilidad total de la fila = utilidad por unidad × cantidad
```

Esta es una estimación básica basada en precios ya registrados. El envío del
proveedor sí se incluye cuando se selecciona. La cotización nueva muestra comisión,
promoción, margen e IVA por separado; no deben confundirse ambos análisis.

## 18. Cómo interpretar las gráficas

- **Cantidad vendida por producto:** una barra más alta representa más unidades.
  Sirve para detectar demanda, no necesariamente ganancia.
- **Ventas por producto:** una barra más alta representa mayor importe vendido.
  Conviene revisar si la moneda y el periodo son los mismos.
- **Ventas por proveedor:** muestra qué importe de ventas está relacionado con los
  registros de cada proveedor; no mide por sí sola la calidad del proveedor.
- **Precio promedio por proveedor:** una barra más baja indica menor promedio
  registrado. Debe interpretarse junto con producto y condiciones de compra.
- **Comparación de un producto:** permite una comparación más justa porque todas
  las barras corresponden al mismo producto.
- **Costo real por proveedor:** suma compra, envío, gramaje y dimensiones. Una
  barra menor indica menor costo económico, no mejor calidad.
- **Venta + envío con IVA por proveedor:** una barra más baja representa un precio
  final menor con la misma cantidad, comisión, promoción, margen, envío e IVA.
- **Monte Carlo:** una barra más alta representa mayor porcentaje de escenarios en
  los que ese proveedor fue el más económico. No representa calidad ni certeza.
- **Utilidad por producto:** muestra la diferencia estimada entre venta y compra.
  Una utilidad alta puede venir de margen, cantidad o ambos.

Antes de presentar una gráfica, lee su título, el eje horizontal y el eje vertical.
Después formula una conclusión limitada a lo que esos elementos realmente miden.

## 19. Cómo funciona Streamlit

Streamlit ejecuta `app.py` de arriba hacia abajo. Cada `st.selectbox`,
`st.multiselect` o `st.radio` crea un control. Cuando la persona cambia una opción,
la pantalla se vuelve a calcular con las nuevas selecciones. `st.dataframe` muestra
tablas, `st.plotly_chart` muestra gráficas y `st.download_button` prepara descargas.

## 20. Orden sugerido para una demostración

1. Mostrar `requirements.txt` y explicar que son las herramientas externas.
2. Abrir `analisis.py` y localizar carga, limpieza, agrupaciones y exportación.
3. Abrir `app.py` y relacionar cada bloque con una sección visible de la pantalla.
4. Ejecutar el programa y comenzar con los tres Excel ficticios de demostración.
5. En “Datos”, comprobar las columnas encontradas y abrir la vista previa.
6. En “Costos y venta”, buscar un producto y capturar los porcentajes.
7. En “Recomendación”, explicar por qué el stock cero quedó fuera.
8. Separar precio de venta con IVA, envío al cliente y total que pagará.
9. Leer la probabilidad de Monte Carlo sin confundirla con una evaluación de calidad.
10. Descargar Excel y explicar que el original sigue intacto.

## 21. Preguntas que podrían hacer y respuestas sencillas

**¿El programa cambia mi Excel?**

No. Lee el archivo y trabaja con una copia en memoria. La descarga es un archivo
nuevo.

**¿Por qué debo elegir las columnas?**

Porque cada empresa usa encabezados distintos. Elegir el nombre real evita que el
programa adivine incorrectamente.

**¿Qué pasa si cargo varios Excel?**

Se leen por separado y sus filas se unen por el nombre exacto de cada columna. La
pantalla muestra cuántas filas y columnas aporta cada archivo. Si los encabezados
son diferentes, se avisa y las columnas ausentes quedan vacías.

**¿Deben tener el mismo orden las columnas?**

No. pandas relaciona las columnas por encabezado, no por posición. Sí conviene que
el mismo concepto use el mismo nombre y la misma unidad en todos los archivos.

**¿Qué pasa si falta cantidad?**

Los análisis que dependen de cantidad muestran un aviso. Otros, como el precio
promedio, todavía pueden funcionar si tienen sus columnas.

**¿Por qué una celda numérica puede quedar vacía?**

Porque su texto no se pudo convertir con seguridad. El reporte indica cuántos
casos existen para que se revisen en una copia del archivo.

**¿Qué diferencia hay entre precio y ventas?**

El precio es el valor de una unidad. Las ventas consideran el importe ya registrado
o multiplican precio de venta por cantidad.

**¿Por qué se usa el promedio del proveedor?**

Porque un proveedor puede aparecer en varias filas con precios diferentes. El
promedio resume esos registros, aunque también conviene revisar mínimos, máximos y
cantidad de observaciones.

**¿El proveedor más barato es el mejor?**

No necesariamente. El precio es solo un criterio; faltan calidad, entrega,
disponibilidad y condiciones comerciales.

**¿Qué pasa cuando el stock es cero?**

El registro se conserva para análisis históricos, pero ese proveedor no aparece
como opción disponible ni puede ganar la cotización o Monte Carlo.

**¿Qué pasa si necesito más unidades que el stock disponible?**

El proveedor se excluye de esa cotización. El programa explica cuántos proveedores
quedaron fuera.

**¿Qué significa la recomendación Monte Carlo?**

Indica qué proveedor fue el más económico en más escenarios simulados. Depende de
las variaciones configuradas y no significa que sea el mejor en calidad o entrega.

**¿Por qué el gramaje cambia el precio?**

Porque se agrega una tarifa fija de envío según la categoría. Estándar usa 100 y
LTL usa 500. No se vuelve a multiplicar por los kilogramos.

**¿Cómo afectan largo, ancho y alto?**

Se multiplican para obtener volumen en metros cúbicos. El volumen se multiplica
por una tarifa editable y el resultado se suma al costo logístico por unidad.

**¿Por qué preguntamos si el envío es por unidad o por pedido?**

Porque un envío total no se puede sumar directamente al precio de una sola unidad.
Primero se divide entre la cantidad comprada.

**¿Qué proveedor conviene elegir?**

La aplicación identifica cuál tiene menor costo real y cuál deja mayor utilidad
estimada para el producto elegido. Esa es una recomendación económica; todavía se
deben revisar calidad, entrega, disponibilidad, garantías y condiciones de pago.

**¿Por qué 20 kg pertenece a Estándar?**

Porque la regla del cliente dice “igual o menor a 20 kg”. LTL comienza cuando el
peso es estrictamente mayor a 20 kg.

**¿De dónde sale el 16% de IVA?**

Es la tasa general del artículo 1 de la Ley del IVA. La pantalla permite cambiarla
porque algunos productos pueden tener tasa 0%, estar exentos o requerir revisión
fiscal específica.

**¿La comisión se cobra sobre el precio con IVA?**

En este modelo educativo se aplica sobre el precio del producto antes de IVA. Hay
que revisar el contrato de cada plataforma y cambiar el modelo si su base es otra.

**¿Qué representa la promoción digital?**

Es el porcentaje del precio antes de IVA que se reserva para publicidad,
posicionamiento u otros cargos promocionales. Debe sustituirse por la tarifa real
de la plataforma.

**¿Cuál es la diferencia entre precio de venta y venta más envío?**

El precio de venta con IVA corresponde al producto. El envío al cliente con IVA se
muestra aparte. La suma de ambos es el total que pagará el cliente.

**¿Qué significa “precio por número”?**

Es el precio total con IVA dividido entre el número de unidades solicitado. Así se
puede responder cuánto cuesta cada unidad dentro de la cotización.

**¿La utilidad es la ganancia final de la empresa?**

No. Es una utilidad básica de compra y venta. Otros gastos no están incluidos.

**¿Por qué se eliminan duplicados?**

Una fila repetida puede contar dos veces la misma operación y exagerar resultados.
La pantalla informa cuántas se eliminaron.

**¿Qué contiene el Excel descargado?**

Incluye datos limpios, indicadores, las tablas que pudieron calcularse y las
conclusiones, cada elemento en una hoja separada.

**¿Cómo sé que funciona?**

El proyecto incluye pruebas automáticas en `tests/`. Estas verifican carga,
limpieza, cálculos, avisos y exportación sin modificar archivos reales.
