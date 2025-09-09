from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
import os
from django.db import transaction
from django.db.models import Max
import json
from .forms import ProductEntryForm, ProductTakeoutForm, SupplierForm, FacturaForm, DetalleFacturaFormSet
from .models import Product, Supplier, Venta, Factura, DetalleFactura
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator




def home(request):
    return render(request, 'home.html')

def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    return redirect('inventory_display')

def add_unit(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.quantity += 1
    product.save()
    messages.success(request, f"✅ Se añadió una nueva unidad al producto {product.name}.")
    return redirect('inventory_display')

from django.db.models import Q

def inventory_display(request):
    # Parámetros GET
    q          = request.GET.get("q", "").strip()
    category   = request.GET.get("category", "").strip()
    supplier   = request.GET.get("supplier", "").strip()   # ← ahora será el NOMBRE del proveedor (texto)
    min_price  = request.GET.get("min_price", "").strip()
    max_price  = request.GET.get("max_price", "").strip()
    in_stock   = request.GET.get("in_stock", "").strip()   # "" | "yes" | "no"
    order_by   = request.GET.get("order_by", "name").strip()
    per_page   = int(request.GET.get("per_page", 24))
    page       = int(request.GET.get("page", 1))

    # SIN select_related, porque supplier no es FK
    qs = Product.objects.all()

    # Texto libre
    if q:
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(category__icontains=q) |
            Q(supplier__icontains=q)   # ← busca por texto en supplier
        )

    # Filtros específicos
    if category:
        qs = qs.filter(category=category)
    if supplier:
        qs = qs.filter(supplier__iexact=supplier)  # ← filtra por el texto exacto del proveedor
    if min_price:
        try: qs = qs.filter(price__gte=float(min_price))
        except ValueError: pass
    if max_price:
        try: qs = qs.filter(price__lte=float(max_price))
        except ValueError: pass
    if in_stock == "yes":
        qs = qs.filter(quantity__gt=0)
    elif in_stock == "no":
        qs = qs.filter(quantity__lte=0)

    # Orden: usar 'supplier' como texto (no supplier__name)
    allowed_order = {
        "name","-name","price","-price","quantity","-quantity",
        "supplier","-supplier","category","-category"
    }
    if order_by not in allowed_order:
        order_by = "name"
    qs = qs.order_by(order_by)

    # Paginación
    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(page)

    # Opciones para los <select>
    categories = (Product.objects
                  .order_by("category")
                  .values_list("category", flat=True).distinct())
    suppliers  = (Product.objects
                  .order_by("supplier")
                  .values_list("supplier", flat=True).distinct())  # ← nombres de proveedor (texto)

    context = {
        "products": page_obj.object_list,
        "page_obj": page_obj,
        "paginator": paginator,
        "filters": {
            "q": q, "category": category, "supplier": supplier,
            "min_price": min_price, "max_price": max_price,
            "in_stock": in_stock, "order_by": order_by, "per_page": per_page,
        },
        "categories": categories,
        "suppliers": suppliers,
    }
    return render(request, "inventory_display.html", context)


def product_entry(request):
    message = ""
    if request.method == 'POST':
        form = ProductEntryForm(request.POST, request.FILES)
        if form.is_valid():
            product = Product(
                name=form.cleaned_data['name'],
                category=form.cleaned_data['category'],
                description=form.cleaned_data['description'],
                price=form.cleaned_data['price'],
                supplier=form.cleaned_data['supplier'],
                quantity=form.cleaned_data['quantity'],
                image=form.cleaned_data['image']
            )

            # ✅ Categorías que requieren fecha de vencimiento
            categories_with_expiration = ['alimentos', 'cosmetica', 'limpieza']

            if form.cleaned_data['category'] in categories_with_expiration:
                product.expiration_date = form.cleaned_data['expiration_date']

            product.save()
            message = "✅ Product created successfully!"
            form = ProductEntryForm()  # reset form
    else:
        form = ProductEntryForm()
    return render(request, 'product_entry.html', {'form': form, 'message': message})


def supplier_list(request):
    suppliers = Supplier.objects.all()
    return render(request, 'supplier_list.html', {'suppliers': suppliers})

def supplier_entry(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save()  # ✅ ahora sí guarda también los productos
            messages.success(request, "✅ Supplier creado correctamente.")
            return redirect('supplier_list')
    else:
        form = SupplierForm()
    return render(request, 'supplier_entry.html', {'form': form})


def delete_supplier(request, supplier_id):
    supplier = get_object_or_404(Supplier, id=supplier_id)
    supplier.delete()
    messages.success(request, f"✅ Supplier {supplier.name} eliminado correctamente.")
    return redirect('supplier_list')

def product_takeout(request):
    message = ""
    if request.method == 'POST':
        form = ProductTakeoutForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            quantity = form.cleaned_data['quantity']
            try:
                product = Product.objects.get(name=name)
                if product.quantity >= quantity:
                    product.quantity -= quantity
                    product.save()
                    message = f"Takeout registered! {quantity} units removed from {name}."
                else:
                    message = f"Not enough units in stock. Available: {product.quantity}."
            except Product.DoesNotExist:
                message = "Product not found."
            form = ProductTakeoutForm()  # Reset form
    else:
        form = ProductTakeoutForm()
    return render(request, 'product_takeout.html', {'form': form, 'message': message})

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

def _filtered_products(request):
    q          = request.GET.get("q", "").strip()
    category   = request.GET.get("category", "").strip()
    supplier   = request.GET.get("supplier", "").strip()
    min_price  = request.GET.get("min_price", "").strip()
    max_price  = request.GET.get("max_price", "").strip()
    in_stock   = request.GET.get("in_stock", "").strip()  # "" | "yes" | "no"
    order_by   = request.GET.get("order_by", "name").strip()

    qs = Product.objects.all()

    if q:
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(category__icontains=q) |
            Q(supplier__icontains=q)
        )
    if category:
        qs = qs.filter(category=category)
    if supplier:
        qs = qs.filter(supplier__iexact=supplier)
    if min_price:
        try: qs = qs.filter(price__gte=float(min_price))
        except ValueError: pass
    if max_price:
        try: qs = qs.filter(price__lte=float(max_price))
        except ValueError: pass
    if in_stock == "yes":
        qs = qs.filter(quantity__gt=0)
    elif in_stock == "no":
        qs = qs.filter(quantity__lte=0)

    allowed_order = {
        "name","-name","price","-price","quantity","-quantity",
        "supplier","-supplier","category","-category"
    }
    if order_by not in allowed_order:
        order_by = "name"

    return qs.order_by(order_by)

def _link_callback(uri, rel):
    """
    Permite a xhtml2pdf resolver rutas de STATIC y MEDIA.
    """
    if uri.startswith(settings.MEDIA_URL):
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
    elif uri.startswith(settings.STATIC_URL):
        path = os.path.join(getattr(settings, "STATIC_ROOT", ""), uri.replace(settings.STATIC_URL, ""))
    else:
        return uri  # URL absoluta
    if not os.path.isfile(path):
        return uri
    return path

def inventory_pdf(request):
    products = _filtered_products(request)  # SIN paginar

    context = {
        "products": products,
        "filters": {
            "q": request.GET.get("q",""),
            "category": request.GET.get("category",""),
            "supplier": request.GET.get("supplier",""),
            "min_price": request.GET.get("min_price",""),
            "max_price": request.GET.get("max_price",""),
        }
    }

    template = get_template("inventory_pdf.html")
    html = template.render(context)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="inventario.pdf"'

    pisa.CreatePDF(html, dest=response, link_callback=_link_callback)
    return response
