from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MinLengthValidator
from django.contrib.auth.models import User

class Product(models.Model):
    id = models.CharField(max_length=64, primary_key=True, unique=True)
    name = models.TextField(validators=[MinLengthValidator(2)])
    description = models.TextField(null=True)
    amount = models.IntegerField(default=1, validators=[MinValueValidator(0)])
    price = models.FloatField(validators=[MinValueValidator(0)])

    user_added_id = models.ForeignKey(User, on_delete=models.CASCADE)

class Sale(models.Model):
    id = models.CharField(max_length=64, primary_key=True, unique=True)
    amount = models.IntegerField(default=1, validators=[MinValueValidator(0)])
    date = models.DateField()

    product_id = models.ForeignKey(Product, on_delete=models.CASCADE)
    user_sold_id = models.ForeignKey(User, on_delete=models.CASCADE)