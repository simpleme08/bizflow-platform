from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import BaseModel
from apps.organization.models import Organization


class Client(BaseModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='clients')
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('organization', 'code'), name='unique_client_code_per_organization')]
        ordering = ('name',)

    def __str__(self):
        return f'{self.code} - {self.name}'


class ClientSite(BaseModel):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='sites')
    name = models.CharField(max_length=150)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('client', 'name'), name='unique_client_site_name')]
        ordering = ('client', 'name')

    def __str__(self):
        return f'{self.client.name} - {self.name}'


class ShiftTemplate(BaseModel):
    # Nullable preserves existing global templates while allowing new templates
    # to be explicitly owned by an organization. Cross-tenant templates are never
    # valid for a tenant-owned EmployeeAssignment.
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, null=True, blank=True, related_name='shift_templates')
    name = models.CharField(max_length=100, unique=True)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def clean(self):
        super().clean()
        if self.end_time == self.start_time:
            raise ValidationError('Shift start and end time cannot be identical.')

    def __str__(self):
        return self.name
