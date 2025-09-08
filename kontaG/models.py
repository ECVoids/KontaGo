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