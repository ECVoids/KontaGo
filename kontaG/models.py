from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name