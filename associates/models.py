from django.db import models
import uuid

class Associate(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    membership_number = models.CharField(max_length=50, unique=True)
    joined_date = models.DateField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.membership_number:
            self.membership_number = str(uuid.uuid4())[:8]  # Generate a unique ID
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"