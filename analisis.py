"""Funciones sencillas para cargar, limpiar y analizar ventas.

Este archivo contiene la lógica del proyecto. Separarla de la interfaz hace que
cada función se pueda estudiar y probar de forma independiente.
"""

from __future__ import annotations

from copy import copy
from io import BytesIO
from pathlib import Path
import random
from typing import Any, BinaryIO
import unicodedata

# Importamos pandas para trabajar con tablas
import pandas as pd


EXTENSIONES_PERMITIDAS = {".csv", ".xlsx", ".xls"}
NOMBRE_TIPO_LOGISTICO = "Tipo logístico calculado"
NOMBRE_STOCK_RESULTADO = "Stock disponible"
NOMBRE_COSTO_GRAMAJE = "Costo logístico por peso promedio"
NOMBRE_VOLUMEN = "Volumen calculado (m³)"
NOMBRE_COSTO_DIMENSIONES = "Costo logístico por dimensiones promedio"


def _normalizar_encabezado(nombre: object) -> str:
    """Compara encabezados ignorando mayúsculas, espacios, signos y acentos."""

    texto = unicodedata.normalize("NFKD", str(nombre).strip().casefold())
    sin_acentos = "".join(letra for letra in texto if not unicodedata.combining(letra))
    return "".join(letra for letra in sin_acentos if letra.isalnum())


def _es_hoja_de_productos(tabla: pd.DataFrame) -> bool:
    """Reconoce hojas que parecen contener productos y precios de proveedores."""

    encabezados = {_normalizar_encabezado(columna) for columna in tabla.columns}
    nombres_producto = {
        "producto",
        "articulo",
        "nombreproducto",
        "nombredelproducto",
    }
    nombres_precio = {
        "precio",
        "preciocompra",
        "preciodecompra",
        "preciocompraunitario",
        "costo",
        "costounitario",
    }
    return bool(encabezados & nombres_producto) and bool(encabezados & nombres_precio)


def _tiene_columna_proveedor(tabla: pd.DataFrame) -> bool:
    """Indica si la hoja ya contiene su propia columna de proveedor."""

    nombres = {_normalizar_encabezado(columna) for columna in tabla.columns}
    return bool(nombres & {"proveedor", "nombreproveedor", "nombredelproveedor"})


def _cargar_hojas_excel(archivo: str | Path | BinaryIO) -> pd.DataFrame:
    """Lee una hoja Datos o combina pestañas que representan proveedores."""

    _volver_al_inicio(archivo)
    hojas = pd.read_excel(archivo, sheet_name=None)
    if not hojas:
        raise ValueError("El Excel no contiene hojas para analizar.")

    # Los libros creados por este proyecto usan una hoja principal llamada Datos.
    hojas_datos = [
        (nombre, tabla)
        for nombre, tabla in hojas.items()
        if _normalizar_encabezado(nombre) == "datos"
    ]
    if hojas_datos:
        nombre, tabla = hojas_datos[0]
        resultado = tabla.dropna(how="all").dropna(axis=1, how="all")
        resultado.attrs["hojas_leidas"] = [nombre]
        return resultado

    hojas_utiles: list[tuple[str, pd.DataFrame]] = []
    hojas_no_vacias: list[tuple[str, pd.DataFrame]] = []
    for nombre, tabla in hojas.items():
        limpia = tabla.dropna(how="all").dropna(axis=1, how="all")
        if limpia.empty or len(limpia.columns) == 0:
            continue
        hojas_no_vacias.append((nombre, limpia))
        if _es_hoja_de_productos(limpia):
            hojas_utiles.append((nombre, limpia))

    # Si no reconocemos el formato, conservamos el comportamiento sencillo y
    # leemos la primera hoja con información.
    seleccionadas = hojas_utiles or hojas_no_vacias[:1]
    if not seleccionadas:
        raise ValueError("El Excel no contiene filas ni columnas para analizar.")

    varias_hojas = len(seleccionadas) > 1
    tablas: list[pd.DataFrame] = []
    for nombre, tabla in seleccionadas:
        copia = tabla.copy()
        nombre_parece_proveedor = "proveedor" in _normalizar_encabezado(nombre)
        if not _tiene_columna_proveedor(copia) and (varias_hojas or nombre_parece_proveedor):
            # Cada pestaña se convierte en un proveedor sin cambiar el Excel original.
            copia["Proveedor"] = nombre
        if varias_hojas:
            copia["Hoja de origen"] = nombre
        tablas.append(copia)

    resultado = pd.concat(tablas, ignore_index=True, sort=False)
    resultado.attrs["hojas_leidas"] = [nombre for nombre, _ in seleccionadas]
    return resultado


def buscar_archivos_datos(carpeta: str | Path = "datos") -> list[Path]:
    """Devuelve los Excel y CSV que ya existen en la carpeta ``datos``.

    La función solo consulta la carpeta: no modifica ni elimina archivos.
    """

    ruta = Path(carpeta)
    if not ruta.exists():
        return []

    return sorted(
        archivo
        for archivo in ruta.iterdir()
        if archivo.is_file() and archivo.suffix.lower() in EXTENSIONES_PERMITIDAS
    )


def _nombre_del_archivo(archivo: str | Path | BinaryIO) -> str:
    """Obtiene el nombre tanto de una ruta como de un archivo subido."""

    if isinstance(archivo, (str, Path)):
        return Path(archivo).name
    return Path(getattr(archivo, "name", "")).name


def _volver_al_inicio(archivo: str | Path | BinaryIO) -> None:
    """Reinicia un archivo en memoria para poder intentar leerlo otra vez."""

    if hasattr(archivo, "seek"):
        archivo.seek(0)


def cargar_archivo(archivo: str | Path | BinaryIO) -> pd.DataFrame:
    """Carga un CSV, XLSX o XLS sin cambiar el archivo original."""

    nombre = _nombre_del_archivo(archivo)
    extension = Path(nombre).suffix.lower()

    if extension not in EXTENSIONES_PERMITIDAS:
        permitidas = ", ".join(sorted(EXTENSIONES_PERMITIDAS))
        raise ValueError(f"Formato no permitido. Usa uno de estos: {permitidas}.")

    _volver_al_inicio(archivo)

    # Leemos el archivo seleccionado
    if extension == ".csv":
        try:
            # sep=None permite detectar comas, punto y coma u otro separador.
            datos = pd.read_csv(
                archivo,
                sep=None,
                engine="python",
                encoding="utf-8-sig",
            )
        except UnicodeDecodeError:
            # Algunos CSV antiguos usan la codificación latin-1.
            _volver_al_inicio(archivo)
            datos = pd.read_csv(
                archivo,
                sep=None,
                engine="python",
                encoding="latin-1",
            )
        datos.attrs["hojas_leidas"] = []
    else:
        # Leemos todas las hojas útiles. Una pestaña puede representar un proveedor.
        datos = _cargar_hojas_excel(archivo)

    if len(datos.columns) == 0:
        raise ValueError("El archivo no contiene columnas para analizar.")

    return datos


def cargar_varios_archivos(
    archivos: list[str | Path | BinaryIO],
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Carga varios Excel/CSV y une sus filas sin cambiar los originales."""

    if not archivos:
        raise ValueError("Selecciona al menos un archivo para comenzar.")

    tablas: list[pd.DataFrame] = []
    resumen: list[dict[str, object]] = []
    conjuntos_columnas: list[set[object]] = []

    for archivo in archivos:
        # Leemos cada archivo seleccionado por separado.
        tabla = cargar_archivo(archivo)
        tablas.append(tabla)
        conjuntos_columnas.append(set(tabla.columns))
        resumen.append(
            {
                "Archivo": _nombre_del_archivo(archivo),
                "Hojas leídas": ", ".join(tabla.attrs.get("hojas_leidas", [])) or "No aplica",
                "Filas": len(tabla),
                "Número de columnas": len(tabla.columns),
                "Columnas detectadas": ", ".join(str(columna) for columna in tabla.columns),
            }
        )

    # Unimos por el nombre real de cada columna. Las ausentes quedan vacías.
    datos_unidos = pd.concat(tablas, ignore_index=True, sort=False)
    avisos: list[str] = []
    if len(conjuntos_columnas) > 1 and any(
        columnas != conjuntos_columnas[0] for columnas in conjuntos_columnas[1:]
    ):
        avisos.append(
            "Los archivos no tienen exactamente las mismas columnas. Se creó una unión; "
            "las columnas que faltan en algún archivo aparecen como celdas vacías."
        )

    return datos_unidos, pd.DataFrame(resumen), avisos


def describir_columnas(datos: pd.DataFrame) -> pd.DataFrame:
    """Crea una tabla simple con las columnas reales que fueron detectadas."""

    filas: list[dict[str, object]] = []
    for columna in datos.columns:
        valores = datos[columna].dropna()
        # Convertimos el ejemplo a texto para que Streamlit no mezcle tipos.
        ejemplo = str(valores.iloc[0]) if not valores.empty else "Sin ejemplo"
        filas.append(
            {
                "Columna detectada": str(columna),
                "Tipo actual": str(datos[columna].dtype),
                "Celdas vacías": int(datos[columna].isna().sum()),
                "Ejemplo": ejemplo,
            }
        )

    return pd.DataFrame(filas)


def _limpiar_texto(serie: pd.Series) -> pd.Series:
    """Quita espacios repetidos y convierte textos vacíos en celdas nulas."""

    texto = serie.astype("string")
    texto = texto.str.strip().str.replace(r"\s+", " ", regex=True)
    return texto.replace("", pd.NA)


def _normalizar_mayusculas(serie: pd.Series, estilo: str) -> pd.Series:
    """Unifica mayúsculas y minúsculas usando una opción fácil de explicar."""

    if estilo == "titulo":
        return serie.str.title()
    if estilo == "minusculas":
        return serie.str.lower()
    if estilo == "mayusculas":
        return serie.str.upper()
    return serie


def _preparar_numero(valor: object) -> object:
    """Prepara números escritos como texto, incluso con símbolos de moneda."""

    if pd.isna(valor) or isinstance(valor, (int, float)):
        return valor

    texto = str(valor).strip()
    if not texto:
        return pd.NA

    negativo = texto.startswith("(") and texto.endswith(")")
    texto = texto.strip("()")
    texto = "".join(caracter for caracter in texto if caracter.isdigit() or caracter in ",.-")

    # Si aparecen punto y coma, el último suele ser el separador decimal.
    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        decimales = len(texto.rsplit(",", 1)[-1])
        texto = texto.replace(",", ".") if decimales in (1, 2) else texto.replace(",", "")

    if negativo:
        texto = f"-{texto}"
    return texto


def convertir_columna_numerica(serie: pd.Series) -> tuple[pd.Series, int]:
    """Convierte texto a número y devuelve cuántos valores no se entendieron."""

    no_vacios_antes = int(serie.notna().sum())
    preparada = serie.map(_preparar_numero)
    convertida = pd.to_numeric(preparada, errors="coerce")
    no_vacios_despues = int(convertida.notna().sum())
    return convertida, no_vacios_antes - no_vacios_despues


def limpiar_datos(
    datos: pd.DataFrame,
    columnas_texto: list[str] | None = None,
    columnas_numericas: list[str] | None = None,
    estilo_texto: str = "titulo",
    eliminar_duplicados: bool = True,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Limpia una copia de los datos y entrega un reporte comprensible.

    Las columnas de texto y numéricas deben venir de los nombres reales que la
    persona seleccionó en la interfaz. Así el programa no adivina columnas.
    """

    columnas_texto = columnas_texto or []
    columnas_numericas = columnas_numericas or []
    resultado = datos.copy()
    filas_iniciales = len(resultado)
    vacias_antes = int(resultado.isna().sum().sum())
    conversiones_fallidas: dict[str, int] = {}

    # Primero quitamos espacios en todas las columnas que contienen texto.
    for columna in resultado.select_dtypes(include=["object", "string"]).columns:
        resultado[columna] = _limpiar_texto(resultado[columna])

    # Después unificamos mayúsculas solo en las columnas elegidas como texto.
    for columna in columnas_texto:
        if columna in resultado.columns:
            texto = _limpiar_texto(resultado[columna])
            resultado[columna] = _normalizar_mayusculas(texto, estilo_texto)

    # Convertimos a número únicamente las columnas indicadas por la persona.
    for columna in columnas_numericas:
        if columna in resultado.columns:
            resultado[columna], errores = convertir_columna_numerica(resultado[columna])
            conversiones_fallidas[columna] = errores

    duplicados = int(resultado.duplicated().sum())
    if eliminar_duplicados:
        resultado = resultado.drop_duplicates().reset_index(drop=True)

    reporte: dict[str, object] = {
        "filas_iniciales": filas_iniciales,
        "filas_finales": len(resultado),
        "duplicados_detectados": duplicados,
        "duplicados_eliminados": duplicados if eliminar_duplicados else 0,
        "celdas_vacias_antes": vacias_antes,
        "celdas_vacias_despues": int(resultado.isna().sum().sum()),
        "conversiones_numericas_fallidas": conversiones_fallidas,
    }
    return resultado, reporte


def agregar_clasificacion_gramaje(
    datos: pd.DataFrame,
    columna_peso: str | None,
    unidad_peso: str = "kg",
) -> tuple[pd.DataFrame, str | None, list[str]]:
    """Clasifica cada registro como Estándar o LTL usando el peso en kg."""

    resultado = datos.copy()
    avisos: list[str] = []
    if not _columnas_disponibles(resultado, [columna_peso]):
        avisos.append(
            "No se clasificó el gramaje: falta elegir la columna de peso."
        )
        return resultado, None, avisos

    if unidad_peso not in {"kg", "g"}:
        avisos.append("No se clasificó el gramaje: la unidad debe ser kg o g.")
        return resultado, None, avisos

    peso_kg = resultado[columna_peso]
    if unidad_peso == "g":
        peso_kg = peso_kg / 1000

    nombre = NOMBRE_TIPO_LOGISTICO
    numero = 2
    while nombre in resultado.columns:
        nombre = f"{NOMBRE_TIPO_LOGISTICO} {numero}"
        numero += 1

    clasificacion = pd.Series(pd.NA, index=resultado.index, dtype="string")
    clasificacion.loc[(peso_kg > 0) & (peso_kg <= 20)] = "Estándar (≤ 20 kg)"
    clasificacion.loc[peso_kg > 20] = "LTL (> 20 kg)"
    resultado[nombre] = clasificacion

    invalidos = int((peso_kg.isna() | (peso_kg <= 0)).sum())
    if invalidos:
        avisos.append(
            f"{invalidos} filas no se clasificaron porque el peso está vacío o no es mayor que cero."
        )
    return resultado, nombre, avisos


def agregar_volumen_dimensiones(
    datos: pd.DataFrame,
    columna_largo: str | None,
    columna_ancho: str | None,
    columna_alto: str | None,
    unidad_dimensiones: str = "cm",
) -> tuple[pd.DataFrame, str | None, list[str]]:
    """Calcula largo × ancho × alto y convierte el resultado a metros cúbicos."""

    resultado = datos.copy()
    avisos: list[str] = []
    seleccionadas = [columna_largo, columna_ancho, columna_alto]
    if all(columna is None for columna in seleccionadas):
        return resultado, None, avisos
    if not _columnas_disponibles(resultado, seleccionadas):
        avisos.append(
            "No se calculó el volumen: deben elegirse las tres columnas de largo, ancho y alto."
        )
        return resultado, None, avisos

    conversion_a_metros = {"mm": 0.001, "cm": 0.01, "m": 1.0}
    if unidad_dimensiones not in conversion_a_metros:
        avisos.append("No se calculó el volumen: la unidad debe ser mm, cm o m.")
        return resultado, None, avisos

    factor = conversion_a_metros[unidad_dimensiones]
    largo_m = resultado[columna_largo] * factor
    ancho_m = resultado[columna_ancho] * factor
    alto_m = resultado[columna_alto] * factor
    validas = (largo_m > 0) & (ancho_m > 0) & (alto_m > 0)

    nombre = NOMBRE_VOLUMEN
    numero = 2
    while nombre in resultado.columns:
        nombre = f"{NOMBRE_VOLUMEN} {numero}"
        numero += 1

    volumen = pd.Series(float("nan"), index=resultado.index, dtype="float64")
    volumen.loc[validas] = largo_m.loc[validas] * ancho_m.loc[validas] * alto_m.loc[validas]
    resultado[nombre] = volumen

    invalidas = int((~validas).sum())
    if invalidas:
        avisos.append(
            f"{invalidas} filas no recibieron volumen porque una dimensión está vacía o no es mayor que cero."
        )
    return resultado, nombre, avisos


def _columnas_disponibles(datos: pd.DataFrame, columnas: list[str | None]) -> bool:
    """Indica si todas las columnas solicitadas existen en la tabla."""

    return all(columna is not None and columna in datos.columns for columna in columnas)


def _agrupar_suma(
    datos: pd.DataFrame,
    columna_grupo: str,
    valores: pd.Series,
    nombre_valor: str,
) -> pd.DataFrame:
    """Suma una serie numérica agrupándola por producto o proveedor."""

    temporal = pd.DataFrame(
        {
            columna_grupo: datos[columna_grupo],
            nombre_valor: valores,
        }
    ).dropna(subset=[columna_grupo, nombre_valor])

    # Agrupamos los registros por producto o proveedor
    agrupado = temporal.groupby(columna_grupo, as_index=False)[nombre_valor].sum()
    return agrupado.sort_values(nombre_valor, ascending=False).reset_index(drop=True)


def calcular_producto_mas_vendido(
    datos: pd.DataFrame,
    columna_producto: str | None,
    columna_cantidad: str | None,
) -> tuple[dict[str, Any] | None, pd.DataFrame, str | None]:
    """Obtiene el producto con la suma de cantidades más alta."""

    if not _columnas_disponibles(datos, [columna_producto, columna_cantidad]):
        aviso = "No se calculó el producto más vendido: falta elegir producto o cantidad."
        return None, pd.DataFrame(), aviso

    tabla = _agrupar_suma(
        datos,
        columna_producto,
        datos[columna_cantidad],
        "Cantidad total",
    )
    if tabla.empty:
        return None, tabla, "No se calculó el producto más vendido: no hay cantidades válidas."

    # Buscamos el valor más alto
    indice_mayor = tabla["Cantidad total"].idxmax()
    fila = tabla.loc[indice_mayor]
    indicador = {
        "producto": fila[columna_producto],
        "cantidad": float(fila["Cantidad total"]),
    }
    return indicador, tabla, None


def calcular_ventas_totales(
    datos: pd.DataFrame,
    columna_grupo: str | None,
    columna_importe_venta: str | None = None,
    columna_cantidad: str | None = None,
    columna_precio_venta: str | None = None,
) -> tuple[pd.DataFrame, float | None, str | None]:
    """Calcula ventas por grupo usando importe real o cantidad por precio."""

    if not _columnas_disponibles(datos, [columna_grupo]):
        return pd.DataFrame(), None, "No se calcularon ventas totales: falta elegir la columna para agrupar."

    if _columnas_disponibles(datos, [columna_importe_venta]):
        importes = datos[columna_importe_venta]
    elif _columnas_disponibles(datos, [columna_cantidad, columna_precio_venta]):
        importes = datos[columna_cantidad] * datos[columna_precio_venta]
    else:
        aviso = (
            "No se calcularon ventas totales: elige un importe de venta o las columnas "
            "cantidad y precio de venta."
        )
        return pd.DataFrame(), None, aviso

    tabla = _agrupar_suma(datos, columna_grupo, importes, "Ventas totales")
    if tabla.empty:
        return tabla, None, "No se calcularon ventas totales: no hay importes válidos."
    return tabla, float(tabla["Ventas totales"].sum()), None


def calcular_precios_por_proveedor(
    datos: pd.DataFrame,
    columna_proveedor: str | None,
    columna_precio_compra: str | None,
    columna_stock: str | None = None,
) -> tuple[pd.DataFrame, dict[str, Any] | None, dict[str, Any] | None, str | None]:
    """Calcula el precio promedio usando proveedores disponibles."""

    if not _columnas_disponibles(datos, [columna_proveedor, columna_precio_compra]):
        aviso = "No se compararon precios: falta elegir proveedor o precio de compra."
        return pd.DataFrame(), None, None, aviso

    columnas = [columna_proveedor, columna_precio_compra]
    excluidos_stock = 0
    if _columnas_disponibles(datos, [columna_stock]):
        columnas.append(columna_stock)
    temporal = datos[columnas]
    if columna_stock in temporal.columns:
        disponible = temporal[columna_stock] > 0
        excluidos_stock = int((~disponible).sum())
        temporal = temporal[disponible]
    temporal = temporal.dropna(subset=[columna_proveedor, columna_precio_compra])
    tabla = (
        temporal.groupby(columna_proveedor, as_index=False)[columna_precio_compra]
        .mean()
        .rename(columns={columna_precio_compra: "Precio promedio"})
        .sort_values("Precio promedio")
        .reset_index(drop=True)
    )
    if tabla.empty:
        if excluidos_stock:
            return tabla, None, None, "No se compararon precios: no hay proveedores con stock mayor que cero."
        return tabla, None, None, "No se compararon precios: no hay precios válidos."

    indice_bajo = tabla["Precio promedio"].idxmin()
    indice_alto = tabla["Precio promedio"].idxmax()
    bajo = {
        "proveedor": tabla.loc[indice_bajo, columna_proveedor],
        "precio": float(tabla.loc[indice_bajo, "Precio promedio"]),
    }
    alto = {
        "proveedor": tabla.loc[indice_alto, columna_proveedor],
        "precio": float(tabla.loc[indice_alto, "Precio promedio"]),
    }
    aviso = None
    if excluidos_stock:
        aviso = f"Se excluyeron {excluidos_stock} registros del precio promedio porque su stock es cero o está vacío."
    return tabla, bajo, alto, aviso


def comparar_proveedores_de_producto(
    datos: pd.DataFrame,
    producto: object | None,
    columna_producto: str | None,
    columna_proveedor: str | None,
    columna_precio_compra: str | None,
    columna_stock: str | None = None,
) -> tuple[pd.DataFrame, str | None]:
    """Compara precios y excluye ofertas cuyo stock sea cero."""

    necesarias = [columna_producto, columna_proveedor, columna_precio_compra]
    if not _columnas_disponibles(datos, necesarias):
        aviso = "No se compararon proveedores por producto: faltan producto, proveedor o precio de compra."
        return pd.DataFrame(), aviso
    if producto is None:
        return pd.DataFrame(), "Elige un producto para comparar sus proveedores."

    mismo_producto = datos[datos[columna_producto] == producto]
    excluidos_stock = 0
    columnas_temporales = [columna_proveedor, columna_precio_compra]
    if _columnas_disponibles(datos, [columna_stock]):
        columnas_temporales.append(columna_stock)
        disponible = mismo_producto[columna_stock] > 0
        excluidos_stock = int((~disponible).sum())
        mismo_producto = mismo_producto[disponible]

    temporal = mismo_producto[columnas_temporales].dropna(
        subset=[columna_proveedor, columna_precio_compra]
    )
    tabla = (
        temporal.groupby(columna_proveedor, as_index=False)[columna_precio_compra]
        .agg(["mean", "min", "max", "count"])
        .reset_index()
        .rename(
            columns={
                "mean": "Precio promedio",
                "min": "Precio mínimo registrado",
                "max": "Precio máximo registrado",
                "count": "Registros comparados",
            }
        )
        .sort_values("Precio promedio")
        .reset_index(drop=True)
    )
    if columna_stock in temporal.columns and not tabla.empty:
        stock = (
            temporal.groupby(columna_proveedor, as_index=False)[columna_stock]
            .max()
            .rename(columns={columna_stock: NOMBRE_STOCK_RESULTADO})
        )
        tabla = tabla.merge(stock, on=columna_proveedor, how="left")
    if tabla.empty:
        if excluidos_stock:
            return tabla, f"No hay proveedores con stock mayor que cero para {producto}."
        return tabla, f"No hay precios válidos para comparar el producto {producto}."
    if excluidos_stock:
        return (
            tabla,
            f"Se excluyeron {excluidos_stock} registros de la comparación porque su stock es cero o está vacío.",
        )
    return tabla, None


def calcular_envio_por_unidad(
    datos: pd.DataFrame,
    columna_envio: str | None,
    tipo_envio: str = "por_unidad",
    columna_cantidad: str | None = None,
) -> tuple[pd.Series | None, list[str]]:
    """Convierte el envío a un costo por unidad para poder compararlo."""

    avisos: list[str] = []
    if not _columnas_disponibles(datos, [columna_envio]):
        avisos.append(
            "No hay una columna de envío del proveedor; se usó 0 provisional para poder comparar."
        )
        return pd.Series(0.0, index=datos.index), avisos

    if tipo_envio == "por_unidad":
        return datos[columna_envio], avisos

    if tipo_envio != "por_pedido":
        avisos.append("No se calculó el envío: el tipo de envío seleccionado no es válido.")
        return None, avisos

    if not _columnas_disponibles(datos, [columna_cantidad]):
        avisos.append(
            "Falta cantidad para dividir el envío del pedido; se usó 0 provisional para poder comparar."
        )
        return pd.Series(0.0, index=datos.index), avisos

    cantidades_validas = datos[columna_cantidad].where(datos[columna_cantidad] > 0)
    envio_unitario = datos[columna_envio] / cantidades_validas
    filas_invalidas = int(
        (datos[columna_envio].notna() & cantidades_validas.isna()).sum()
    )
    if filas_invalidas:
        avisos.append(
            f"{filas_invalidas} filas usaron 0 provisional de envío porque su cantidad está vacía o no es mayor que cero."
        )
    return envio_unitario.fillna(0), avisos


def calcular_costo_logistico_por_peso(
    datos: pd.DataFrame,
    columna_peso: str | None,
    unidad_peso: str = "kg",
    costo_estandar_por_kg: float = 0.0,
    costo_ltl_por_kg: float = 0.0,
    modo_costo_gramaje: str = "por_kg",
) -> tuple[pd.Series | None, list[str]]:
    """Simula un costo por categoría, ya sea fijo o multiplicado por kg."""

    avisos: list[str] = []
    if costo_estandar_por_kg < 0 or costo_ltl_por_kg < 0:
        avisos.append("No se simuló el costo por gramaje: las tarifas no pueden ser negativas.")
        return None, avisos
    if modo_costo_gramaje not in {"por_kg", "fijo"}:
        avisos.append(
            "No se simuló el costo por gramaje: el modo debe ser por_kg o fijo."
        )
        return None, avisos

    # Con ambos costos en cero, el cálculo anterior se conserva sin cambios.
    if costo_estandar_por_kg == 0 and costo_ltl_por_kg == 0:
        return pd.Series(0.0, index=datos.index), avisos

    if not _columnas_disponibles(datos, [columna_peso]):
        avisos.append(
            "Falta el peso: no se agregó la tarifa Estándar/LTL y se usó 0 provisional para poder comparar."
        )
        return pd.Series(0.0, index=datos.index), avisos
    if unidad_peso not in {"kg", "g"}:
        avisos.append("No se simuló el costo por gramaje: la unidad debe ser kg o g.")
        return None, avisos

    peso_kg = datos[columna_peso].copy()
    if unidad_peso == "g":
        peso_kg = peso_kg / 1000

    costo = pd.Series(float("nan"), index=datos.index, dtype="float64")
    estandar = (peso_kg > 0) & (peso_kg <= 20)
    ltl = peso_kg > 20
    if modo_costo_gramaje == "fijo":
        # La tarifa se cobra una sola vez según el tipo de envío.
        costo.loc[estandar] = costo_estandar_por_kg
        costo.loc[ltl] = costo_ltl_por_kg
    else:
        costo.loc[estandar] = peso_kg.loc[estandar] * costo_estandar_por_kg
        costo.loc[ltl] = peso_kg.loc[ltl] * costo_ltl_por_kg

    invalidos = int((~(estandar | ltl)).sum())
    if invalidos:
        avisos.append(
            f"{invalidos} filas usaron 0 provisional de tarifa Estándar/LTL porque el peso está vacío o no es mayor que cero."
        )
    return costo.fillna(0), avisos


def calcular_costo_logistico_por_dimensiones(
    datos: pd.DataFrame,
    columna_volumen: str | None,
    costo_por_m3: float = 0.0,
) -> tuple[pd.Series | None, list[str]]:
    """Simula un costo adicional multiplicando volumen por una tarifa por m³."""

    avisos: list[str] = []
    if costo_por_m3 < 0:
        avisos.append(
            "No se simuló el costo por dimensiones: la tarifa por m³ no puede ser negativa."
        )
        return None, avisos
    if costo_por_m3 == 0:
        return pd.Series(0.0, index=datos.index), avisos
    if not _columnas_disponibles(datos, [columna_volumen]):
        avisos.append(
            "Faltan dimensiones válidas: se usó 0 provisional de costo por volumen para poder comparar."
        )
        return pd.Series(0.0, index=datos.index), avisos

    costo = datos[columna_volumen] * costo_por_m3
    invalidas = int(costo.isna().sum())
    if invalidas:
        avisos.append(
            f"{invalidas} filas usaron 0 provisional de dimensiones porque su volumen no es válido."
        )
    return costo.fillna(0), avisos


def comparar_costo_real_proveedores(
    datos: pd.DataFrame,
    producto: object | None,
    columna_producto: str | None,
    columna_proveedor: str | None,
    columna_precio_compra: str | None,
    columna_envio: str | None,
    tipo_envio: str = "por_unidad",
    columna_cantidad: str | None = None,
    columna_precio_venta: str | None = None,
    columna_tipo_logistico: str | None = None,
    columna_stock: str | None = None,
    columna_peso: str | None = None,
    unidad_peso: str = "kg",
    costo_estandar_por_kg: float = 0.0,
    costo_ltl_por_kg: float = 0.0,
    modo_costo_gramaje: str = "por_kg",
    columna_volumen: str | None = None,
    costo_dimensiones_por_m3: float = 0.0,
) -> tuple[pd.DataFrame, dict[str, Any], list[str]]:
    """Compara compra, envío y costos simulados por peso y dimensiones."""

    avisos: list[str] = []
    indicadores: dict[str, Any] = {}
    necesarias = [columna_producto, columna_proveedor, columna_precio_compra]
    if not _columnas_disponibles(datos, necesarias):
        avisos.append(
            "No se calculó el costo real: faltan producto, proveedor o precio de compra."
        )
        return pd.DataFrame(), indicadores, avisos
    if producto is None:
        avisos.append("Elige un producto para comparar el costo real de sus proveedores.")
        return pd.DataFrame(), indicadores, avisos

    envio_unitario, avisos_envio = calcular_envio_por_unidad(
        datos, columna_envio, tipo_envio, columna_cantidad
    )
    avisos.extend(avisos_envio)
    if envio_unitario is None:
        return pd.DataFrame(), indicadores, avisos

    costo_gramaje, avisos_gramaje = calcular_costo_logistico_por_peso(
        datos,
        columna_peso,
        unidad_peso,
        costo_estandar_por_kg,
        costo_ltl_por_kg,
        modo_costo_gramaje,
    )
    avisos.extend(avisos_gramaje)
    if costo_gramaje is None:
        return pd.DataFrame(), indicadores, avisos

    costo_dimensiones, avisos_dimensiones = calcular_costo_logistico_por_dimensiones(
        datos,
        columna_volumen,
        costo_dimensiones_por_m3,
    )
    avisos.extend(avisos_dimensiones)
    if costo_dimensiones is None:
        return pd.DataFrame(), indicadores, avisos

    mismo_producto = datos[datos[columna_producto] == producto]
    excluidos_stock = 0
    if _columnas_disponibles(datos, [columna_stock]):
        disponible = mismo_producto[columna_stock] > 0
        excluidos_stock = int((~disponible).sum())
        mismo_producto = mismo_producto[disponible]

    temporal = pd.DataFrame(
        {
            columna_proveedor: mismo_producto[columna_proveedor],
            "Precio de compra promedio": mismo_producto[columna_precio_compra],
            "Envío por unidad promedio": envio_unitario.loc[mismo_producto.index],
            NOMBRE_COSTO_GRAMAJE: costo_gramaje.loc[mismo_producto.index],
            NOMBRE_COSTO_DIMENSIONES: costo_dimensiones.loc[mismo_producto.index],
        }
    )
    temporal["Costo real promedio"] = (
        temporal["Precio de compra promedio"]
        + temporal["Envío por unidad promedio"]
        + temporal[NOMBRE_COSTO_GRAMAJE]
        + temporal[NOMBRE_COSTO_DIMENSIONES]
    )

    columnas_promedio = [
        "Costo real promedio",
        "Precio de compra promedio",
        "Envío por unidad promedio",
        NOMBRE_COSTO_GRAMAJE,
        NOMBRE_COSTO_DIMENSIONES,
    ]
    if _columnas_disponibles(datos, [columna_precio_venta]):
        temporal["Precio de venta promedio"] = mismo_producto[columna_precio_venta]
        temporal["Utilidad unitaria promedio"] = (
            temporal["Precio de venta promedio"] - temporal["Costo real promedio"]
        )
        columnas_promedio.extend(
            ["Precio de venta promedio", "Utilidad unitaria promedio"]
        )

    if _columnas_disponibles(datos, [columna_tipo_logistico]):
        temporal[columna_tipo_logistico] = mismo_producto[columna_tipo_logistico]
    if _columnas_disponibles(datos, [columna_stock]):
        temporal[NOMBRE_STOCK_RESULTADO] = mismo_producto[columna_stock]

    temporal = temporal.dropna(
        subset=[
            columna_proveedor,
            "Precio de compra promedio",
            "Envío por unidad promedio",
            NOMBRE_COSTO_GRAMAJE,
            NOMBRE_COSTO_DIMENSIONES,
        ]
    )
    if temporal.empty:
        if excluidos_stock:
            avisos.append(f"No hay proveedores con stock mayor que cero para {producto}.")
        else:
            avisos.append(
                f"No hay precios, envíos, pesos y dimensiones válidos para comparar el producto {producto}."
            )
        return pd.DataFrame(), indicadores, avisos
    if excluidos_stock:
        avisos.append(
            f"Se excluyeron {excluidos_stock} registros del costo y la recomendación porque su stock es cero o está vacío."
        )

    columnas_grupo = [columna_proveedor]
    if _columnas_disponibles(temporal, [columna_tipo_logistico]):
        columnas_grupo.append(columna_tipo_logistico)

    grupos = temporal.groupby(columnas_grupo)
    tabla = grupos[columnas_promedio].mean().reset_index()
    tabla["Registros comparados"] = grupos.size().values
    if NOMBRE_STOCK_RESULTADO in temporal.columns:
        # No sumamos el stock repetido: conservamos el mayor valor registrado.
        tabla[NOMBRE_STOCK_RESULTADO] = grupos[NOMBRE_STOCK_RESULTADO].max().values
    columnas_orden = [columna_proveedor, "Costo real promedio"]
    if columna_tipo_logistico in tabla.columns:
        columnas_orden.append(columna_tipo_logistico)
    columnas_orden.extend(
        columna for columna in tabla.columns if columna not in columnas_orden
    )
    tabla = tabla[columnas_orden]
    tabla = tabla.sort_values("Costo real promedio").reset_index(drop=True)

    # Buscamos el proveedor con el costo real promedio más bajo.
    menor = tabla.loc[tabla["Costo real promedio"].idxmin()]
    indicadores["Menor costo real con envío"] = {
        "producto": producto,
        "proveedor": menor[columna_proveedor],
        "costo_real": float(menor["Costo real promedio"]),
    }
    if columna_tipo_logistico in tabla.columns:
        indicadores["Menor costo real con envío"]["tipo_logistico"] = menor[
            columna_tipo_logistico
        ]

    if "Utilidad unitaria promedio" in tabla.columns:
        utilidades_validas = tabla["Utilidad unitaria promedio"].dropna()
        if not utilidades_validas.empty:
            mayor = tabla.loc[utilidades_validas.idxmax()]
            indicadores["Mayor utilidad unitaria con envío"] = {
                "producto": producto,
                "proveedor": mayor[columna_proveedor],
                "utilidad": float(mayor["Utilidad unitaria promedio"]),
            }
            if columna_tipo_logistico in tabla.columns:
                indicadores["Mayor utilidad unitaria con envío"][
                    "tipo_logistico"
                ] = mayor[columna_tipo_logistico]
    return tabla, indicadores, avisos


def calcular_cotizacion_proveedores(
    tabla_costos: pd.DataFrame,
    columna_proveedor: str | None,
    numero_unidades: int = 1,
    envio_cobrado_cliente: float = 0.0,
    comision_plataforma_pct: float = 0.0,
    promocion_digital_pct: float = 0.0,
    margen_ganancia_pct: float = 0.0,
    tasa_iva_pct: float = 16.0,
    columna_tipo_logistico: str | None = None,
    columna_stock_resultado: str = NOMBRE_STOCK_RESULTADO,
) -> tuple[pd.DataFrame, dict[str, Any], list[str]]:
    """Calcula una cotización comparable a partir del costo de cada proveedor."""

    avisos: list[str] = []
    indicadores: dict[str, Any] = {}
    if tabla_costos.empty or columna_proveedor not in tabla_costos.columns:
        return pd.DataFrame(), indicadores, avisos
    if numero_unidades <= 0:
        avisos.append("No se calculó la cotización: el número de unidades debe ser mayor que cero.")
        return pd.DataFrame(), indicadores, avisos
    if envio_cobrado_cliente < 0:
        avisos.append("No se calculó la cotización: el envío cobrado al cliente no puede ser negativo.")
        return pd.DataFrame(), indicadores, avisos

    porcentajes = [
        comision_plataforma_pct,
        promocion_digital_pct,
        margen_ganancia_pct,
        tasa_iva_pct,
    ]
    if any(valor < 0 for valor in porcentajes):
        avisos.append("No se calculó la cotización: los porcentajes no pueden ser negativos.")
        return pd.DataFrame(), indicadores, avisos

    comision = comision_plataforma_pct / 100
    promocion = promocion_digital_pct / 100
    margen = margen_ganancia_pct / 100
    iva = tasa_iva_pct / 100
    if comision + promocion + margen >= 1:
        avisos.append(
            "No se calculó la cotización: la suma de comisión, promoción y margen debe ser menor que 100%."
        )
        return pd.DataFrame(), indicadores, avisos

    cotizacion = tabla_costos.copy()
    if columna_stock_resultado in cotizacion.columns:
        alcanza = cotizacion[columna_stock_resultado] >= numero_unidades
        excluidos = int((~alcanza).sum())
        cotizacion = cotizacion[alcanza].copy()
        if excluidos:
            avisos.append(
                f"Se excluyeron {excluidos} proveedores de la cotización porque no tienen stock suficiente para {numero_unidades} unidades."
            )
        if cotizacion.empty:
            avisos.append(
                f"No se calculó la cotización: ningún proveedor tiene stock suficiente para {numero_unidades} unidades."
            )
            return pd.DataFrame(), indicadores, avisos

    cotizacion["Número de unidades"] = numero_unidades
    cotizacion["Costo real total"] = (
        cotizacion["Costo real promedio"] * numero_unidades
    )
    # Sumamos solamente los conceptos de envío que sí existen en los datos.
    componentes_envio = [
        columna
        for columna in [
            "Envío por unidad promedio",
            NOMBRE_COSTO_GRAMAJE,
            NOMBRE_COSTO_DIMENSIONES,
        ]
        if columna in cotizacion.columns
    ]
    cotizacion["Costo de envío interno por unidad"] = (
        cotizacion[componentes_envio].fillna(0).sum(axis=1)
        if componentes_envio
        else 0.0
    )
    cotizacion["Costo de envío interno total"] = (
        cotizacion["Costo de envío interno por unidad"] * numero_unidades
    )
    if "Precio de compra promedio" not in cotizacion.columns:
        cotizacion["Precio de compra promedio"] = (
            cotizacion["Costo real promedio"]
            - cotizacion["Costo de envío interno por unidad"]
        ).clip(lower=0)
    cotizacion["Costo del producto total"] = (
        cotizacion["Precio de compra promedio"] * numero_unidades
    )
    # El precio del producto se calcula primero, sin incluir el envío.
    cotizacion["Precio producto sin IVA"] = cotizacion["Costo del producto total"] / (
        1 - comision - promocion - margen
    )
    cotizacion["Comisión de plataforma"] = (
        cotizacion["Precio producto sin IVA"] * comision
    )
    cotizacion["Promoción digital"] = (
        cotizacion["Precio producto sin IVA"] * promocion
    )
    cotizacion["Ganancia objetivo"] = (
        cotizacion["Precio producto sin IVA"] * margen
    )
    cotizacion["Envío cobrado al cliente"] = envio_cobrado_cliente
    cotizacion["IVA del precio de venta"] = cotizacion["Precio producto sin IVA"] * iva
    cotizacion["Precio de venta con IVA"] = (
        cotizacion["Precio producto sin IVA"] + cotizacion["IVA del precio de venta"]
    ).round(2)
    cotizacion["Precio de venta por unidad con IVA"] = (
        cotizacion["Precio de venta con IVA"] / numero_unidades
    )
    cotizacion["IVA del envío al cliente"] = envio_cobrado_cliente * iva
    cotizacion["Envío al cliente con IVA"] = (
        cotizacion["Envío cobrado al cliente"]
        + cotizacion["IVA del envío al cliente"]
    )
    cotizacion["Envío total sumado"] = (
        cotizacion["Costo de envío interno total"]
        + cotizacion["Envío al cliente con IVA"]
    ).round(2)
    cotizacion["Subtotal sin IVA"] = (
        cotizacion["Precio producto sin IVA"] + envio_cobrado_cliente
    )
    cotizacion["IVA"] = cotizacion["Subtotal sin IVA"] * iva
    # Redondeamos a centavos antes de sumar para que los importes visibles cuadren.
    cotizacion["Precio total cliente con IVA"] = (
        cotizacion["Precio de venta con IVA"] + cotizacion["Envío total sumado"]
    ).round(2)
    cotizacion["Total venta + envío con IVA"] = cotizacion[
        "Precio total cliente con IVA"
    ]
    cotizacion["Precio por unidad con IVA"] = (
        cotizacion["Precio total cliente con IVA"] / numero_unidades
    )

    columnas = [columna_proveedor]
    for columna_resumen in [
        columna_tipo_logistico,
        "Precio de compra promedio",
        "Costo de envío interno por unidad",
        "Costo de envío interno total",
        "Envío total sumado",
        "Precio de venta con IVA",
        "Precio de venta por unidad con IVA",
        "Envío al cliente con IVA",
        "Total venta + envío con IVA",
        "Precio por unidad con IVA",
        columna_stock_resultado,
    ]:
        if columna_resumen in cotizacion.columns and columna_resumen not in columnas:
            columnas.append(columna_resumen)
    columnas.extend(
        [
            "Número de unidades",
            "Costo real promedio",
            "Costo real total",
            "Costo del producto total",
            "Precio producto sin IVA",
            "Comisión de plataforma",
            "Promoción digital",
            "Ganancia objetivo",
            "IVA del precio de venta",
            "Envío cobrado al cliente",
            "IVA del envío al cliente",
            "Subtotal sin IVA",
            "IVA",
            "Precio total cliente con IVA",
        ]
    )
    cotizacion = cotizacion[columnas].sort_values(
        "Precio total cliente con IVA"
    ).reset_index(drop=True)

    menor = cotizacion.loc[cotizacion["Precio total cliente con IVA"].idxmin()]
    indicadores["Cotización económica"] = {
        "proveedor": menor[columna_proveedor],
        "precio_total": float(menor["Precio total cliente con IVA"]),
        "precio_unidad": float(menor["Precio por unidad con IVA"]),
        "numero_unidades": numero_unidades,
    }
    if columna_tipo_logistico in cotizacion.columns:
        indicadores["Cotización económica"]["tipo_logistico"] = menor[
            columna_tipo_logistico
        ]
    return cotizacion, indicadores, avisos


def simular_monte_carlo_proveedores(
    tabla_costos: pd.DataFrame,
    columna_proveedor: str | None,
    numero_unidades: int = 1,
    envio_cobrado_cliente: float = 0.0,
    comision_plataforma_pct: float = 0.0,
    promocion_digital_pct: float = 0.0,
    margen_ganancia_pct: float = 0.0,
    tasa_iva_pct: float = 16.0,
    variacion_compra_pct: float = 5.0,
    variacion_logistica_pct: float = 10.0,
    iteraciones: int = 5000,
    semilla: int = 42,
    columna_stock_resultado: str = NOMBRE_STOCK_RESULTADO,
) -> tuple[pd.DataFrame, dict[str, Any], list[str]]:
    """Repite escenarios inciertos y estima qué proveedor resulta más económico."""

    avisos: list[str] = []
    indicadores: dict[str, Any] = {}
    necesarias = [
        columna_proveedor,
        "Precio de compra promedio",
        "Envío por unidad promedio",
        NOMBRE_COSTO_GRAMAJE,
    ]
    if tabla_costos.empty or not _columnas_disponibles(tabla_costos, necesarias):
        avisos.append(
            "No se ejecutó Monte Carlo: primero se necesitan costos válidos por proveedor."
        )
        return pd.DataFrame(), indicadores, avisos
    if numero_unidades <= 0 or iteraciones < 100:
        avisos.append(
            "No se ejecutó Monte Carlo: usa unidades mayores que cero y al menos 100 simulaciones."
        )
        return pd.DataFrame(), indicadores, avisos
    if variacion_compra_pct < 0 or variacion_logistica_pct < 0:
        avisos.append("No se ejecutó Monte Carlo: las variaciones no pueden ser negativas.")
        return pd.DataFrame(), indicadores, avisos

    comision = comision_plataforma_pct / 100
    promocion = promocion_digital_pct / 100
    margen = margen_ganancia_pct / 100
    iva = tasa_iva_pct / 100
    if (
        min(comision, promocion, margen, iva) < 0
        or comision + promocion + margen >= 1
    ):
        avisos.append(
            "No se ejecutó Monte Carlo: revisa comisión, promoción, margen e IVA; los tres primeros deben sumar menos de 100%."
        )
        return pd.DataFrame(), indicadores, avisos

    proveedores = tabla_costos.copy()
    if NOMBRE_COSTO_DIMENSIONES not in proveedores.columns:
        proveedores[NOMBRE_COSTO_DIMENSIONES] = 0.0
    if columna_stock_resultado in proveedores.columns:
        alcanza = proveedores[columna_stock_resultado] >= numero_unidades
        excluidos = int((~alcanza).sum())
        proveedores = proveedores[alcanza].reset_index(drop=True)
        if excluidos:
            avisos.append(
                f"Monte Carlo excluyó {excluidos} proveedores sin stock suficiente para {numero_unidades} unidades."
            )
        if proveedores.empty:
            avisos.append("No se ejecutó Monte Carlo: ningún proveedor tiene stock suficiente.")
            return pd.DataFrame(), indicadores, avisos
    proveedores = proveedores.reset_index(drop=True)

    # La semilla hace que la misma configuración produzca el mismo resultado.
    generador = random.Random(semilla)
    desviacion_compra = variacion_compra_pct / 100
    desviacion_logistica = variacion_logistica_pct / 100
    precios_simulados: list[list[float]] = [[] for _ in range(len(proveedores))]
    escenarios_ganados = [0 for _ in range(len(proveedores))]

    # Repetimos muchos futuros posibles para comparar proveedores bajo incertidumbre.
    for _ in range(iteraciones):
        precios_del_escenario: list[float] = []
        for posicion, fila in proveedores.iterrows():
            compra_base = float(fila["Precio de compra promedio"])
            logistica_base = float(
                fila["Envío por unidad promedio"]
                + fila[NOMBRE_COSTO_GRAMAJE]
                + fila[NOMBRE_COSTO_DIMENSIONES]
            )
            compra = max(0.0, generador.gauss(compra_base, abs(compra_base) * desviacion_compra))
            logistica = max(
                0.0,
                generador.gauss(logistica_base, abs(logistica_base) * desviacion_logistica),
            )
            costo_producto_total = compra * numero_unidades
            precio_sin_iva = costo_producto_total / (1 - comision - promocion - margen)
            precio_venta_con_iva = precio_sin_iva * (1 + iva)
            envio_total = (
                logistica * numero_unidades
                + envio_cobrado_cliente * (1 + iva)
            )
            precio_cliente = precio_venta_con_iva + envio_total
            precios_simulados[posicion].append(precio_cliente)
            precios_del_escenario.append(precio_cliente)

        # Buscamos el valor más bajo en cada escenario.
        ganador = min(range(len(precios_del_escenario)), key=precios_del_escenario.__getitem__)
        escenarios_ganados[ganador] += 1

    filas: list[dict[str, object]] = []
    for posicion, fila in proveedores.iterrows():
        serie = pd.Series(precios_simulados[posicion], dtype="float64")
        resultado_fila: dict[str, object] = {
            columna_proveedor: fila[columna_proveedor],
            "Probabilidad de ser más económico (%)": escenarios_ganados[posicion] / iteraciones * 100,
            "Precio total promedio simulado": float(serie.mean()),
            "Escenario favorable (percentil 5)": float(serie.quantile(0.05)),
            "Escenario desfavorable (percentil 95)": float(serie.quantile(0.95)),
            "Simulaciones": iteraciones,
        }
        if columna_stock_resultado in proveedores.columns:
            resultado_fila[columna_stock_resultado] = fila[columna_stock_resultado]
        filas.append(resultado_fila)

    tabla = pd.DataFrame(filas).sort_values(
        ["Probabilidad de ser más económico (%)", "Precio total promedio simulado"],
        ascending=[False, True],
    ).reset_index(drop=True)
    recomendado = tabla.iloc[0]
    indicadores["Recomendación Monte Carlo"] = {
        "proveedor": recomendado[columna_proveedor],
        "probabilidad_economica": float(recomendado["Probabilidad de ser más económico (%)"]),
        "precio_promedio_simulado": float(recomendado["Precio total promedio simulado"]),
        "iteraciones": iteraciones,
    }
    return tabla, indicadores, avisos


def calcular_utilidad(
    datos: pd.DataFrame,
    columna_producto: str | None,
    columna_proveedor: str | None,
    columna_precio_compra: str | None,
    columna_precio_venta: str | None,
    columna_cantidad: str | None = None,
    columna_envio: str | None = None,
    tipo_envio: str = "por_unidad",
    columna_peso: str | None = None,
    unidad_peso: str = "kg",
    costo_estandar_por_kg: float = 0.0,
    costo_ltl_por_kg: float = 0.0,
    modo_costo_gramaje: str = "por_kg",
    columna_volumen: str | None = None,
    costo_dimensiones_por_m3: float = 0.0,
) -> tuple[dict[str, pd.DataFrame], dict[str, float], list[str]]:
    """Calcula utilidad restando compra, envío, peso y dimensiones."""

    tablas: dict[str, pd.DataFrame] = {}
    indicadores: dict[str, float] = {}
    avisos: list[str] = []

    if not _columnas_disponibles(datos, [columna_precio_compra, columna_precio_venta]):
        avisos.append("No se calculó utilidad: faltan precio de compra o precio de venta.")
        return tablas, indicadores, avisos

    envio_unitario, avisos_envio = calcular_envio_por_unidad(
        datos, columna_envio, tipo_envio, columna_cantidad
    )
    avisos.extend(avisos_envio)
    if envio_unitario is None:
        return tablas, indicadores, avisos

    costo_gramaje, avisos_gramaje = calcular_costo_logistico_por_peso(
        datos,
        columna_peso,
        unidad_peso,
        costo_estandar_por_kg,
        costo_ltl_por_kg,
        modo_costo_gramaje,
    )
    avisos.extend(avisos_gramaje)
    if costo_gramaje is None:
        return tablas, indicadores, avisos

    costo_dimensiones, avisos_dimensiones = calcular_costo_logistico_por_dimensiones(
        datos,
        columna_volumen,
        costo_dimensiones_por_m3,
    )
    avisos.extend(avisos_dimensiones)
    if costo_dimensiones is None:
        return tablas, indicadores, avisos

    costo_real_unitario = (
        datos[columna_precio_compra]
        + envio_unitario
        + costo_gramaje
        + costo_dimensiones
    )
    utilidad_unitaria = datos[columna_precio_venta] - costo_real_unitario
    if utilidad_unitaria.dropna().empty:
        avisos.append(
            "No se calculó utilidad: no hay filas con precio de compra y precio de venta válidos."
        )
        return tablas, indicadores, avisos
    indicadores["Utilidad unitaria promedio"] = float(utilidad_unitaria.mean())

    if _columnas_disponibles(datos, [columna_cantidad]):
        utilidad = utilidad_unitaria * datos[columna_cantidad]
        nombre_valor = "Utilidad total"
        indicadores[nombre_valor] = float(utilidad.sum())
    else:
        utilidad = utilidad_unitaria
        nombre_valor = "Utilidad unitaria acumulada"
        avisos.append(
            "La utilidad total no se calculó porque falta cantidad; se muestra utilidad por unidad."
        )

    if _columnas_disponibles(datos, [columna_producto]):
        tablas["utilidad_por_producto"] = _agrupar_suma(
            datos, columna_producto, utilidad, nombre_valor
        )
    if _columnas_disponibles(datos, [columna_proveedor]):
        tablas["utilidad_por_proveedor"] = _agrupar_suma(
            datos, columna_proveedor, utilidad, nombre_valor
        )
    return tablas, indicadores, avisos


def analizar_datos(
    datos: pd.DataFrame,
    columna_producto: str | None = None,
    columna_proveedor: str | None = None,
    columna_cantidad: str | None = None,
    columna_precio_compra: str | None = None,
    columna_precio_venta: str | None = None,
    columna_importe_venta: str | None = None,
    columna_envio: str | None = None,
    tipo_envio: str = "por_unidad",
    columna_tipo_logistico: str | None = None,
    columna_stock: str | None = None,
    columna_peso: str | None = None,
    unidad_peso: str = "kg",
    costo_estandar_por_kg: float = 0.0,
    costo_ltl_por_kg: float = 0.0,
    modo_costo_gramaje: str = "por_kg",
    columna_volumen: str | None = None,
    costo_dimensiones_por_m3: float = 0.0,
    numero_unidades: int = 1,
    envio_cobrado_cliente: float = 0.0,
    comision_plataforma_pct: float = 0.0,
    promocion_digital_pct: float = 0.0,
    margen_ganancia_pct: float = 0.0,
    tasa_iva_pct: float = 16.0,
    variacion_compra_pct: float = 5.0,
    variacion_logistica_pct: float = 10.0,
    iteraciones_monte_carlo: int = 5000,
    semilla_monte_carlo: int = 42,
    producto_para_comparar: object | None = None,
) -> dict[str, Any]:
    """Ejecuta todos los análisis posibles sin fallar por columnas ausentes."""

    resultado: dict[str, Any] = {
        "indicadores": {},
        "tablas": {},
        "avisos": [],
        "conclusiones": [],
    }
    # La recomendación siempre explica qué tan completa es la información usada.
    disponibilidad_decision = {
        "producto": _columnas_disponibles(datos, [columna_producto]),
        "proveedor": _columnas_disponibles(datos, [columna_proveedor]),
        "precio de compra": _columnas_disponibles(datos, [columna_precio_compra]),
        "stock": _columnas_disponibles(datos, [columna_stock]),
        "envío del proveedor": _columnas_disponibles(datos, [columna_envio]),
        "peso": _columnas_disponibles(datos, [columna_peso]),
    }
    faltantes_decision = [
        nombre for nombre, disponible in disponibilidad_decision.items() if not disponible
    ]
    if all(disponibilidad_decision.values()):
        nivel_confianza = "Alta"
    elif (
        disponibilidad_decision["proveedor"]
        and disponibilidad_decision["precio de compra"]
        and disponibilidad_decision["stock"]
    ):
        nivel_confianza = "Media"
    elif disponibilidad_decision["proveedor"] and disponibilidad_decision["precio de compra"]:
        nivel_confianza = "Baja"
    elif disponibilidad_decision["proveedor"]:
        nivel_confianza = "Muy baja"
    else:
        nivel_confianza = "No disponible"
    resultado["indicadores"]["Calidad de recomendación"] = {
        "nivel": nivel_confianza,
        "faltantes": faltantes_decision,
        "stock_verificado": disponibilidad_decision["stock"],
        "provisional": nivel_confianza != "Alta",
    }
    if disponibilidad_decision["proveedor"]:
        proveedores_respaldo = datos[[columna_proveedor]].dropna().copy()
        criterio_respaldo = "orden alfabético, porque faltan precio y stock"
        if disponibilidad_decision["stock"]:
            proveedores_respaldo[columna_stock] = datos.loc[
                proveedores_respaldo.index, columna_stock
            ]
            proveedores_respaldo = proveedores_respaldo[
                proveedores_respaldo[columna_stock] > 0
            ]
            proveedores_respaldo = (
                proveedores_respaldo.groupby(columna_proveedor, as_index=False)[columna_stock]
                .max()
                .sort_values([columna_stock, columna_proveedor], ascending=[False, True])
            )
            criterio_respaldo = "mayor stock disponible"
        else:
            proveedores_respaldo = proveedores_respaldo.drop_duplicates().sort_values(
                columna_proveedor
            )
        if not proveedores_respaldo.empty:
            resultado["indicadores"]["Proveedor de respaldo"] = {
                "proveedor": proveedores_respaldo.iloc[0][columna_proveedor],
                "criterio": criterio_respaldo,
            }
    if not _columnas_disponibles(datos, [columna_stock]):
        resultado["avisos"].append(
            "No se verificó disponibilidad: falta elegir una columna de stock."
        )

    mas_vendido, tabla_cantidades, aviso = calcular_producto_mas_vendido(
        datos, columna_producto, columna_cantidad
    )
    if mas_vendido:
        resultado["indicadores"]["Producto más vendido"] = mas_vendido
        resultado["tablas"]["cantidad_por_producto"] = tabla_cantidades
    if aviso:
        resultado["avisos"].append(aviso)

    ventas_producto, total_producto, aviso = calcular_ventas_totales(
        datos,
        columna_producto,
        columna_importe_venta,
        columna_cantidad,
        columna_precio_venta,
    )
    if not ventas_producto.empty:
        resultado["tablas"]["ventas_por_producto"] = ventas_producto
        resultado["indicadores"]["Ventas totales"] = total_producto
    if aviso:
        resultado["avisos"].append(aviso)

    ventas_proveedor, _, aviso = calcular_ventas_totales(
        datos,
        columna_proveedor,
        columna_importe_venta,
        columna_cantidad,
        columna_precio_venta,
    )
    if not ventas_proveedor.empty:
        resultado["tablas"]["ventas_por_proveedor"] = ventas_proveedor
    if aviso:
        resultado["avisos"].append(aviso.replace("ventas totales", "ventas por proveedor", 1))

    precios, bajo, alto, aviso = calcular_precios_por_proveedor(
        datos, columna_proveedor, columna_precio_compra, columna_stock
    )
    if not precios.empty:
        resultado["tablas"]["precio_promedio_por_proveedor"] = precios
        resultado["indicadores"]["Precio promedio más bajo"] = bajo
        resultado["indicadores"]["Precio promedio más alto"] = alto
    if aviso:
        resultado["avisos"].append(aviso)

    comparacion, aviso = comparar_proveedores_de_producto(
        datos,
        producto_para_comparar,
        columna_producto,
        columna_proveedor,
        columna_precio_compra,
        columna_stock,
    )
    if not comparacion.empty:
        resultado["tablas"]["comparacion_proveedores_producto"] = comparacion
    if aviso:
        resultado["avisos"].append(aviso)

    costos_reales, indicadores_costos, avisos_costos = comparar_costo_real_proveedores(
        datos,
        producto_para_comparar,
        columna_producto,
        columna_proveedor,
        columna_precio_compra,
        columna_envio,
        tipo_envio,
        columna_cantidad,
        columna_precio_venta,
        columna_tipo_logistico,
        columna_stock,
        columna_peso,
        unidad_peso,
        costo_estandar_por_kg,
        costo_ltl_por_kg,
        modo_costo_gramaje,
        columna_volumen,
        costo_dimensiones_por_m3,
    )
    if not costos_reales.empty:
        resultado["tablas"]["costo_real_proveedores_producto"] = costos_reales
    resultado["indicadores"].update(indicadores_costos)
    resultado["avisos"].extend(avisos_costos)

    cotizacion, indicadores_cotizacion, avisos_cotizacion = calcular_cotizacion_proveedores(
        costos_reales,
        columna_proveedor,
        numero_unidades,
        envio_cobrado_cliente,
        comision_plataforma_pct,
        promocion_digital_pct,
        margen_ganancia_pct,
        tasa_iva_pct,
        columna_tipo_logistico,
    )
    if not cotizacion.empty:
        resultado["tablas"]["cotizacion_proveedores"] = cotizacion
    resultado["indicadores"].update(indicadores_cotizacion)
    resultado["avisos"].extend(avisos_cotizacion)

    monte_carlo, indicadores_monte_carlo, avisos_monte_carlo = simular_monte_carlo_proveedores(
        costos_reales,
        columna_proveedor,
        numero_unidades,
        envio_cobrado_cliente,
        comision_plataforma_pct,
        promocion_digital_pct,
        margen_ganancia_pct,
        tasa_iva_pct,
        variacion_compra_pct,
        variacion_logistica_pct,
        iteraciones_monte_carlo,
        semilla_monte_carlo,
    )
    if not monte_carlo.empty:
        resultado["tablas"]["monte_carlo_proveedores"] = monte_carlo
    resultado["indicadores"].update(indicadores_monte_carlo)
    resultado["avisos"].extend(avisos_monte_carlo)

    tablas_utilidad, indicadores_utilidad, avisos_utilidad = calcular_utilidad(
        datos,
        columna_producto,
        columna_proveedor,
        columna_precio_compra,
        columna_precio_venta,
        columna_cantidad,
        columna_envio,
        tipo_envio,
        columna_peso,
        unidad_peso,
        costo_estandar_por_kg,
        costo_ltl_por_kg,
        modo_costo_gramaje,
        columna_volumen,
        costo_dimensiones_por_m3,
    )
    resultado["tablas"].update(tablas_utilidad)
    resultado["indicadores"].update(indicadores_utilidad)
    resultado["avisos"].extend(avisos_utilidad)
    resultado["avisos"] = list(dict.fromkeys(resultado["avisos"]))
    resultado["conclusiones"] = crear_conclusiones(resultado)
    return resultado


def crear_conclusiones(resultado: dict[str, Any]) -> list[str]:
    """Redacta conclusiones prudentes a partir de cálculos disponibles."""

    indicadores = resultado.get("indicadores", {})
    conclusiones: list[str] = []

    vendido = indicadores.get("Producto más vendido")
    if vendido:
        conclusiones.append(
            f"El producto con mayor cantidad registrada es {vendido['producto']} "
            f"con {vendido['cantidad']:,.2f} unidades."
        )

    if indicadores.get("Ventas totales") is not None:
        conclusiones.append(
            f"Las ventas suman {indicadores['Ventas totales']:,.2f} en los registros analizados."
        )

    bajo = indicadores.get("Precio promedio más bajo")
    alto = indicadores.get("Precio promedio más alto")
    if bajo and alto:
        conclusiones.append(
            f"{bajo['proveedor']} tiene el precio promedio registrado más bajo "
            f"({bajo['precio']:,.2f}) y {alto['proveedor']} el más alto "
            f"({alto['precio']:,.2f})."
        )
        conclusiones.append(
            "Un precio menor no convierte automáticamente a un proveedor en el mejor: "
            "también conviene revisar calidad, tiempos de entrega, disponibilidad y condiciones de pago."
        )

    if indicadores.get("Utilidad total") is not None:
        conclusiones.append(
            f"La utilidad histórica estimada es {indicadores['Utilidad total']:,.2f} antes de "
            "comisiones e IVA; depende de que compra, venta, envío y cantidad estén correctamente registrados."
        )

    costo_real = indicadores.get("Menor costo real con envío")
    if costo_real:
        tipo = (
            f" en {costo_real['tipo_logistico']}"
            if costo_real.get("tipo_logistico")
            else ""
        )
        conclusiones.append(
            f"Para {costo_real['producto']}{tipo}, {costo_real['proveedor']} presenta el menor "
            f"costo real promedio ({costo_real['costo_real']:,.2f}) al sumar compra, envío y "
            "los costos configurados por gramaje y dimensiones."
        )
        conclusiones.append(
            "Ese proveedor conviene según el criterio económico disponible, pero la decisión final "
            "también debe considerar calidad, entrega, disponibilidad, garantías y condiciones de pago."
        )

    mayor_utilidad = indicadores.get("Mayor utilidad unitaria con envío")
    if mayor_utilidad:
        conclusiones.append(
            f"Para {mayor_utilidad['producto']}, {mayor_utilidad['proveedor']} deja la mayor "
            f"utilidad unitaria promedio estimada ({mayor_utilidad['utilidad']:,.2f}) después del envío."
        )

    cotizacion = indicadores.get("Cotización económica")
    if cotizacion:
        palabra_unidades = "unidad" if cotizacion["numero_unidades"] == 1 else "unidades"
        tipo = (
            f" en la categoría {cotizacion['tipo_logistico']}"
            if cotizacion.get("tipo_logistico")
            else ""
        )
        conclusiones.append(
            f"Para {cotizacion['numero_unidades']} {palabra_unidades}{tipo}, {cotizacion['proveedor']} "
            f"genera la cotización más baja: {cotizacion['precio_total']:,.2f} con IVA, "
            f"equivalente a {cotizacion['precio_unidad']:,.2f} por unidad."
        )
        conclusiones.append(
            "La cotización recupera el costo de la comisión, la promoción digital y el margen "
            "configurados antes de agregar IVA; confirma las reglas particulares de cada plataforma."
        )

    monte_carlo = indicadores.get("Recomendación Monte Carlo")
    if monte_carlo:
        conclusiones.append(
            f"En {monte_carlo['iteraciones']:,} escenarios Monte Carlo, "
            f"{monte_carlo['proveedor']} fue la alternativa económica en "
            f"{monte_carlo['probabilidad_economica']:.1f}% de las simulaciones, con un "
            f"precio total promedio de {monte_carlo['precio_promedio_simulado']:,.2f}."
        )
        conclusiones.append(
            "Monte Carlo compara incertidumbre de precio y logística; no mide por sí solo calidad, "
            "puntualidad, garantías ni condiciones de pago."
        )

    if not conclusiones:
        conclusiones.append(
            "Todavía no hay columnas suficientes para generar conclusiones; revisa las selecciones."
        )
    return conclusiones


def _indicadores_como_tabla(indicadores: dict[str, Any]) -> pd.DataFrame:
    """Convierte indicadores variados en una tabla fácil de exportar."""

    filas: list[dict[str, object]] = []
    for nombre, valor in indicadores.items():
        if isinstance(valor, dict):
            detalle = ", ".join(f"{clave}: {dato}" for clave, dato in valor.items())
        else:
            detalle = valor
        filas.append({"Indicador": nombre, "Resultado": detalle})
    return pd.DataFrame(filas)


def exportar_resultados_excel(datos_limpios: pd.DataFrame, resultado: dict[str, Any]) -> bytes:
    """Crea un Excel nuevo con datos limpios, indicadores, tablas y conclusiones."""

    salida = BytesIO()
    nombres_hoja = {
        "cantidad_por_producto": "Cantidad producto",
        "ventas_por_producto": "Ventas producto",
        "ventas_por_proveedor": "Ventas proveedor",
        "precio_promedio_por_proveedor": "Precios proveedor",
        "comparacion_proveedores_producto": "Comparacion producto",
        "costo_real_proveedores_producto": "Costo real proveedor",
        "cotizacion_proveedores": "Cotizacion proveedor",
        "monte_carlo_proveedores": "Monte Carlo",
        "utilidad_por_producto": "Utilidad producto",
        "utilidad_por_proveedor": "Utilidad proveedor",
    }

    with pd.ExcelWriter(salida, engine="openpyxl") as escritor:
        datos_limpios.to_excel(escritor, index=False, sheet_name="Datos limpios")
        _indicadores_como_tabla(resultado.get("indicadores", {})).to_excel(
            escritor, index=False, sheet_name="Indicadores"
        )
        for clave, tabla in resultado.get("tablas", {}).items():
            if not tabla.empty:
                tabla.to_excel(
                    escritor,
                    index=False,
                    sheet_name=nombres_hoja.get(clave, clave[:31]),
                )
        pd.DataFrame(
            {"Conclusiones": resultado.get("conclusiones", [])}
        ).to_excel(escritor, index=False, sheet_name="Conclusiones")

        # Damos formato básico para que cada hoja sea fácil de leer.
        for hoja in escritor.book.worksheets:
            hoja.freeze_panes = "A2"
            hoja.auto_filter.ref = hoja.dimensions
            for celda in hoja[1]:
                fuente = copy(celda.font)
                fuente.bold = True
                celda.font = fuente
            for columna in hoja.columns:
                ancho = min(max(len(str(celda.value or "")) for celda in columna) + 2, 45)
                hoja.column_dimensions[columna[0].column_letter].width = ancho

    return salida.getvalue()


def exportar_resultados_csv(resultado: dict[str, Any]) -> bytes:
    """Une resultados distintos en un CSV largo con sección, registro y campo."""

    filas: list[dict[str, object]] = []
    for nombre, valor in resultado.get("indicadores", {}).items():
        filas.append(
            {
                "Sección": "Indicadores",
                "Tabla": nombre,
                "Registro": 1,
                "Campo": "Resultado",
                "Valor": str(valor),
            }
        )

    for nombre_tabla, tabla in resultado.get("tablas", {}).items():
        for numero, (_, fila) in enumerate(tabla.iterrows(), start=1):
            for campo, valor in fila.items():
                filas.append(
                    {
                        "Sección": "Tablas",
                        "Tabla": nombre_tabla,
                        "Registro": numero,
                        "Campo": campo,
                        "Valor": valor,
                    }
                )

    for numero, conclusion in enumerate(resultado.get("conclusiones", []), start=1):
        filas.append(
            {
                "Sección": "Conclusiones",
                "Tabla": "conclusiones",
                "Registro": numero,
                "Campo": "Texto",
                "Valor": conclusion,
            }
        )
    return pd.DataFrame(filas).to_csv(index=False).encode("utf-8-sig")


def dataframe_a_excel(datos: pd.DataFrame, nombre_hoja: str = "Resultados") -> bytes:
    """Convierte una tabla en bytes para descargarla como archivo Excel."""

    salida = BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as escritor:
        datos.to_excel(escritor, index=False, sheet_name=nombre_hoja[:31])
    return salida.getvalue()


def dataframe_a_csv(datos: pd.DataFrame) -> bytes:
    """Convierte una tabla a CSV con UTF-8 para conservar letras y acentos."""

    return datos.to_csv(index=False).encode("utf-8-sig")
