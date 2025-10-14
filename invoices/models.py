from django.db import models
#from inventory.models import Product  # importa Product desde la app de inventario

class Venta(models.Model):
    product = models.ForeignKey("inventory.Product", on_delete=models.CASCADE)
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
    producto = models.ForeignKey("inventory.Product", on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.producto.name} x {self.cantidad}"
    
