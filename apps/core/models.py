from django.db import models


class Settings(models.Model):
    key = models.CharField(max_length=255, unique=True)
    value = models.TextField()
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)

    def __str__(self):
        return f"{self.key}: {self.value}"

    @staticmethod
    def get_all():
        return {setting.key: setting.value for setting in Settings.objects.all()}

    @staticmethod
    def get_value(key, default=None):
        """Retrieve a global option, returning a default value if not found."""
        option = Settings.objects.filter(key=key).first()
        return option.value if option else default
