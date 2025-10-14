from django.shortcuts import render
from inventory.models import Product
from invoices.models import Venta, DetalleFactura

import matplotlib.pyplot as plt
import matplotlib
import io
import urllib, base64
import os
from openai import OpenAI
from dotenv import load_dotenv
import markdown
from django.db.models import Sum
from datetime import datetime, timedelta
from django.db.models import Max


matplotlib.use('Agg')
_ = load_dotenv('openAI.env')
client = OpenAI(api_key=os.environ.get('openAI_api_key'))

def graphics(request):
    """Genera gráficas de analítica de ventas basadas en las facturas."""
    
    # --- Recolección de datos de ventas ---
    detalles = DetalleFactura.objects.select_related('producto').all()
    
    ventas_por_producto = {}
    facturacion_por_producto = {}

    for detalle in detalles:
        nombre = detalle.producto.name
        ventas_por_producto[nombre] = ventas_por_producto.get(nombre, 0) + detalle.cantidad
        facturacion_por_producto[nombre] = facturacion_por_producto.get(nombre, 0) + float(detalle.subtotal)

    if not ventas_por_producto:
        return render(request, 'graphics.html', {
            'graphic': None,
            'graphic2': None,
            'message': "No hay datos de ventas para mostrar."
        })

    # --- Gráfico 1: Cantidades vendidas ---
    plt.figure(figsize=(8, 5))
    posiciones = range(len(ventas_por_producto))
    plt.bar(posiciones, ventas_por_producto.values(), width=0.5, color="#a97155")
    plt.title('Cantidad vendida por producto')
    plt.xlabel('Producto')
    plt.ylabel('Unidades vendidas')
    plt.xticks(posiciones, ventas_por_producto.keys(), rotation=90)
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()
    graphic = base64.b64encode(buffer.getvalue()).decode('utf-8')

    # --- Gráfico 2: Facturación total ---
    plt.figure(figsize=(8, 5))
    posiciones = range(len(facturacion_por_producto))
    plt.bar(posiciones, facturacion_por_producto.values(), width=0.5, color="#6d4c41")
    plt.title('Facturación total por producto')
    plt.xlabel('Producto')
    plt.ylabel('Total facturado ($)')
    plt.xticks(posiciones, facturacion_por_producto.keys(), rotation=90)
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()
    graphic2 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    return render(request, 'graphics.html', {
        'graphic': graphic,
        'graphic2': graphic2,
        'message': None
    })

def selling(request):
    """Genera sugerencias de venta usando OpenAI según el desempeño de los productos."""

    detalles = DetalleFactura.objects.select_related('producto').all()

    ventas_por_producto = {}
    facturacion_por_producto = {}

    for detalle in detalles:
        nombre = detalle.producto.name
        ventas_por_producto[nombre] = ventas_por_producto.get(nombre, 0) + detalle.cantidad
        facturacion_por_producto[nombre] = facturacion_por_producto.get(nombre, 0) + float(detalle.subtotal)

    if not ventas_por_producto:
        return render(request, 'selling.html', {
            'suggestions': "<p>No hay datos suficientes para generar sugerencias.</p>"
        })

    # Determinar productos clave
    mas_vendido = max(ventas_por_producto, key=ventas_por_producto.get)
    menos_vendido = min(ventas_por_producto, key=ventas_por_producto.get)

    prompt = f"""
    Eres un asistente experto en análisis de ventas de productos alimenticios.
    A partir de los siguientes datos de ventas, genera sugerencias de venta y marketing para mejorar el rendimiento:

    Producto más vendido: {mas_vendido} (unidades vendidas: {ventas_por_producto[mas_vendido]})
    Producto menos vendido: {menos_vendido} (unidades vendidas: {ventas_por_producto[menos_vendido]})

    Ventas totales por producto:
    {ventas_por_producto}

    Facturación total por producto:
    {facturacion_por_producto}

    Objetivo:
    - Incrementar ventas de los productos de bajo rendimiento.
    - Reducir acumulación de stock lento.
    - Mejorar la estrategia de precios o promociones.

    Devuelve un texto en formato claro y estructurado (usa títulos y listas) con estrategias concretas.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=900,
    )

    suggestions_md = response.choices[0].message.content
    suggestions_html = markdown.markdown(suggestions_md)

    return render(request, 'selling.html', {'suggestions': suggestions_html})

def restock_recommendations(request):
    """FR-15: Recomendaciones de reabastecimiento con IA (usa Venta + DetalleFactura)"""
    hoy = datetime.now()
    hace_30_dias = hoy - timedelta(days=30)

    productos_info = []

    for p in Product.objects.all():
        # ventas desde el modelo Venta (si lo usas)
        ventas_venta = Venta.objects.filter(
            product=p, fecha__gte=hace_30_dias
        ).aggregate(total=Sum('cantidad'))['total'] or 0

        # ventas desde DetalleFactura (filtradas por la fecha de la factura)
        ventas_detalle = DetalleFactura.objects.filter(
            producto=p, factura__fecha__gte=hace_30_dias
        ).aggregate(total=Sum('cantidad'))['total'] or 0

        ventas_mes = int(ventas_venta or 0) + int(ventas_detalle or 0)

        # última fecha de venta: max entre Venta.fecha y DetalleFactura.factura.fecha
        ultima_venta_venta = Venta.objects.filter(product=p).aggregate(fecha=Max('fecha'))['fecha']
        ultima_venta_detalle = DetalleFactura.objects.filter(producto=p).aggregate(fecha=Max('factura__fecha'))['fecha']

        ultima_venta = None
        if ultima_venta_venta and ultima_venta_detalle:
            ultima_venta = max(ultima_venta_venta, ultima_venta_detalle)
        else:
            ultima_venta = ultima_venta_venta or ultima_venta_detalle

        productos_info.append({
            "nombre": p.name,
            "categoria": p.category,
            "stock": p.quantity,
            "ventas_ult_30d": ventas_mes,
            "ultima_venta": ultima_venta.isoformat() if ultima_venta else "Nunca",
            "precio": float(p.price),
        })

    # Prompt claro en español (similar al de selling)
    prompt = f"""
Eres un asistente experto en gestión de inventario para comercios.

A continuación tienes una lista de productos con su stock actual, ventas de los últimos 30 días y la última fecha de venta.
Para cada producto, responde en español y genera:
- Recomendación: "Reabastecer" o "No reabastecer".
- Cantidad sugerida a comprar (número entero).
- Plazo recomendado para realizar el pedido (en días).
- Breve justificación basada en las ventas y el stock actual.

Formato solicitado (por producto):
Producto: <nombre>
Recomendación: <Reabastecer / No reabastecer>
Cantidad sugerida: <número>
Plazo (días): <número>
Justificación: <texto corto>

Productos:
{productos_info}

Devuelve la respuesta en texto claro, con una sección por producto.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Eres un asistente de inventario inteligente."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=700,
    )

    recomendaciones_md = response.choices[0].message.content.strip()
    # convertimos markdown (si lo devuelve) a HTML para mostrarlo con seguridad
    recomendaciones_html = markdown.markdown(recomendaciones_md)

    return render(request, 'restock_recommendations.html', {
        'recomendaciones': recomendaciones_html
    })


def slow_inventory_alerts(request):
    """FR-17: Alertas de inventario lento u obsoleto con IA (usa Venta + DetalleFactura)"""
    hoy = datetime.now()
    hace_60_dias = hoy - timedelta(days=60)

    productos_info = []

    for p in Product.objects.all():
        ventas_venta = Venta.objects.filter(
            product=p, fecha__gte=hace_60_dias
        ).aggregate(total=Sum('cantidad'))['total'] or 0

        ventas_detalle = DetalleFactura.objects.filter(
            producto=p, factura__fecha__gte=hace_60_dias
        ).aggregate(total=Sum('cantidad'))['total'] or 0

        ventas_60d = int(ventas_venta or 0) + int(ventas_detalle or 0)

        ultima_venta_venta = Venta.objects.filter(product=p).aggregate(fecha=Max('fecha'))['fecha']
        ultima_venta_detalle = DetalleFactura.objects.filter(producto=p).aggregate(fecha=Max('factura__fecha'))['fecha']

        ultima_venta = None
        if ultima_venta_venta and ultima_venta_detalle:
            ultima_venta = max(ultima_venta_venta, ultima_venta_detalle)
        else:
            ultima_venta = ultima_venta_venta or ultima_venta_detalle

        productos_info.append({
            "nombre": p.name,
            "categoria": p.category,
            "stock": p.quantity,
            "ventas_ult_60d": ventas_60d,
            "ultima_venta": ultima_venta.isoformat() if ultima_venta else "Nunca",
        })

    prompt = f"""
Eres un analista de inventario experto.

Tienes información de productos, su stock, ventas en los últimos 60 días y la última venta.
Identifica qué productos parecen tener movimiento lento u obsolescencia.

Para cada producto que esté lento u obsoleto, devuelve:
- Producto: <nombre>
- Estado: <Movimiento lento / Obsoleto>
- Motivo: <breve justificación (por ejemplo: sin ventas en X días, stock muy alto respecto ventas)>
- Acción sugerida: <Mantener / Promoción / Remate / Retirar>

Productos:
{productos_info}

Devuélvelo en español con una lista clara por producto.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Eres un experto en análisis de inventario."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.25,
        max_tokens=800,
    )

    analisis_md = response.choices[0].message.content.strip()
    analisis_html = markdown.markdown(analisis_md)

    return render(request, 'slow_inventory_alerts.html', {
        'analisis': analisis_html
    })
