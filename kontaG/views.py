from django.shortcuts import render
from django.http import HttpResponse
from .forms import ProductEntryForm
from .models import Product
from .forms import ProductTakeoutForm

# Create your views here.
def home(request):
    return render(request, 'home.html')

def product_entry(request):
    message = ""
    if request.method == 'POST':
        form = ProductEntryForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            description = form.cleaned_data['description']
            quantity = form.cleaned_data['quantity']
            product, created = Product.objects.get_or_create(name=name, defaults={'description': description, 'quantity': 0})
            if not created:
                product.quantity += quantity
                if description:
                    product.description = description
            else:
                product.quantity = quantity
            product.save()
            message = "Product entry registered successfully!"
            form = ProductEntryForm()  # Reset form
    else:
        form = ProductEntryForm()
    return render(request, 'product_entry.html', {'form': form, 'message': message})

# ...existing code...
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