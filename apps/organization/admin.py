from django.contrib import admin

from .models import CostCenter, Department, EmploymentType, Organization, OrganizationMembership, Position

admin.site.register(Organization)
admin.site.register(OrganizationMembership)
admin.site.register(Department)
admin.site.register(Position)
admin.site.register(EmploymentType)
admin.site.register(CostCenter)
