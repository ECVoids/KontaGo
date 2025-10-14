from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
import os
from django.db import transaction
from django.db.models import Max
import json
from .forms import ProductEntryForm, ProductTakeoutForm, SupplierForm
from .models import Product, Supplier
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.conf import settings

from invoices.models import Factura, DetalleFactura, Venta
from invoices.forms import FacturaForm, DetalleFacturaFormSet
from .suggestions import suggest_price, assign_suggestions

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

    for product in qs:
        if product.price_suggestion == 0:
            product.price_suggestion = suggest_price(product_name=product.name, product_category=product.category, product_description=product.description)
            product.save()
        if product.product_assigned_suggestions == "Blank" or product.product_assigned_suggestions is None:
            product.product_assigned_suggestions = assign_suggestions(product_name=product.name, product_category=product.category, product_description=product.description)
            product.save()

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
