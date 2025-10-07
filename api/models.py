from django.db import models
from django.contrib.auth.hashers import make_password

class Profile(models.Model):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    score = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        # Hash the password before saving
        if not self.pk:  # only hash when creating new user
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username
