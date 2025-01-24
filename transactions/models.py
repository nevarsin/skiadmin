from django.db import models
from associates.models import Associate

class Transaction(models.Model):
    associate = models.ForeignKey(Associate, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=100)  # e.g., 'Skipass Purchase', 'Card Renewal'
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type} - ${self.amount}"