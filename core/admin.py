from django.contrib import admin

from django.contrib import admin
from .models import Company, Vessel, Engine, UserProfile

admin.site.register(Company)
admin.site.register(Vessel)
admin.site.register(Engine)
admin.site.register(UserProfile)
