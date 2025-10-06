from django.shortcuts import render
from apps.core.models import Settings

def index(request):
    settings = Settings.get_all()
    return render(request, 'index.html', {"settings": settings})