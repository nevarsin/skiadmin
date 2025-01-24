from django.db import models
import uuid

class Associate(models.Model):

    # Fixed choice values
    MEMBERSHIP_TYPES = [
        ('standard', 'Standard'),  # ('value', 'Display Name')
        ('minor', 'Minor'),
        ('counselor', 'Counselor'),        
    ]

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    membership_number = models.CharField(max_length=50, unique=True)
    membership_type = models.CharField(
        max_length=20,  # Ensure the max_length is large enough for all choices
        choices=MEMBERSHIP_TYPES,
        default='standard'  # Set a default value
    )
    joined_date = models.DateField(auto_now_add=True)
    renewal_date = models.DateField()
    address_street = models.CharField(max_length=255)  # Street name, e.g., "Main Street"
    address_number = models.CharField(max_length=10)  # House/building number, e.g., "42A"
    address_city = models.CharField(max_length=100)  # City name, e.g., "New York"
    address_zip = models.CharField(max_length=20)  # ZIP or postal code, e.g., "10001"
    address_province = models.CharField(max_length=100)  # Province/state name, e.g., "NY"
    address_country = models.CharField(max_length=100)  # Country name, e.g., "United States"
    birth_date = models.DateField()  # Date of birth, e.g., "1990-01-01"
    birth_city = models.CharField(max_length=100)  # City of birth, e.g., "Los Angeles"
    birth_province = models.CharField(max_length=100)  # Province/state of birth, e.g., "CA"
    birth_country = models.CharField(max_length=100)  # Country of birth, e.g., "USA"
    fiscal_code = models.CharField(max_length=50, unique=True)  # Unique fiscal/ID code    
    phone = models.CharField(max_length=20, blank=True, null=True)  # Phone number, optional
    card_sent = models.BooleanField(default=False)  # Whether the membership card was sent
    notes = models.TextField(blank=True, null=True)  # Additional notes, optional
    parent_email = models.EmailField()  

    def save(self, *args, **kwargs):
        if not self.membership_number:
            self.membership_number = str(uuid.uuid4())[:8]  # Generate a unique ID
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"