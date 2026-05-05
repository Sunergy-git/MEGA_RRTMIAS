from django.shortcuts import render
from core.models import Engine

def home(request):
    if request.user.is_superuser:
        engines = Engine.objects.all()
    else:
        engines = Engine.objects.filter(
            vessel__company=request.user.userprofile.company
        )

    return render(request, "dashboard/home.html", {"engines": engines})
