from django.db import models

class Product(models.Model):

    CATEGORY_CHOICES = [
        ('alimentos', 'Alimentos'),
        ('utiles', 'Útiles escolares'),
        ('peluqueria', 'Peluquería'),
        ('cosmetica', 'Cosmética'),
        ('limpieza', 'Limpieza'),
    ]

    name = models.CharField(max_length=200, unique=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    supplier = models.CharField(max_length=200, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    expiration_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.name
    
class Supplier(models.Model):
    name = models.CharField(max_length=100, unique=True)
    contact_name = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    products = models.ManyToManyField(Product, related_name="suppliers")
    
    def __str__(self):
        return self.name  

class Venta(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def save(self, *args, **kwargs):
        # Calcular total antes de guardar
        if self.product and self.cantidad:
            self.total = self.product.price * self.cantidad
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cantidad} x {self.product.name} ({self.total})"
    
class Factura(models.Model):
    codigo = models.CharField(max_length=20, unique=True)  # ej: F001
    fecha = models.DateTimeField(auto_now_add=True)
    cliente = models.CharField(max_length=100, blank=True, null=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Factura {self.codigo} - {self.fecha.strftime('%Y-%m-%d')}"

class DetalleFactura(models.Model):
    factura = models.ForeignKey(Factura, related_name="detalles", on_delete=models.CASCADE)
    producto = models.ForeignKey("Product", on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.producto.name} x {self.cantidad}"