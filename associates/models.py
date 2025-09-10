import uuid
from datetime import date, datetime
from django.db import models
from django.utils.translation import gettext_lazy as _
from . import utils

class Associate(models.Model):

    # Fixed choice values
    MEMBERSHIP_TYPES = [
        ('standard', _('Standard')),  # ('value', 'Display Name')
        ('minor', _('Minor')),
        ('counselor', _('Counselor')),
    ]

    first_name = models.CharField(_("First Name"), max_length=100)
    last_name = models.CharField(_("Last Name"), max_length=100)
    email = models.EmailField(_("Email"), unique=True)
    membership_number = models.CharField(max_length=50, unique=True)
    membership_type = models.CharField(
        _("Membership type"),
        max_length=20,  # Ensure the max_length is large enough for all choices
        choices=MEMBERSHIP_TYPES,
        default='standard'  # Set a default value
    )
    joined_date = models.DateField(auto_now_add=True)
    renewal_date = models.DateField(auto_now_add=True)
    active = models.BooleanField(_("Active"),default=False)
    expiration_date = models.DateField()
    address_street = models.CharField(_("Address street"), max_length=255)  # Street name, e.g., "Main Street"
    address_number = models.CharField(_("Address number"),max_length=10)  # House/building number, e.g., "42A"
    address_city = models.CharField(_("Address city"),max_length=100)  # City name, e.g., "New York"
    address_zip = models.CharField(_("Address ZIP code"),max_length=20)  # ZIP or postal code, e.g., "10001"
    address_province = models.CharField(_("Address province"),max_length=100)  # Province/state name, e.g., "NY"
    address_country = models.CharField(_("Address country"),max_length=100)  # Country name, e.g., "United States"
    birth_date = models.DateField(_("Date of birth"))  # Date of birth, e.g., "1990-01-01"
    birth_city = models.CharField(_("Birth city"),max_length=100)  # City of birth, e.g., "Los Angeles"
    birth_province = models.CharField(_("Birth province"),max_length=100)  # Province/state of birth, e.g., "CA"
    birth_country = models.CharField(_("Birth country"),max_length=100)  # Country of birth, e.g., "USA"
    fiscal_code = models.CharField(_("Fiscal code"),max_length=50, unique=True)  # Unique fiscal/ID code
    phone = models.CharField(_("Phone"),max_length=20, blank=True, null=True)  # Phone number, optional
    card_sent = models.BooleanField(_("Card sent"),default=False)  # Whether the membership card was sent
    notes = models.TextField(_("Notes"),blank=True, null=True)  # Additional notes, optional
    parent_email = models.EmailField(_("Parent email"))

    def save(self, *args, **kwargs):
        if utils.is_minor(self.birth_date):
            self.membership_type="minor"
        if not self.membership_number:
            self.membership_number = str(uuid.uuid4())[:8]  # Generate a unique ID
        if not self.renewal_date:
            self.renewal_date = date.today()
            if self.renewal_date > date(self.renewal_date.year, 8, 31):
                self.expiration_date = date(self.renewal_date.year + 1, 8, 31)  # 30/04 of the subsequent year
            else:
                self.expiration_date = date(self.renewal_date.year, 8, 31)  # 30/04 of the current year

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"