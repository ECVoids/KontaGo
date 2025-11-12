from django.db import models
from django.contrib.auth.models import User

class Perfil(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    rut = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.usuario.username