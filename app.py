"""Aplicación web para comparar proveedores y publicarla en Vercel.

FastAPI recibe los Excel o CSV, reutiliza las funciones educativas de
``analisis.py`` y devuelve resultados que la pantalla puede mostrar.
Los archivos se procesan en memoria: nunca se modifican ni se guardan.
"""

from __future__ import annotations

import base64
from email import policy
from email.parser import BytesParser
from io import BytesIO
import json
import math
from pathlib import Path
import unicodedata
from typing import Any
from wsgiref.simple_server import make_server

# Importamos pandas para trabajar con tablas
import pandas as pd

from analisis import (
    agregar_clasificacion_gramaje,
    agregar_volumen_dimensiones,
    analizar_datos,
    cargar_varios_archivos,
    describir_columnas,
    exportar_resultados_csv,
    exportar_resultados_excel,
    limpiar_datos,
)


CARPETA_PROYECTO = Path(__file__).parent
ARCHIVO_DEMO = CARPETA_PROYECTO / "datos_demostracion.csv"
EXTENSIONES_PERMITIDAS = {".csv", ".xlsx", ".xls"}
MAXIMO_ARCHIVOS = 8
MAXIMO_TOTAL_BYTES = 4_000_000


class ErrorApi(Exception):
    """Error comprensible que se enviará a la pantalla como JSON."""

    def __init__(self, estado: int, detalle: str):
        super().__init__(detalle)
        self.estado = estado
        self.detalle = detalle

# Estas listas ayudan a reconocer encabezados habituales. No cambian los
# nombres reales que vienen en el archivo del cliente.
ALIAS_COLUMNAS = {
    "producto": ["producto", "artículo", "articulo", "nombre del producto"],
    "proveedor": ["proveedor", "nombre proveedor", "nombre del proveedor"],
    "cantidad": [
        "cantidad",
        "cantidad vendida",
        "unidades vendidas",
        "número de unidades",
        "numero de unidades",
    ],
    "importe": [
        "importe venta",
        "importe total venta",
        "importe total de la venta",
        "total venta",
    ],
    "compra": [
        "precio compra unitario",
        "precio de compra",
        "precio compra",
        "precio",
        "costo unitario",
    ],
    "envio": [
        "costo envío pedido",
        "costo envio pedido",
        "costo de envío",
        "costo de envio",
    ],
    "venta": [
        "precio venta unitario",
        "precio de venta",
        "precio venta",
        "precio público",
        "precio publico",
    ],
    "peso": ["peso kg", "peso", "gramaje", "peso del producto"],
    "stock": ["stock disponible", "stock", "existencias", "inventario", "inv"],
    "largo": ["largo cm", "largo", "longitud cm", "longitud"],
    "ancho": ["ancho cm", "ancho"],
    "alto": ["alto cm", "alto"],
}


def normalizar_encabezado(nombre: object) -> str:
    """Compara encabezados sin importar espacios, mayúsculas o acentos."""

    texto = unicodedata.normalize("NFKD", str(nombre).strip().casefold())
    sin_acentos = "".join(letra for letra in texto if not unicodedata.combining(letra))
    return "".join(letra for letra in sin_acentos if letra.isalnum())


def detectar_columnas(columnas: list[object]) -> dict[str, str | None]:
    """Relaciona cada concepto con un nombre real cuando la coincidencia es única."""

    detectadas: dict[str, str | None] = {}
    for concepto, alias in ALIAS_COLUMNAS.items():
        opciones = {normalizar_encabezado(nombre) for nombre in alias}
        coincidencias = [
            str(columna)
            for columna in columnas
            if normalizar_encabezado(columna) in opciones
        ]
        detectadas[concepto] = coincidencias[0] if len(coincidencias) == 1 else None
    return detectadas


def _texto_o_none(valor: str | None, columnas: list[object]) -> str | None:
    """Acepta una columna solamente cuando realmente existe en la tabla."""

    if not valor:
        return None
    return valor if valor in columnas else None


def _valor_json(valor: Any) -> Any:
    """Convierte valores de pandas y NumPy a tipos que entiende JSON."""

    if isinstance(valor, dict):
        return {str(clave): _valor_json(dato) for clave, dato in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_valor_json(dato) for dato in valor]
    if isinstance(valor, pd.Timestamp):
        return valor.isoformat()
    if hasattr(valor, "item"):
        try:
            return _valor_json(valor.item())
        except (TypeError, ValueError):
            pass
    if valor is pd.NA:
        return None
    if isinstance(valor, float) and (math.isnan(valor) or math.isinf(valor)):
        return None
    try:
        if pd.isna(valor):
            return None
    except (TypeError, ValueError):
        pass
    return valor


def _tabla_json(tabla: pd.DataFrame, limite: int | None = None) -> list[dict[str, Any]]:
    """Convierte una tabla en filas para mostrarla en el navegador."""

    if tabla is None or tabla.empty:
        return []
    visible = tabla.head(limite) if limite else tabla
    filas = visible.to_dict(orient="records")
    return [_valor_json(fila) for fila in filas]


def _cargar_subidos(
    archivos: list[tuple[str, bytes]],
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Lee varios archivos subidos y los entrega a las funciones educativas."""

    if not archivos:
        raise ErrorApi(400, "Selecciona al menos un archivo.")
    if len(archivos) > MAXIMO_ARCHIVOS:
        raise ErrorApi(400, f"Puedes analizar hasta {MAXIMO_ARCHIVOS} archivos a la vez.")

    buffers: list[BytesIO] = []
    total = 0
    for nombre_recibido, contenido in archivos:
        nombre = Path(nombre_recibido or "").name
        if Path(nombre).suffix.lower() not in EXTENSIONES_PERMITIDAS:
            raise ErrorApi(400, f"{nombre or 'El archivo'} no es CSV, XLSX o XLS.")
        total += len(contenido)
        if total > MAXIMO_TOTAL_BYTES:
            raise ErrorApi(
                413,
                "Los archivos juntos deben pesar menos de 4 MB para esta versión web.",
            )
        memoria = BytesIO(contenido)
        memoria.name = nombre
        buffers.append(memoria)

    try:
        # Leemos los archivos seleccionados sin escribirlos en el servidor
        return cargar_varios_archivos(buffers)
    except (ValueError, TypeError, OSError, KeyError) as error:
        raise ErrorApi(400, str(error)) from error


def _preparar_limpieza(
    datos: pd.DataFrame,
    columnas: dict[str, str | None],
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Limpia texto, números y duplicados usando las columnas seleccionadas."""

    columnas_texto = list(
        dict.fromkeys(
            columna
            for columna in [columnas["producto"], columnas["proveedor"]]
            if columna is not None
        )
    )
    columnas_numericas = list(
        dict.fromkeys(
            columna
            for columna in [
                columnas["cantidad"],
                columnas["importe"],
                columnas["compra"],
                columnas["venta"],
                columnas["envio"],
                columnas["peso"],
                columnas["stock"],
                columnas["largo"],
                columnas["ancho"],
                columnas["alto"],
            ]
            if columna is not None
        )
    )
    return limpiar_datos(
        datos,
        columnas_texto=columnas_texto,
        columnas_numericas=columnas_numericas,
        estilo_texto="titulo",
        eliminar_duplicados=True,
    )


def _recomendacion_resumida(resultado: dict[str, Any]) -> dict[str, Any]:
    """Elige la mejor recomendación disponible y explica su alcance."""

    indicadores = resultado.get("indicadores", {})
    calidad = indicadores.get("Calidad de recomendación", {})
    monte_carlo = indicadores.get("Recomendación Monte Carlo")
    cotizacion = indicadores.get("Cotización económica")
    costo = indicadores.get("Menor costo real con envío")
    respaldo = indicadores.get("Proveedor de respaldo")

    if monte_carlo:
        resumen = {
            "proveedor": monte_carlo["proveedor"],
            "criterio": "Monte Carlo y menor costo económico esperado",
            "probabilidad": monte_carlo.get("probabilidad_economica"),
            "precio": monte_carlo.get("precio_promedio_simulado"),
        }
    elif cotizacion:
        resumen = {
            "proveedor": cotizacion["proveedor"],
            "criterio": "menor precio total de venta con envío e IVA",
            "precio": cotizacion.get("precio_total"),
        }
    elif costo:
        resumen = {
            "proveedor": costo["proveedor"],
            "criterio": "menor costo disponible de compra y logística",
            "precio": costo.get("costo_real"),
        }
    elif respaldo:
        resumen = {
            "proveedor": respaldo["proveedor"],
            "criterio": respaldo.get("criterio", "datos disponibles"),
            "precio": None,
        }
    else:
        resumen = {
            "proveedor": None,
            "criterio": "faltan columnas para identificar proveedores",
            "precio": None,
        }

    resumen["confianza"] = calidad.get("nivel", "No disponible")
    resumen["provisional"] = bool(calidad.get("provisional", True))
    resumen["faltantes"] = calidad.get("faltantes", [])
    return _valor_json(resumen)


def health() -> dict[str, str]:
    """Permite comprobar que la aplicación abrió correctamente."""

    return {"status": "ok"}


def inspeccionar_archivos(
    files: list[tuple[str, bytes]],
) -> dict[str, Any]:
    """Muestra columnas y una vista previa antes de ejecutar cálculos."""

    datos, resumen, avisos = _cargar_subidos(files)
    detectadas = detectar_columnas(list(datos.columns))
    seleccion = {
        concepto: _texto_o_none(nombre, list(datos.columns))
        for concepto, nombre in detectadas.items()
    }
    limpios, reporte = _preparar_limpieza(datos, seleccion)
    productos: list[Any] = []
    if seleccion["producto"]:
        productos = sorted(
            limpios[seleccion["producto"]].dropna().unique().tolist(), key=str
        )

    return {
        "rows": len(datos),
        "columns": [str(columna) for columna in datos.columns],
        "detected": seleccion,
        "products": _valor_json(productos),
        "preview": _tabla_json(limpios, 12),
        "column_details": _tabla_json(describir_columnas(limpios)),
        "file_summary": _tabla_json(resumen),
        "cleaning": _valor_json(reporte),
        "warnings": avisos,
    }


def ejecutar_analisis(
    files: list[tuple[str, bytes]],
    producto: str | None = None,
    columna_producto: str | None = None,
    columna_proveedor: str | None = None,
    columna_cantidad: str | None = None,
    columna_importe: str | None = None,
    columna_compra: str | None = None,
    columna_venta: str | None = None,
    columna_envio: str | None = None,
    columna_peso: str | None = None,
    columna_stock: str | None = None,
    columna_largo: str | None = None,
    columna_ancho: str | None = None,
    columna_alto: str | None = None,
    tipo_envio: str = "por_pedido",
    unidad_peso: str = "kg",
    unidad_dimensiones: str = "cm",
    numero_unidades: int = 1,
    peso_manual: float = 0.0,
    tarifa_estandar: float = 100.0,
    tarifa_ltl: float = 500.0,
    envio_cliente: float = 0.0,
    comision: float = 0.0,
    promocion: float = 0.0,
    margen: float = 0.0,
    iva: float = 16.0,
    costo_m3: float = 0.0,
    variacion_compra: float = 5.0,
    variacion_logistica: float = 10.0,
    iteraciones: int = 5000,
) -> dict[str, Any]:
    """Limpia datos, compara proveedores y genera archivos descargables."""

    if numero_unidades < 1:
        raise ErrorApi(400, "El número de unidades debe ser mayor que cero.")
    if not 100 <= iteraciones <= 50_000:
        raise ErrorApi(400, "Monte Carlo debe usar entre 100 y 50,000 simulaciones.")
    if min(
        peso_manual,
        tarifa_estandar,
        tarifa_ltl,
        envio_cliente,
        comision,
        promocion,
        margen,
        iva,
        costo_m3,
        variacion_compra,
        variacion_logistica,
    ) < 0:
        raise ErrorApi(400, "Los costos y porcentajes no pueden ser negativos.")
    if comision + promocion + margen >= 100:
        raise ErrorApi(400, "Comisión, promoción y margen deben sumar menos de 100%.")

    datos, resumen_archivos, avisos_union = _cargar_subidos(files)
    columnas_reales = list(datos.columns)
    automaticas = detectar_columnas(columnas_reales)
    recibidas = {
        "producto": columna_producto,
        "proveedor": columna_proveedor,
        "cantidad": columna_cantidad,
        "importe": columna_importe,
        "compra": columna_compra,
        "venta": columna_venta,
        "envio": columna_envio,
        "peso": columna_peso,
        "stock": columna_stock,
        "largo": columna_largo,
        "ancho": columna_ancho,
        "alto": columna_alto,
    }
    seleccion = {
        concepto: _texto_o_none(recibidas[concepto] or automaticas[concepto], columnas_reales)
        for concepto in ALIAS_COLUMNAS
    }

    limpios, reporte = _preparar_limpieza(datos, seleccion)
    productos: list[Any] = []
    if seleccion["producto"]:
        productos = sorted(
            limpios[seleccion["producto"]].dropna().unique().tolist(), key=str
        )
    if not producto and productos:
        producto = str(productos[0])
    if producto and productos:
        coincidencia = next(
            (valor for valor in productos if str(valor).casefold() == producto.casefold()),
            producto,
        )
        producto = coincidencia

    if seleccion["peso"] is None and producto and peso_manual > 0 and seleccion["producto"]:
        seleccion["peso"] = "Peso capturado en la web (kg)"
        limpios[seleccion["peso"]] = float("nan")
        limpios.loc[
            limpios[seleccion["producto"]] == producto, seleccion["peso"]
        ] = peso_manual
        unidad_peso = "kg"

    limpios, columna_tipo, avisos_peso = agregar_clasificacion_gramaje(
        limpios, seleccion["peso"], unidad_peso
    )
    limpios, columna_volumen, avisos_dimensiones = agregar_volumen_dimensiones(
        limpios,
        seleccion["largo"],
        seleccion["ancho"],
        seleccion["alto"],
        unidad_dimensiones,
    )

    resultado = analizar_datos(
        limpios,
        columna_producto=seleccion["producto"],
        columna_proveedor=seleccion["proveedor"],
        columna_cantidad=seleccion["cantidad"],
        columna_precio_compra=seleccion["compra"],
        columna_precio_venta=seleccion["venta"],
        columna_importe_venta=seleccion["importe"],
        columna_envio=seleccion["envio"],
        tipo_envio=tipo_envio,
        columna_tipo_logistico=columna_tipo,
        columna_stock=seleccion["stock"],
        columna_peso=seleccion["peso"],
        unidad_peso=unidad_peso,
        costo_estandar_por_kg=tarifa_estandar,
        costo_ltl_por_kg=tarifa_ltl,
        modo_costo_gramaje="fijo",
        columna_volumen=columna_volumen,
        costo_dimensiones_por_m3=costo_m3,
        numero_unidades=numero_unidades,
        envio_cobrado_cliente=envio_cliente,
        comision_plataforma_pct=comision,
        promocion_digital_pct=promocion,
        margen_ganancia_pct=margen,
        tasa_iva_pct=iva,
        variacion_compra_pct=variacion_compra,
        variacion_logistica_pct=variacion_logistica,
        iteraciones_monte_carlo=iteraciones,
        producto_para_comparar=producto,
    )
    resultado["avisos"] = list(
        dict.fromkeys(
            [*avisos_union, *avisos_peso, *avisos_dimensiones, *resultado["avisos"]]
        )
    )

    try:
        excel = exportar_resultados_excel(limpios, resultado)
        csv = exportar_resultados_csv(resultado)
    except (ValueError, TypeError, OSError) as error:
        raise ErrorApi(500, f"No se pudo exportar: {error}") from error

    return {
        "product": _valor_json(producto),
        "products": _valor_json(productos),
        "rows_clean": len(limpios),
        "columns": [str(columna) for columna in limpios.columns],
        "selected_columns": seleccion,
        "cleaning": _valor_json(reporte),
        "preview": _tabla_json(limpios, 12),
        "file_summary": _tabla_json(resumen_archivos),
        "recommendation": _recomendacion_resumida(resultado),
        "indicators": _valor_json(resultado["indicadores"]),
        "tables": {
            nombre: _tabla_json(tabla)
            for nombre, tabla in resultado["tablas"].items()
        },
        "conclusions": resultado["conclusiones"],
        "warnings": resultado["avisos"],
        "downloads": {
            "excel": base64.b64encode(excel).decode("ascii"),
            "csv": base64.b64encode(csv).decode("ascii"),
        },
    }


def _parsear_multipart(environ: dict[str, Any]) -> tuple[list[tuple[str, bytes]], dict[str, str]]:
    """Separa los archivos y campos enviados por el formulario del navegador."""

    tipo = environ.get("CONTENT_TYPE", "")
    if "multipart/form-data" not in tipo:
        raise ErrorApi(400, "El formulario debe enviarse como multipart/form-data.")
    try:
        longitud = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError as error:
        raise ErrorApi(400, "El tamaño de la solicitud no es válido.") from error
    if longitud <= 0:
        raise ErrorApi(400, "La solicitud está vacía.")
    if longitud > MAXIMO_TOTAL_BYTES + 750_000:
        raise ErrorApi(413, "Los archivos juntos deben pesar menos de 4 MB.")

    cuerpo = environ["wsgi.input"].read(longitud)
    encabezados = (
        f"Content-Type: {tipo}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8")
    )
    mensaje = BytesParser(policy=policy.default).parsebytes(encabezados + cuerpo)
    if not mensaje.is_multipart():
        raise ErrorApi(400, "No se pudieron separar los campos del formulario.")

    archivos: list[tuple[str, bytes]] = []
    campos: dict[str, str] = {}
    for parte in mensaje.iter_parts():
        nombre_campo = parte.get_param("name", header="content-disposition")
        if not nombre_campo:
            continue
        contenido = parte.get_payload(decode=True) or b""
        nombre_archivo = parte.get_filename()
        if nombre_archivo:
            archivos.append((Path(nombre_archivo).name, contenido))
        else:
            codificacion = parte.get_content_charset() or "utf-8"
            campos[nombre_campo] = contenido.decode(codificacion, errors="replace")
    return archivos, campos


def _decimal(campos: dict[str, str], nombre: str, predeterminado: float) -> float:
    """Convierte un campo del formulario a número decimal."""

    texto = campos.get(nombre, "").strip()
    if not texto:
        return predeterminado
    try:
        return float(texto)
    except ValueError as error:
        raise ErrorApi(400, f"El campo {nombre} debe ser numérico.") from error


def _entero(campos: dict[str, str], nombre: str, predeterminado: int) -> int:
    """Convierte un campo del formulario a número entero."""

    texto = campos.get(nombre, "").strip()
    if not texto:
        return predeterminado
    try:
        return int(texto)
    except ValueError as error:
        raise ErrorApi(400, f"El campo {nombre} debe ser un número entero.") from error


def _analizar_formulario(
    archivos: list[tuple[str, bytes]], campos: dict[str, str]
) -> dict[str, Any]:
    """Pasa los campos del navegador a la función principal de análisis."""

    return ejecutar_analisis(
        archivos,
        producto=campos.get("producto") or None,
        columna_producto=campos.get("columna_producto") or None,
        columna_proveedor=campos.get("columna_proveedor") or None,
        columna_cantidad=campos.get("columna_cantidad") or None,
        columna_importe=campos.get("columna_importe") or None,
        columna_compra=campos.get("columna_compra") or None,
        columna_venta=campos.get("columna_venta") or None,
        columna_envio=campos.get("columna_envio") or None,
        columna_peso=campos.get("columna_peso") or None,
        columna_stock=campos.get("columna_stock") or None,
        columna_largo=campos.get("columna_largo") or None,
        columna_ancho=campos.get("columna_ancho") or None,
        columna_alto=campos.get("columna_alto") or None,
        tipo_envio=campos.get("tipo_envio") or "por_pedido",
        unidad_peso=campos.get("unidad_peso") or "kg",
        unidad_dimensiones=campos.get("unidad_dimensiones") or "cm",
        numero_unidades=_entero(campos, "numero_unidades", 1),
        peso_manual=_decimal(campos, "peso_manual", 0.0),
        tarifa_estandar=_decimal(campos, "tarifa_estandar", 100.0),
        tarifa_ltl=_decimal(campos, "tarifa_ltl", 500.0),
        envio_cliente=_decimal(campos, "envio_cliente", 0.0),
        comision=_decimal(campos, "comision", 0.0),
        promocion=_decimal(campos, "promocion", 0.0),
        margen=_decimal(campos, "margen", 0.0),
        iva=_decimal(campos, "iva", 16.0),
        costo_m3=_decimal(campos, "costo_m3", 0.0),
        variacion_compra=_decimal(campos, "variacion_compra", 5.0),
        variacion_logistica=_decimal(campos, "variacion_logistica", 10.0),
        iteraciones=_entero(campos, "iteraciones", 5000),
    )


def _json_bytes(datos: Any) -> bytes:
    """Codifica una respuesta JSON conservando acentos."""

    return json.dumps(datos, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


class AplicacionWSGI:
    """Aplicación HTTP pequeña compatible con Vercel y con Python estándar."""

    estados = {
        200: "200 OK",
        400: "400 Bad Request",
        404: "404 Not Found",
        413: "413 Content Too Large",
        500: "500 Internal Server Error",
    }

    archivos_publicos = {
        "/": ("index.html", "text/html; charset=utf-8"),
        "/styles.css": ("styles.css", "text/css; charset=utf-8"),
        "/app.js": ("app.js", "application/javascript; charset=utf-8"),
        "/datos_demostracion.csv": (
            "datos_demostracion.csv",
            "text/csv; charset=utf-8",
        ),
    }

    def _responder(
        self,
        start_response,
        estado: int,
        cuerpo: bytes,
        tipo: str,
        encabezados_extra: list[tuple[str, str]] | None = None,
    ):
        encabezados = [
            ("Content-Type", tipo),
            ("Content-Length", str(len(cuerpo))),
            ("X-Content-Type-Options", "nosniff"),
        ]
        encabezados.extend(encabezados_extra or [])
        start_response(self.estados[estado], encabezados)
        return [cuerpo]

    def __call__(self, environ, start_response):
        metodo = environ.get("REQUEST_METHOD", "GET").upper()
        ruta = environ.get("PATH_INFO", "/") or "/"
        try:
            if metodo == "GET" and ruta in self.archivos_publicos:
                nombre, tipo = self.archivos_publicos[ruta]
                contenido = (CARPETA_PROYECTO / nombre).read_bytes()
                extras = []
                if ruta == "/datos_demostracion.csv":
                    extras.append(
                        ("Content-Disposition", 'inline; filename="datos_demostracion.csv"')
                    )
                return self._responder(start_response, 200, contenido, tipo, extras)

            if metodo == "GET" and ruta == "/api/health":
                return self._responder(
                    start_response,
                    200,
                    _json_bytes(health()),
                    "application/json; charset=utf-8",
                )

            if metodo == "POST" and ruta in {"/api/inspect", "/api/analyze"}:
                archivos, campos = _parsear_multipart(environ)
                resultado = (
                    inspeccionar_archivos(archivos)
                    if ruta == "/api/inspect"
                    else _analizar_formulario(archivos, campos)
                )
                return self._responder(
                    start_response,
                    200,
                    _json_bytes(resultado),
                    "application/json; charset=utf-8",
                )

            return self._responder(
                start_response,
                404,
                _json_bytes({"detail": "Ruta no encontrada."}),
                "application/json; charset=utf-8",
            )
        except ErrorApi as error:
            return self._responder(
                start_response,
                error.estado,
                _json_bytes({"detail": error.detalle}),
                "application/json; charset=utf-8",
            )
        except Exception:
            return self._responder(
                start_response,
                500,
                _json_bytes({"detail": "Ocurrió un error interno durante el análisis."}),
                "application/json; charset=utf-8",
            )


# Vercel busca una variable llamada ``app`` que implemente WSGI.
app = AplicacionWSGI()


if __name__ == "__main__":
    # Servidor incluido en Python para probar la versión web localmente.
    with make_server("127.0.0.1", 8000, app) as servidor:
        print("Proveedor Claro disponible en http://127.0.0.1:8000")
        servidor.serve_forever()
