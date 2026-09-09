from django.contrib import admin

from .models import Employee, EmployeeAssignment


class EmployeeAssignmentInline(admin.TabularInline):
	model = EmployeeAssignment
	extra = 0


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
	list_display = ('employee_number', 'last_name', 'first_name', 'organization', 'is_active')
	list_filter = ('organization', 'is_active')
	search_fields = ('employee_number', 'first_name', 'last_name', 'user__username')
	fieldsets = (
		(None, {'fields': ('employee_number', 'user', 'organization', 'first_name', 'last_name', 'is_active')}),
		('Organization structure', {'fields': ('department', 'position', 'employment_type')}),
	)
	inlines = (EmployeeAssignmentInline,)


@admin.register(EmployeeAssignment)
class EmployeeAssignmentAdmin(admin.ModelAdmin):
	list_display = ('employee', 'shift_template', 'start_date', 'end_date', 'is_primary')
	list_filter = ('is_primary', 'shift_template')
	search_fields = ('employee__employee_number', 'employee__last_name')
	fieldsets = (
		(None, {'fields': ('employee', 'shift_template', 'client', 'client_site', 'cost_center', 'start_date', 'end_date', 'is_primary')}),
	)
