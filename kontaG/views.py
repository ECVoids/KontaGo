from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .forms import ProductEntryForm, ProductTakeoutForm, SupplierForm
from .models import Product, Supplier
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