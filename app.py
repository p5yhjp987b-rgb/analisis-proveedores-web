"""Interfaz educativa para analizar ventas y proveedores con Streamlit."""

from pathlib import Path
import hashlib
import unicodedata

# Importamos Plotly para crear gráficas interactivas
import plotly.express as px
# Importamos Streamlit para construir la pantalla de la aplicación
import streamlit as st

from analisis import (
    agregar_clasificacion_gramaje,
    agregar_volumen_dimensiones,
    analizar_datos,
    buscar_archivos_datos,
    cargar_varios_archivos,
    describir_columnas,
    exportar_resultados_csv,
    exportar_resultados_excel,
    limpiar_datos,
)


CARPETA_PROYECTO = Path(__file__).parent
CARPETA_DATOS = CARPETA_PROYECTO / "datos"
NOMBRE_ARCHIVO_DEMO = "datos_demostracion.csv"
# Estas listas no cambian los encabezados del archivo. Solamente ayudan a
# reconocer nombres habituales escritos con mayúsculas, espacios o acentos.
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
    """Prepara un encabezado para compararlo sin cambiar el nombre original."""

    texto = unicodedata.normalize("NFKD", str(nombre).strip().casefold())
    sin_acentos = "".join(letra for letra in texto if not unicodedata.combining(letra))
    # Ignoramos espacios y signos; conservamos solamente letras y números.
    return "".join(letra for letra in sin_acentos if letra.isalnum())


def detectar_columnas_automaticamente(columnas: list[object]) -> dict[str, object | None]:
    """Relaciona conceptos con nombres reales solo cuando hay una coincidencia única."""

    detectadas: dict[str, object | None] = {}
    for concepto, alias in ALIAS_COLUMNAS.items():
        nombres_posibles = {normalizar_encabezado(nombre) for nombre in alias}
        coincidencias = [
            columna
            for columna in columnas
            if normalizar_encabezado(columna) in nombres_posibles
        ]
        # Si hay dos posibles columnas, no adivinamos cuál quiso usar la persona.
        detectadas[concepto] = coincidencias[0] if len(coincidencias) == 1 else None
    return detectadas


def firma_de_columnas(columnas: list[object]) -> str:
    """Crea una clave estable para reiniciar selectores al cambiar de archivo."""

    nombres = "\x1f".join(str(columna) for columna in columnas)
    return hashlib.sha1(nombres.encode("utf-8")).hexdigest()[:10]


def seleccionar_columna(
    etiqueta: str,
    columnas: list[object],
    clave: str,
    firma_columnas: str,
    valor_inicial: object | None = None,
) -> object | None:
    """Muestra los nombres reales y permite elegir uno o ninguno."""

    opciones = [None, *columnas]
    indice_inicial = opciones.index(valor_inicial) if valor_inicial in opciones else 0
    return st.selectbox(
        etiqueta,
        opciones,
        index=indice_inicial,
        format_func=lambda valor: "— No seleccionar —" if valor is None else str(valor),
        # La firma evita conservar una selección vacía de otro grupo de archivos.
        key=f"columna_{clave}_{firma_columnas}",
    )


def valores_unicos(datos, columna: object | None) -> list[object]:
    """Prepara una lista ordenada para los filtros."""

    if columna is None or columna not in datos.columns:
        return []
    return sorted(datos[columna].dropna().unique().tolist(), key=str)


def mostrar_indicadores(resultado: dict, filas: int) -> None:
    """Presenta los números principales en tarjetas."""

    indicadores = resultado["indicadores"]
    vendido = indicadores.get("Producto más vendido")
    ventas = indicadores.get("Ventas totales")
    bajo = indicadores.get("Precio promedio más bajo")
    utilidad = indicadores.get("Utilidad total")
    costo_real = indicadores.get("Menor costo real con envío")
    cotizacion = indicadores.get("Cotización económica")
    monte_carlo = indicadores.get("Recomendación Monte Carlo")

    tarjetas = st.columns(3)
    tarjetas[0].metric("Registros analizados", f"{filas:,}")
    tarjetas[1].metric(
        "Producto más vendido",
        str(vendido["producto"]) if vendido else "No disponible",
        f"{vendido['cantidad']:,.2f} unidades" if vendido else None,
    )
    tarjetas[2].metric(
        "Ventas totales",
        f"{ventas:,.2f}" if ventas is not None else "No disponible",
    )
    tarjetas_inferiores = st.columns(3)
    tarjetas_inferiores[0].metric(
        "Utilidad histórica (sin comisión/IVA)",
        f"{utilidad:,.2f}" if utilidad is not None else "No disponible",
    )
    tarjetas_inferiores[1].metric(
        "Menor costo real",
        str(costo_real["proveedor"]) if costo_real else "No disponible",
        f"{costo_real['costo_real']:,.2f} por unidad" if costo_real else None,
    )
    tarjetas_inferiores[2].metric(
        "Cotización más baja",
        str(cotizacion["proveedor"]) if cotizacion else "No disponible",
        f"{cotizacion['precio_total']:,.2f} con IVA" if cotizacion else None,
    )
    tarjetas_monte_carlo = st.columns(3)
    tarjetas_monte_carlo[0].metric(
        "Recomendación Monte Carlo",
        str(monte_carlo["proveedor"]) if monte_carlo else "No disponible",
        (
            f"Económico en {monte_carlo['probabilidad_economica']:.1f}% de escenarios"
            if monte_carlo
            else None
        ),
    )

    if bajo:
        st.caption(
            f"Menor precio promedio registrado: {bajo['proveedor']} "
            f"({bajo['precio']:,.2f}). Esto no significa automáticamente que sea el mejor proveedor."
        )


def mostrar_comparador_producto(
    resultado: dict,
    producto: object | None,
    proveedores_totales: int,
) -> None:
    """Resume la comparación de un producto entre todos sus proveedores."""

    st.subheader("9. Comparador de un producto entre proveedores")
    if producto is None:
        st.info("Selecciona un producto para comenzar la comparación.")
        return

    tablas = resultado["tablas"]
    indicadores = resultado["indicadores"]
    costos = tablas.get("costo_real_proveedores_producto")
    precios = tablas.get("comparacion_proveedores_producto")
    monte_carlo = tablas.get("monte_carlo_proveedores")
    menor_costo = indicadores.get("Menor costo real con envío")
    recomendacion = indicadores.get("Recomendación Monte Carlo")

    menor_precio = None
    if precios is not None and not precios.empty and "Precio promedio" in precios.columns:
        columna_nombre_proveedor = precios.columns[0]
        fila_menor_precio = precios.iloc[0]
        menor_precio = {
            "proveedor": fila_menor_precio[columna_nombre_proveedor],
            "precio": float(fila_menor_precio["Precio promedio"]),
        }

    if costos is not None and not costos.empty:
        proveedores_disponibles = len(costos)
    elif precios is not None and not precios.empty:
        proveedores_disponibles = len(precios)
    else:
        proveedores_disponibles = 0
    tarjetas = st.columns(3)
    tarjetas[0].metric("Producto buscado", str(producto))
    tarjetas[1].metric(
        "Proveedores con stock",
        f"{proveedores_disponibles} de {proveedores_totales}",
    )
    if menor_costo:
        tarjetas[2].metric(
            "Menor costo completo",
            str(menor_costo["proveedor"]),
            f"{menor_costo['costo_real']:,.2f} por unidad",
        )
    elif menor_precio:
        tarjetas[2].metric(
            "Menor precio disponible",
            str(menor_precio["proveedor"]),
            f"{menor_precio['precio']:,.2f}",
        )
    else:
        tarjetas[2].metric("Alternativa económica", "No disponible")

    if proveedores_disponibles < proveedores_totales:
        st.warning(
            "La comparación excluyó proveedores sin stock o sin datos suficientes. "
            "Por eso puede mostrar menos de tres alternativas."
        )

    if costos is not None and not costos.empty:
        st.markdown("**Costo completo por proveedor**")
        st.dataframe(costos, width="stretch", hide_index=True)
    elif precios is not None and not precios.empty:
        st.markdown("**Precios disponibles por proveedor**")
        st.dataframe(precios, width="stretch", hide_index=True)
    else:
        st.info("No hay proveedores disponibles para comparar este producto.")

    if monte_carlo is not None and not monte_carlo.empty:
        st.markdown("**Resultado de Monte Carlo**")
        st.dataframe(monte_carlo, width="stretch", hide_index=True)

    if menor_costo and recomendacion:
        if menor_costo["proveedor"] == recomendacion["proveedor"]:
            st.success(
                f"Según el costo completo y la simulación, {recomendacion['proveedor']} "
                f"es la alternativa económica para {producto}. Fue la opción más barata en "
                f"{recomendacion['probabilidad_economica']:.1f}% de los escenarios Monte Carlo."
            )
        else:
            st.info(
                f"El menor costo actual corresponde a {menor_costo['proveedor']}, pero "
                f"Monte Carlo favorece a {recomendacion['proveedor']} en "
                f"{recomendacion['probabilidad_economica']:.1f}% de los escenarios. "
                "La diferencia indica que la decisión cambia bajo incertidumbre."
            )
    elif menor_costo:
        st.success(
            f"Con los datos disponibles, {menor_costo['proveedor']} presenta el menor "
            f"costo completo para {producto}."
        )
    elif menor_precio:
        st.success(
            f"Con las columnas actuales, {menor_precio['proveedor']} presenta el menor "
            f"precio disponible para {producto}: {menor_precio['precio']:,.2f}."
        )
        st.info(
            "Esta recomendación usa solamente precio y stock. Para comparar el costo "
            "completo y ejecutar Monte Carlo agrega envío y, si aplica, peso y dimensiones."
        )

    st.caption(
        "La recomendación es económica: considera compra, envío, gramaje, dimensiones y stock. "
        "Antes de elegir también revisa calidad, tiempos de entrega, garantías y condiciones de pago."
    )


def mostrar_tablas(tablas: dict) -> None:
    """Muestra únicamente las tablas que sí pudieron calcularse."""

    nombres = {
        "cantidad_por_producto": "Cantidad vendida por producto",
        "ventas_por_producto": "Ventas totales por producto",
        "ventas_por_proveedor": "Ventas totales por proveedor",
        "precio_promedio_por_proveedor": "Precio promedio por proveedor",
        "comparacion_proveedores_producto": "Comparación de proveedores para el producto",
        "costo_real_proveedores_producto": "Costo real por proveedor: compra, envío, gramaje y dimensiones",
        "cotizacion_proveedores": "Cotización por proveedor con comisión, margen e IVA",
        "monte_carlo_proveedores": "Simulación Monte Carlo por proveedor",
        "registros_por_tipo_logistico": "Registros por tipo logístico",
        "utilidad_por_producto": "Utilidad por producto",
        "utilidad_por_proveedor": "Utilidad por proveedor",
    }
    for clave, tabla in tablas.items():
        if not tabla.empty:
            with st.expander(nombres.get(clave, clave.replace("_", " ").title()), expanded=True):
                st.dataframe(tabla, width="stretch", hide_index=True)


def grafica_barras(tabla, titulo: str, color: str) -> None:
    """Crea una gráfica de barras usando las primeras dos columnas."""

    if tabla.empty or len(tabla.columns) < 2:
        return
    categoria, valor = tabla.columns[:2]
    figura = px.bar(
        tabla,
        x=categoria,
        y=valor,
        title=titulo,
        text_auto=".3s",
        color_discrete_sequence=[color],
    )
    figura.update_layout(xaxis_title=str(categoria), yaxis_title=str(valor))
    st.plotly_chart(figura, width="stretch")


def mostrar_graficas(tablas: dict) -> None:
    """Elige gráficas sencillas según los análisis disponibles."""

    configuraciones = [
        ("cantidad_por_producto", "Cantidad vendida por producto", "#2563EB"),
        ("ventas_por_producto", "Ventas totales por producto", "#059669"),
        ("ventas_por_proveedor", "Ventas totales por proveedor", "#7C3AED"),
        ("precio_promedio_por_proveedor", "Precio promedio por proveedor", "#EA580C"),
        (
            "comparacion_proveedores_producto",
            "Comparación de precios para el producto elegido",
            "#0891B2",
        ),
        (
            "costo_real_proveedores_producto",
            "Costo real por proveedor: compra, envío, gramaje y dimensiones",
            "#DC2626",
        ),
        (
            "cotizacion_proveedores",
            "Precio total al cliente por proveedor, con IVA",
            "#0F766E",
        ),
        (
            "monte_carlo_proveedores",
            "Probabilidad de ser el proveedor más económico",
            "#9333EA",
        ),
        ("utilidad_por_producto", "Utilidad por producto", "#16A34A"),
    ]
    for clave, titulo, color in configuraciones:
        tabla = tablas.get(clave)
        if tabla is not None and not tabla.empty:
            grafica_barras(tabla, titulo, color)


def aplicar_estilo_visual() -> None:
    """Agrega espacio y jerarquía visual sin depender de una librería adicional."""

    st.markdown(
        """
        <style>
        .block-container {max-width: 1180px; padding-top: 2rem; padding-bottom: 4rem;}
        .hero-proveedores {
            padding: 1.5rem 1.7rem;
            border: 1px solid rgba(56, 189, 248, .30);
            border-radius: 18px;
            background: linear-gradient(135deg, rgba(14, 165, 233, .13), rgba(99, 102, 241, .08));
            margin-bottom: 1.2rem;
        }
        .hero-proveedores h1 {margin: 0 0 .35rem 0; font-size: 2rem;}
        .hero-proveedores p {margin: 0; opacity: .82; font-size: 1.02rem;}
        [data-testid="stMetric"] {
            border: 1px solid rgba(148, 163, 184, .22);
            background: rgba(148, 163, 184, .07);
            padding: .95rem 1rem;
            border-radius: 14px;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: .45rem;
            padding: .4rem;
            border-radius: 14px;
            background: rgba(148, 163, 184, .08);
        }
        .stTabs [data-baseweb="tab"] {height: 46px; border-radius: 10px; padding: 0 1rem;}
        .stTabs [aria-selected="true"] {background: rgba(14, 165, 233, .16);}
        div[data-testid="stVerticalBlockBorderWrapper"] {border-radius: 16px;}
        h2, h3 {scroll-margin-top: 5rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def mostrar_recomendacion_enfocada(
    resultado: dict,
    producto: object | None,
    columna_proveedor: object | None,
    columna_tipo_logistico: object | None,
    proveedores_totales: int,
) -> None:
    """Muestra primero la decisión y después solamente el detalle necesario."""

    st.subheader("3. Proveedor recomendado")
    if columna_proveedor is None:
        st.info("Selecciona la columna de proveedor para poder identificar una alternativa.")
        return

    tablas = resultado["tablas"]
    indicadores = resultado["indicadores"]
    costos = tablas.get("costo_real_proveedores_producto")
    cotizaciones = tablas.get("cotizacion_proveedores")
    monte_carlo = tablas.get("monte_carlo_proveedores")
    precios_producto = tablas.get("comparacion_proveedores_producto")
    recomendacion_mc = indicadores.get("Recomendación Monte Carlo")
    cotizacion_economica = indicadores.get("Cotización económica")
    menor_costo = indicadores.get("Menor costo real con envío")
    precio_bajo_global = indicadores.get("Precio promedio más bajo")
    proveedor_respaldo = indicadores.get("Proveedor de respaldo")
    calidad = indicadores.get("Calidad de recomendación", {})

    proveedor_recomendado = None
    if recomendacion_mc:
        proveedor_recomendado = recomendacion_mc["proveedor"]
    elif cotizacion_economica:
        proveedor_recomendado = cotizacion_economica["proveedor"]
    elif menor_costo:
        proveedor_recomendado = menor_costo["proveedor"]
    elif precios_producto is not None and not precios_producto.empty:
        proveedor_recomendado = precios_producto.iloc[0][columna_proveedor]
    elif precio_bajo_global:
        proveedor_recomendado = precio_bajo_global["proveedor"]
    elif proveedor_respaldo:
        proveedor_recomendado = proveedor_respaldo["proveedor"]

    if proveedor_recomendado is None:
        st.warning(
            "Todavía no se puede elegir un proveedor. Revisa que estén seleccionadas las "
            "columnas de producto, proveedor y precio de compra."
        )
        return

    if costos is not None and not costos.empty:
        proveedores_disponibles = len(costos)
    elif precios_producto is not None and not precios_producto.empty:
        proveedores_disponibles = len(precios_producto)
    else:
        tabla_precios_global = tablas.get("precio_promedio_por_proveedor")
        proveedores_disponibles = (
            len(tabla_precios_global)
            if tabla_precios_global is not None and not tabla_precios_global.empty
            else (1 if proveedor_respaldo else 0)
        )
    producto_mostrado = producto if producto is not None else "los datos disponibles"
    mensaje_recomendacion = (
        f"Para **{producto_mostrado}**, el proveedor seleccionado con la información "
        f"disponible es **{proveedor_recomendado}**."
    )
    if calidad.get("provisional", True):
        st.warning(mensaje_recomendacion)
        faltantes = calidad.get("faltantes", [])
        if faltantes:
            st.caption(
                "Recomendación provisional. Faltan: " + ", ".join(map(str, faltantes)) + "."
            )
    else:
        st.success(mensaje_recomendacion)

    fila_cotizacion = None
    if cotizaciones is not None and not cotizaciones.empty:
        coincidencia = cotizaciones[
            cotizaciones[columna_proveedor] == proveedor_recomendado
        ]
        if not coincidencia.empty:
            fila_cotizacion = coincidencia.iloc[0]

    tipo_logistico = "No disponible"
    if cotizacion_economica and cotizacion_economica.get("tipo_logistico"):
        tipo_logistico = cotizacion_economica["tipo_logistico"]
    elif menor_costo and menor_costo.get("tipo_logistico"):
        tipo_logistico = menor_costo["tipo_logistico"]
    tipo_corto = str(tipo_logistico)
    regla_tipo = None
    if "Estándar" in tipo_corto:
        tipo_corto = "Estándar"
        regla_tipo = "Peso igual o menor a 20 kg."
    elif "LTL" in tipo_corto:
        tipo_corto = "LTL"
        regla_tipo = "Peso mayor a 20 kg."
    tarjetas = st.columns(4)
    tarjetas[0].metric("Tipo de envío", tipo_corto)
    if regla_tipo:
        tarjetas[0].caption(regla_tipo)
    tarjetas[1].metric(
        "Envío que se suma",
        (
            f"${fila_cotizacion['Envío total sumado']:,.2f}"
            if fila_cotizacion is not None
            else "No disponible"
        ),
    )
    tarjetas[1].caption("Envío interno total + envío adicional.")
    tarjetas[2].metric(
        "Venta antes del envío",
        (
            f"${fila_cotizacion['Precio de venta con IVA']:,.2f}"
            if fila_cotizacion is not None
            else "No disponible"
        ),
    )
    tarjetas[2].caption("Producto con plataforma, promoción, margen e IVA.")
    tarjetas[3].metric(
        "Venta + envío",
        (
            f"${fila_cotizacion['Total venta + envío con IVA']:,.2f}"
            if fila_cotizacion is not None
            else "No disponible"
        ),
    )
    tarjetas[3].caption("Este total es la suma de los cuadros 2 y 3.")
    mensaje_disponibilidad = (
        f"Se compararon {proveedores_disponibles} de {proveedores_totales} proveedores."
    )
    if calidad.get("stock_verificado"):
        mensaje_disponibilidad += " Los proveedores con stock 0 quedan fuera."
    else:
        mensaje_disponibilidad += " El stock no pudo verificarse."
    st.caption(mensaje_disponibilidad)
    if recomendacion_mc:
        st.caption(
            f"Monte Carlo eligió esta alternativa en "
            f"{recomendacion_mc['probabilidad_economica']:.1f}% de los escenarios."
        )

    if cotizaciones is not None and not cotizaciones.empty:
        st.markdown("#### Comparativa: precio de venta según el envío")
        columnas_resumen = [columna_proveedor]
        for opcional in [
            columna_tipo_logistico,
            "Precio de compra promedio",
            "Envío total sumado",
            "Precio de venta con IVA",
            "Total venta + envío con IVA",
            "Precio por unidad con IVA",
            "Stock disponible",
        ]:
            if opcional in cotizaciones.columns:
                columnas_resumen.append(opcional)
        configuracion_columnas = {
            "Precio de compra promedio": st.column_config.NumberColumn(
                "Compra", format="$ %.2f"
            ),
            "Envío total sumado": st.column_config.NumberColumn(
                "Envío que se suma", format="$ %.2f"
            ),
            "Precio de venta con IVA": st.column_config.NumberColumn(
                "Venta antes del envío", format="$ %.2f"
            ),
            "Total venta + envío con IVA": st.column_config.NumberColumn(
                "Total final", format="$ %.2f"
            ),
            "Precio por unidad con IVA": st.column_config.NumberColumn(
                "Total final por unidad", format="$ %.2f"
            ),
        }
        if columna_tipo_logistico is not None:
            configuracion_columnas[columna_tipo_logistico] = st.column_config.TextColumn(
                "Tipo de envío"
            )
        st.dataframe(
            cotizaciones[columnas_resumen],
            width="stretch",
            hide_index=True,
            column_config=configuracion_columnas,
        )
        figura = px.bar(
            cotizaciones,
            x=columna_proveedor,
            y="Total venta + envío con IVA",
            text_auto=".3s",
            color=columna_proveedor,
            title="Total de venta más envío por proveedor",
        )
        figura.update_layout(
            showlegend=False,
            yaxis_title="Total final",
            xaxis_title="Proveedor",
        )
        st.plotly_chart(figura, width="stretch")
    else:
        tabla_provisional = precios_producto
        if tabla_provisional is None or tabla_provisional.empty:
            tabla_provisional = tablas.get("precio_promedio_por_proveedor")
        if tabla_provisional is not None and not tabla_provisional.empty:
            st.markdown("#### Comparativa provisional con los datos disponibles")
            st.dataframe(tabla_provisional, width="stretch", hide_index=True)
            st.caption(
                "Esta tabla permite seleccionar un proveedor por precio, aunque todavía "
                "no sea posible calcular el precio de venta completo."
            )

    if fila_cotizacion is not None:
        st.markdown("#### Cómo se forma el precio final")
        desglose_1, desglose_2, desglose_3 = st.columns(3)
        with desglose_1:
            st.metric("Compra del producto", f"${fila_cotizacion['Costo del producto total']:,.2f}")
            st.caption("Todavía no incluye el envío.")
        with desglose_2:
            cargos_digitales = (
                fila_cotizacion["Comisión de plataforma"]
                + fila_cotizacion["Promoción digital"]
            )
            st.metric("Plataforma + promoción", f"${cargos_digitales:,.2f}")
            st.caption("Lo que debe recuperar la venta por cargos digitales.")
        with desglose_3:
            st.metric("Ganancia objetivo", f"${fila_cotizacion['Ganancia objetivo']:,.2f}")
            st.caption("Margen configurado sobre el precio antes de IVA.")

        total_1, total_2, total_3 = st.columns(3)
        total_1.metric(
            "Precio de venta con IVA",
            f"${fila_cotizacion['Precio de venta con IVA']:,.2f}",
        )
        total_2.metric("Envío total que se suma", f"${fila_cotizacion['Envío total sumado']:,.2f}")
        total_3.metric(
            "Total que paga el cliente",
            f"${fila_cotizacion['Precio total cliente con IVA']:,.2f}",
        )

    if monte_carlo is not None and not monte_carlo.empty:
        with st.expander("Ver resultado de la simulación Monte Carlo", expanded=False):
            st.dataframe(monte_carlo, width="stretch", hide_index=True)
            st.caption(
                "Monte Carlo prueba muchos escenarios de cambio en compra y logística. "
                "No evalúa calidad, puntualidad, garantías ni condiciones de pago."
            )

    st.info(
        "La recomendación identifica la alternativa económica con stock. Antes de contratar, "
        "también revisa calidad, tiempo de entrega, devoluciones y condiciones de pago."
    )


def main() -> None:
    """Organiza la aplicación en tres pasos fáciles de seguir."""

    st.set_page_config(
        page_title="Análisis de ventas y proveedores",
        page_icon="📦",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    aplicar_estilo_visual()
    with st.container(border=True):
        st.title("📊 Análisis de ventas y proveedores")
        st.write(
            "Sube tus datos, configura los costos y descubre qué proveedor conviene "
            "para un producto."
        )

    with st.container(border=True):
        st.markdown("### Cargar archivos")
        archivos_subidos = st.file_uploader(
            "Sube uno o varios Excel/CSV",
            type=["xlsx", "xls", "csv"],
            accept_multiple_files=True,
            help="Puedes subir varios archivos o un Excel con una pestaña por proveedor.",
        )
        archivos_locales = buscar_archivos_datos(CARPETA_DATOS)
        archivos_locales_elegidos: list[Path] = []
        if archivos_locales:
            demos_excel = [
                ruta
                for ruta in archivos_locales
                if ruta.suffix.lower() == ".xlsx"
                and ruta.name.startswith("datos_demostracion_")
            ]
            demo_csv = [
                ruta for ruta in archivos_locales if ruta.name == NOMBRE_ARCHIVO_DEMO
            ]
            archivos_locales_elegidos = st.multiselect(
                "Archivos disponibles en la carpeta datos",
                archivos_locales,
                default=demos_excel or demo_csv,
                format_func=lambda ruta: ruta.name,
                help="Se usan solamente cuando no subes archivos desde tu computadora.",
            )

    # Si se subieron archivos, se analizan esos y no se mezclan con los ejemplos.
    archivos_elegidos = (
        list(archivos_subidos) if archivos_subidos else archivos_locales_elegidos
    )
    if not archivos_elegidos:
        st.info("Carga uno o varios archivos `.xlsx`, `.xls` o `.csv` para comenzar.")
        st.stop()

    try:
        # Leemos y unimos todos los archivos seleccionados.
        datos_originales, resumen_archivos, avisos_union = cargar_varios_archivos(
            archivos_elegidos
        )
    except Exception as error:
        st.error(f"No se pudieron leer los archivos: {error}")
        st.stop()

    nombres_mostrados = [
        archivo.name if hasattr(archivo, "name") else Path(archivo).name
        for archivo in archivos_elegidos
    ]
    es_demostracion = all(
        nombre == NOMBRE_ARCHIVO_DEMO or nombre.startswith("datos_demostracion_")
        for nombre in nombres_mostrados
    )
    if es_demostracion:
        st.info(
            "Estás usando datos ficticios de demostración. Puedes practicar y después "
            "subir tus propios Excel sin modificar los originales."
        )

    columnas = list(datos_originales.columns)
    valores_detectados = detectar_columnas_automaticamente(columnas)
    firma_columnas = firma_de_columnas(columnas)
    tab_datos, tab_costos, tab_resultado = st.tabs(
        ["1 · Datos", "2 · Costos y venta", "3 · Recomendación"]
    )

    with tab_datos:
        st.subheader("1. Revisar datos y columnas")
        resumen_1, resumen_2, resumen_3 = st.columns(3)
        resumen_1.metric("Archivos", len(archivos_elegidos))
        resumen_2.metric("Registros", f"{len(datos_originales):,}")
        resumen_3.metric("Columnas detectadas", len(columnas))
        st.caption("Archivos cargados: " + ", ".join(nombres_mostrados))

        nombres_conceptos = {
            "producto": "Producto",
            "proveedor": "Proveedor",
            "cantidad": "Cantidad",
            "importe": "Importe de venta",
            "compra": "Precio de compra",
            "envio": "Envío del archivo",
            "venta": "Precio de venta registrado",
            "peso": "Peso o gramaje",
            "stock": "Stock",
            "largo": "Largo",
            "ancho": "Ancho",
            "alto": "Alto",
        }
        tabla_deteccion = [
            {
                "Dato necesario": nombres_conceptos[concepto],
                "Columna encontrada": (
                    str(columna) if columna is not None else "No detectada"
                ),
            }
            for concepto, columna in valores_detectados.items()
        ]
        st.markdown("#### Columnas reconocidas automáticamente")
        st.dataframe(tabla_deteccion, width="stretch", hide_index=True)

        faltan_claves = any(
            valores_detectados.get(clave) is None
            for clave in ["producto", "proveedor", "compra"]
        )
        with st.expander(
            "Revisar o corregir la asignación de columnas",
            expanded=faltan_claves,
        ):
            st.caption(
                "El programa usa los nombres reales del archivo. Si algo no coincide, "
                "selecciona aquí la columna correcta."
            )
            grupo_1, grupo_2, grupo_3, grupo_4 = st.columns(4)
            with grupo_1:
                columna_producto = seleccionar_columna(
                    "Producto", columnas, "producto", firma_columnas,
                    valores_detectados.get("producto"),
                )
                columna_proveedor = seleccionar_columna(
                    "Proveedor", columnas, "proveedor", firma_columnas,
                    valores_detectados.get("proveedor"),
                )
            with grupo_2:
                columna_compra = seleccionar_columna(
                    "Precio de compra", columnas, "compra", firma_columnas,
                    valores_detectados.get("compra"),
                )
                columna_stock = seleccionar_columna(
                    "Stock disponible", columnas, "stock", firma_columnas,
                    valores_detectados.get("stock"),
                )
            with grupo_3:
                columna_peso = seleccionar_columna(
                    "Peso o gramaje", columnas, "peso", firma_columnas,
                    valores_detectados.get("peso"),
                )
                columna_envio = seleccionar_columna(
                    "Costo de envío del archivo", columnas, "envio", firma_columnas,
                    valores_detectados.get("envio"),
                )
            with grupo_4:
                columna_cantidad = seleccionar_columna(
                    "Cantidad", columnas, "cantidad", firma_columnas,
                    valores_detectados.get("cantidad"),
                )
                columna_venta = seleccionar_columna(
                    "Precio de venta registrado", columnas, "venta", firma_columnas,
                    valores_detectados.get("venta"),
                )
                columna_importe = seleccionar_columna(
                    "Importe total registrado", columnas, "importe", firma_columnas,
                    valores_detectados.get("importe"),
                )

            st.markdown("**Dimensiones opcionales**")
            dimension_1, dimension_2, dimension_3 = st.columns(3)
            with dimension_1:
                columna_largo = seleccionar_columna(
                    "Largo", columnas, "largo", firma_columnas,
                    valores_detectados.get("largo"),
                )
            with dimension_2:
                columna_ancho = seleccionar_columna(
                    "Ancho", columnas, "ancho", firma_columnas,
                    valores_detectados.get("ancho"),
                )
            with dimension_3:
                columna_alto = seleccionar_columna(
                    "Alto", columnas, "alto", firma_columnas,
                    valores_detectados.get("alto"),
                )

        tipo_envio = "por_unidad"
        unidad_peso = "kg"
        unidad_dimensiones = "cm"
        with st.expander("Unidades y formato del envío", expanded=False):
            if columna_envio is not None:
                envio_indica_pedido = "pedido" in normalizar_encabezado(columna_envio)
                tipo_envio_visible = st.radio(
                    "El envío del archivo está registrado",
                    ["Por unidad", "Por pedido completo"],
                    index=1 if es_demostracion or envio_indica_pedido else 0,
                    horizontal=True,
                )
                tipo_envio = (
                    "por_unidad" if tipo_envio_visible == "Por unidad" else "por_pedido"
                )
            if columna_peso is not None:
                unidad_peso_visible = st.radio(
                    "Unidad del peso", ["Kilogramos (kg)", "Gramos (g)"], horizontal=True
                )
                unidad_peso = "kg" if unidad_peso_visible == "Kilogramos (kg)" else "g"
            if any(
                columna is not None
                for columna in [columna_largo, columna_ancho, columna_alto]
            ):
                unidad_dimensiones_visible = st.radio(
                    "Unidad de las dimensiones",
                    ["Centímetros (cm)", "Milímetros (mm)", "Metros (m)"],
                    horizontal=True,
                )
                unidad_dimensiones = {
                    "Centímetros (cm)": "cm",
                    "Milímetros (mm)": "mm",
                    "Metros (m)": "m",
                }[unidad_dimensiones_visible]

        columnas_texto = list(
            dict.fromkeys(
                columna
                for columna in [columna_producto, columna_proveedor]
                if columna is not None
            )
        )
        columnas_numericas = list(
            dict.fromkeys(
                columna
                for columna in [
                    columna_cantidad,
                    columna_importe,
                    columna_compra,
                    columna_venta,
                    columna_envio,
                    columna_peso,
                    columna_stock,
                    columna_largo,
                    columna_ancho,
                    columna_alto,
                ]
                if columna is not None
            )
        )
        datos_limpios, reporte_limpieza = limpiar_datos(
            datos_originales,
            columnas_texto=columnas_texto,
            columnas_numericas=columnas_numericas,
            estilo_texto="titulo",
            eliminar_duplicados=True,
        )
        with st.expander("Vista previa y limpieza automática", expanded=False):
            limpieza_1, limpieza_2, limpieza_3 = st.columns(3)
            limpieza_1.metric("Filas limpias", reporte_limpieza["filas_finales"])
            limpieza_2.metric(
                "Duplicados eliminados", reporte_limpieza["duplicados_eliminados"]
            )
            limpieza_3.metric(
                "Celdas vacías", reporte_limpieza["celdas_vacias_despues"]
            )
            st.dataframe(datos_limpios.head(20), width="stretch", hide_index=True)
            st.markdown("**Detalle de columnas reales**")
            st.dataframe(describir_columnas(datos_limpios), width="stretch", hide_index=True)
            st.markdown("**Archivos unidos**")
            st.dataframe(resumen_archivos, width="stretch", hide_index=True)
            for aviso in avisos_union:
                st.warning(aviso)

    with tab_costos:
        st.subheader("2. Elegir producto y configurar el precio")
        st.caption(
            "Captura solamente los valores que apliquen. El archivo original nunca se modifica."
        )
        productos_para_comparar = valores_unicos(datos_limpios, columna_producto)
        producto_comparado = None
        if productos_para_comparar:
            producto_comparado = st.selectbox(
                "Producto que deseas comparar",
                productos_para_comparar,
                help="Escribe dentro de la lista para encontrarlo más rápido.",
            )
        else:
            st.warning("No se detectó una columna de producto.")

        pedido_1, pedido_2 = st.columns(2)
        with pedido_1:
            numero_unidades = st.number_input(
                "Número de unidades", min_value=1, value=1, step=1
            )
        peso_manual = 0.0
        with pedido_2:
            if columna_peso is None:
                peso_manual = st.number_input(
                    "Peso del producto seleccionado (kg)",
                    min_value=0.0,
                    value=0.0,
                    step=0.1,
                    help="Úsalo si tu Excel no incluye peso. Solo se usa en memoria.",
                )
            else:
                st.success(f"El peso se tomará de la columna: {columna_peso}")

        if columna_peso is None and producto_comparado is not None and peso_manual > 0:
            columna_peso = "Peso capturado en la aplicación (kg)"
            datos_limpios[columna_peso] = float("nan")
            datos_limpios.loc[
                datos_limpios[columna_producto] == producto_comparado, columna_peso
            ] = peso_manual
            unidad_peso = "kg"
        elif columna_peso is None:
            st.warning(
                "Sin peso no se puede decidir si el envío es Estándar ($100) o LTL ($500)."
            )

        st.markdown("#### Costos de envío")
        envio_1, envio_2, envio_3 = st.columns(3)
        with envio_1:
            tarifa_envio_estandar = st.number_input(
                "Tarifa fija Estándar (≤ 20 kg)",
                min_value=0.0,
                value=100.0,
                step=10.0,
            )
        with envio_2:
            tarifa_envio_ltl = st.number_input(
                "Tarifa fija LTL (> 20 kg)",
                min_value=0.0,
                value=500.0,
                step=10.0,
            )
        with envio_3:
            envio_cobrado_cliente = st.number_input(
                "Envío cobrado al cliente (antes de IVA)",
                min_value=0.0,
                value=0.0,
                step=10.0,
                help="Este importe se suma al precio de venta final.",
            )
        st.caption(
            "Estándar y LTL son costos internos. El envío al cliente se muestra separado "
            "y después se suma al total que pagará."
        )

        st.markdown("#### Precio de venta")
        precio_1, precio_2, precio_3, precio_4 = st.columns(4)
        with precio_1:
            comision_plataforma = st.number_input(
                "Comisión de plataforma (%)",
                min_value=0.0,
                max_value=99.0,
                value=0.0,
                step=0.5,
                help="Porcentaje que cobra la plataforma por vender.",
            )
        with precio_2:
            promocion_digital = st.number_input(
                "Promoción digital (%)",
                min_value=0.0,
                max_value=99.0,
                value=0.0,
                step=0.5,
                help="Publicidad, posicionamiento y otros cargos promocionales.",
            )
        with precio_3:
            margen_ganancia = st.number_input(
                "Margen de ganancia (%)",
                min_value=0.0,
                max_value=99.0,
                value=0.0,
                step=0.5,
            )
        with precio_4:
            tasa_iva = st.number_input(
                "IVA (%)", min_value=0.0, max_value=100.0, value=16.0, step=1.0
            )
        st.info(
            "Fórmula: compra + logística → precio que recupera comisión, promoción y margen "
            "→ IVA → precio de venta + envío al cliente."
        )
        st.caption(
            "El IVA inicia en 16% como tasa general en México. Confirma si tu producto "
            "tiene tasa 0%, está exento o necesita otro tratamiento fiscal."
        )

        costo_dimensiones_por_m3 = 0.0
        variacion_compra = 5.0
        variacion_logistica = 10.0
        iteraciones_monte_carlo = 5000
        with st.expander("Opciones avanzadas", expanded=False):
            costo_dimensiones_por_m3 = st.number_input(
                "Costo adicional por volumen ($ por m³)",
                min_value=0.0,
                value=100.0 if es_demostracion else 0.0,
                step=10.0,
            )
            avanzado_1, avanzado_2, avanzado_3 = st.columns(3)
            with avanzado_1:
                variacion_compra = st.number_input(
                    "Variación posible de compra (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=8.0 if es_demostracion else 5.0,
                    step=1.0,
                )
            with avanzado_2:
                variacion_logistica = st.number_input(
                    "Variación posible de logística (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=12.0 if es_demostracion else 10.0,
                    step=1.0,
                )
            with avanzado_3:
                iteraciones_monte_carlo = st.number_input(
                    "Simulaciones Monte Carlo",
                    min_value=100,
                    max_value=50000,
                    value=5000,
                    step=1000,
                )

    datos_limpios, columna_tipo_logistico, avisos_gramaje = agregar_clasificacion_gramaje(
        datos_limpios, columna_peso, unidad_peso
    )
    datos_limpios, columna_volumen, avisos_dimensiones = agregar_volumen_dimensiones(
        datos_limpios,
        columna_largo,
        columna_ancho,
        columna_alto,
        unidad_dimensiones,
    )

    parametros_analisis = {
        "columna_producto": columna_producto,
        "columna_proveedor": columna_proveedor,
        "columna_cantidad": columna_cantidad,
        "columna_precio_compra": columna_compra,
        "columna_precio_venta": columna_venta,
        "columna_importe_venta": columna_importe,
        "columna_envio": columna_envio,
        "tipo_envio": tipo_envio,
        "columna_tipo_logistico": columna_tipo_logistico,
        "columna_stock": columna_stock,
        "columna_peso": columna_peso,
        "unidad_peso": unidad_peso,
        "costo_estandar_por_kg": float(tarifa_envio_estandar),
        "costo_ltl_por_kg": float(tarifa_envio_ltl),
        "modo_costo_gramaje": "fijo",
        "columna_volumen": columna_volumen,
        "costo_dimensiones_por_m3": float(costo_dimensiones_por_m3),
        "numero_unidades": int(numero_unidades),
        "envio_cobrado_cliente": float(envio_cobrado_cliente),
        "comision_plataforma_pct": float(comision_plataforma),
        "promocion_digital_pct": float(promocion_digital),
        "margen_ganancia_pct": float(margen_ganancia),
        "tasa_iva_pct": float(tasa_iva),
        "variacion_compra_pct": float(variacion_compra),
        "variacion_logistica_pct": float(variacion_logistica),
        "iteraciones_monte_carlo": int(iteraciones_monte_carlo),
        "semilla_monte_carlo": 42,
        "producto_para_comparar": producto_comparado,
    }
    resultado = analizar_datos(datos_limpios, **parametros_analisis)

    with tab_resultado:
        mostrar_recomendacion_enfocada(
            resultado,
            producto_comparado,
            columna_proveedor,
            columna_tipo_logistico,
            len(valores_unicos(datos_limpios, columna_proveedor)),
        )
        avisos = [*avisos_gramaje, *avisos_dimensiones, *resultado["avisos"]]
        if avisos:
            with st.expander("Avisos sobre los datos usados", expanded=False):
                for aviso in dict.fromkeys(avisos):
                    st.warning(aviso)

        with st.expander("Conclusiones completas", expanded=False):
            for conclusion in resultado["conclusiones"]:
                st.write(f"- {conclusion}")

        st.markdown("#### Descargar el análisis")
        descarga_1, descarga_2 = st.columns(2)
        with descarga_1:
            st.download_button(
                "Descargar resultados en Excel",
                data=exportar_resultados_excel(datos_limpios, resultado),
                file_name="comparacion_proveedores.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
            )
        with descarga_2:
            st.download_button(
                "Descargar resultados en CSV",
                data=exportar_resultados_csv(resultado),
                file_name="comparacion_proveedores.csv",
                mime="text/csv",
                width="stretch",
            )


if __name__ == "__main__":
    main()
