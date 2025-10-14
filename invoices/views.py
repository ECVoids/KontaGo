from django.shortcuts import render, redirect
from django.db import transaction
from django.db.models import Max
from django.contrib import messages
import json

from .forms import FacturaForm
from inventory.models import Product
from .models import Factura, DetalleFactura


def generar_codigo_factura():
    ultimo_id = Factura.objects.aggregate(max_id=Max("id"))["max_id"] or 0
    return f"F{ultimo_id + 1:04d}"  # F0001, F0002, ...

def sales_list(request):
    facturas = Factura.objects.prefetch_related("detalles__producto").all().order_by("-fecha")
    return render(request, "sales_list.html", {"facturas": facturas})

@transaction.atomic
def register_invoice(request):
    """
    Vista que reemplaza el flujo basado en formset.
    Usa un carrito en JS que se envía como JSON en 'cart_data'.
    """
    products = Product.objects.all()

    if request.method == "POST":
        factura_form = FacturaForm(request.POST)
        cart_json = request.POST.get("cart_data", "[]")
        try:
            cart = json.loads(cart_json)
        except Exception:
            cart = []

        # Validación rápida del carrito
        if not cart:
            messages.error(request, "Debes agregar al menos un producto al carrito.")
            return render(request, "register_invoice.html", {"factura_form": factura_form, "products": products})

        if factura_form.is_valid():
            # crear factura (sin total de momento)
            factura = factura_form.save(commit=False)
            factura.codigo = generar_codigo_factura()
            factura.total = 0
            factura.save()

            total = 0

            # Procesar cada item del carrito
            for item in cart:
                try:
                    product_id = int(item.get("product_id"))
                    cantidad = int(item.get("quantity"))
                except Exception:
                    transaction.set_rollback(True)
                    factura.delete()
                    messages.error(request, "Formato de producto incorrecto en el carrito.")
                    return render(request, "register_invoice.html", {"factura_form": factura_form, "products": products})

                # bloqueo de fila para evitar race-conditions en stock
                producto = Product.objects.select_for_update().get(pk=product_id)

                if cantidad <= 0:
                    transaction.set_rollback(True)
                    factura.delete()
                    messages.error(request, f"La cantidad para {producto.name} debe ser mayor que 0.")
                    return render(request, "register_invoice.html", {"factura_form": factura_form, "products": products})

                if cantidad > producto.quantity:
                    transaction.set_rollback(True)
                    factura.delete()
                    messages.error(request, f"Stock insuficiente para {producto.name}. Disponible: {producto.quantity}")
                    return render(request, "register_invoice.html", {"factura_form": factura_form, "products": products})

                precio_unitario = producto.price
                subtotal = precio_unitario * cantidad

                # crear detalle
                DetalleFactura.objects.create(
                    factura=factura,
                    producto=producto,
                    cantidad=cantidad,
                    precio_unitario=precio_unitario,
                    subtotal=subtotal
                )

                # descontar stock
                producto.quantity -= cantidad
                producto.save()

                total += subtotal

            factura.total = total
            factura.save()

            messages.success(request, f"✅ Factura {factura.codigo} registrada correctamente. Total: ${factura.total}.")
            return redirect("sales_list")
        else:
            # formulario inválido
            messages.error(request, "Revisa los datos de la factura.")
            return render(request, "register_invoice.html", {"factura_form": factura_form, "products": products})

    # GET
    factura_form = FacturaForm()
    return render(request, "register_invoice.html", {"factura_form": factura_form, "products": products})