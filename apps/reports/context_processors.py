from django.conf import settings

def currency_symbol(request):
    return {"CURRENCY_SYMBOL": getattr(settings, "CURRENCY_SYMBOL", "€")}