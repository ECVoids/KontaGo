from django import forms
from .models import Product, Supplier, Factura, DetalleFactura, Product


from django import forms

class ProductEntryForm(forms.Form):

    CATEGORY_CHOICES = [
        ('alimentos', 'Alimentos'),
        ('utiles', 'Útiles escolares'),
        ('peluqueria', 'Peluquería'),
        ('cosmetica', 'Cosmética'),
        ('limpieza', 'Limpieza'),
    ]
     
    name = forms.CharField(label="Product Name", max_length=100)
    category = forms.ChoiceField(label="Category", choices=CATEGORY_CHOICES)
    description = forms.CharField(label="Description", widget=forms.Textarea, required=False)
    price = forms.DecimalField(label="Price", min_value=0, max_digits=10, decimal_places=2)
    quantity = forms.IntegerField(label="Initial Stock", min_value=0)
    supplier = forms.CharField(label="Supplier", max_length=100, required=False)
    image = forms.ImageField(label="Product Image", required=False)
    expiration_date = forms.DateField(label="Expiration Date", required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    #Para no crear productos con el mismo nombre(que ya existe en la base de datos)
    def clean_name(self):
        name = self.cleaned_data["name"]
        if Product.objects.filter(name=name).exists():
            raise forms.ValidationError("⚠️ A product with this name already exists.")
        return name
    
    #Validación personalizada para la fecha de expiración
    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get("category")
        expiration_date = cleaned_data.get("expiration_date")

        # Definir qué categorías requieren fecha de vencimiento
        categories_with_expiration = ["alimentos", "cosmetica", "limpieza"]

        #Validar si fecha es obligatoria
        if category in categories_with_expiration and not expiration_date:
            self.add_error("expiration_date", "Expiration date is required for food products.")
        
        return cleaned_data
    
class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_name', 'phone', 'email', 'address', 'notes', 'products']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'products': forms.CheckboxSelectMultiple,  # checkboxes
        }
        labels = {
            'name': "Company's name",
        }

    def save(self, commit=True):
        supplier = super().save(commit=False)
        if commit:
            supplier.save()
            self.save_m2m()  # 👈 guarda la relación ManyToMany
        return supplier



class ProductTakeoutForm(forms.Form):
    name = forms.CharField(label="Product Name", max_length=100)
    quantity = forms.IntegerField(label="Quantity to Take Out", min_value=1)


class FacturaForm(forms.ModelForm):
    class Meta:
        model = Factura
        fields = ["cliente"]  # mantenemos cliente, no pedimos total
        widgets = {
            "cliente": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre del cliente"}),
        }


class DetalleFacturaForm(forms.ModelForm):
    class Meta:
        model = DetalleFactura
        fields = ["producto", "cantidad"]  # subtotal y precio_unitario se calculan
        widgets = {
            "cantidad": forms.NumberInput(attrs={"min": 1, "class": "form-control"}),
            "producto": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Crear lista de opciones personalizadas con data-stock
        productos = Product.objects.all()
        self.fields["producto"].choices = [
            (p.id, f"{p.name} (Stock: {p.quantity})") for p in productos
        ]

        # 🔑 Diccionario id -> stock (para pasarlo al template desde el primer form)
        self.producto_stock = {p.id: p.quantity for p in productos}

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Tomamos el precio desde el producto
        instance.precio_unitario = instance.producto.price
        # Calculamos subtotal
        instance.subtotal = instance.precio_unitario * instance.cantidad
        if commit:
            instance.save()
        return instance


# 🔑 Un formset para manejar varios detalles dentro de una sola factura
DetalleFacturaFormSet = forms.inlineformset_factory(
    Factura,
    DetalleFactura,
    form=DetalleFacturaForm,
    extra=1,
    can_delete=True
)