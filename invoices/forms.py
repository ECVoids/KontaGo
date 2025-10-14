from django import forms
from .models import Factura, DetalleFactura  # modelos propios del módulo invoices
from inventory.models import Product
from django.forms import inlineformset_factory

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
