from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.db import transaction
from django.db.models import Max
import json
from .forms import ProductEntryForm, ProductTakeoutForm, SupplierForm, FacturaForm, DetalleFacturaFormSet
from .models import Product, Supplier, Venta, Factura, DetalleFactura
from django.contrib import messages



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

def inventory_display(request):
    products = Product.objects.all()
    return render(request, 'inventory_display.html', {'products': products})

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