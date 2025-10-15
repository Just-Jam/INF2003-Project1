from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Actor(models.Model):
    name = models.CharField(max_length=100)
    age = models.IntegerField()
    bio = models.TextField()

    def __str__(self):
        return self.name
