from django import forms
from .models import Product

class ProductEntryForm(forms.Form):
    name = forms.CharField(label="Product Name", max_length=100)
    description = forms.CharField(label="Description", required=False, widget=forms.Textarea)
    quantity = forms.IntegerField(label="Quantity", min_value=1)

class ProductTakeoutForm(forms.Form):
    name = forms.CharField(label="Product Name", max_length=100)
    quantity = forms.IntegerField(label="Quantity to Take Out", min_value=1)
