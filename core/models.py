from django.db import models
from django.contrib.auth.models import User

class Company(models.Model):
    name = models.CharField(max_length=128, unique=True)
    address = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Companies"

    def __str__(self):
        return self.name
    
class Vessel(models.Model):
    vessel_id = models.AutoField(primary_key=True)

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="vessels"
    )

    name = models.CharField(max_length=128)
    imo_number = models.CharField(max_length=64, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.company.name})"
    
class Engine(models.Model):
    engine_id = models.AutoField(primary_key=True)

    vessel = models.ForeignKey(
        Vessel,
        on_delete=models.CASCADE,
        related_name="engines"
    )

    serial_number = models.CharField(max_length=128, unique=True)
    model_name = models.CharField(max_length=128)

    engine_type = models.CharField(
        max_length=2,
        choices=[
            ("ME", "Main Engine"),
            ("AE", "Auxiliary Generator"),
        ]
    )

    rated_rpm = models.IntegerField(null=True, blank=True)
    rated_power = models.IntegerField(null=True, blank=True)
    rated_frequency = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.model_name} - {self.serial_number}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    is_company_admin = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username