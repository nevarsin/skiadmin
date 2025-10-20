from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.articles.models import Article
from apps.associates.models import Associate


class Transaction(models.Model):
    TRANSACTION_METHODS = [
        ('cash', _('Cash')),  # ('value', 'Display Name')
        ('wiretransfer', _('Wire Transfer')),        
        ('card', _('Card (POS)')),
    ]

    associate = models.ForeignKey(Associate, on_delete=models.CASCADE, related_name="transactions")
    amount = models.DecimalField(_("Amount"),max_digits=10, decimal_places=2, default=0.00)  # Grand total
    transaction_type = models.CharField(_("Type"),default="")
    method = models.CharField(_("Payment Method"),choices=TRANSACTION_METHODS,default="cash",max_length=20)

    date = models.DateTimeField(_("Date"),auto_now_add=True)

    def update_total(self):
        """Updates the total amount based on related TransactionLines."""
        self.amount = self.lines.aggregate(total=models.Sum("price"))["total"] or 0
        self.save()

    def __str__(self):
        return f"Transaction #{self.id} - {self.associate} - ${self.amount}"

class TransactionLine(models.Model):

    # Fixed choice values    
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name="lines")
    associate = models.ForeignKey(Associate, on_delete=models.CASCADE)  # Optional: link to a specific associate
    quantity = models.PositiveIntegerField(_("Quantity"),default=1)
    article = models.ForeignKey(Article, related_name="article", on_delete=models.SET_NULL, null=True)
    
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price per unit

    def total_price(self):
        """Calculate the total price of this line item."""
        return self.quantity * self.price

    def save(self, *args, **kwargs):
        """Override save to update transaction amount whenever a line item changes."""
        super().save(*args, **kwargs)
        self.transaction.update_total()

    def delete(self, *args, **kwargs):
        """Override delete to update transaction amount when a line item is removed."""
        super().delete(*args, **kwargs)
        self.transaction.update_total()

    def __str__(self):
        return f"{self.item_name} (x{self.quantity}) - ${self.price}"