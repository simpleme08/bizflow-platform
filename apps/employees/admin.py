from django.contrib import admin

from .models import Employee, EmployeeAssignment, EmployeeDocument, EmploymentHistory


class EmployeeAssignmentInline(admin.TabularInline):
    model = EmployeeAssignment
    extra = 0


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_number', 'last_name', 'first_name', 'organization', 'status', 'manager', 'is_active')
    list_filter = ('organization', 'status', 'is_active')
    search_fields = ('employee_number', 'first_name', 'last_name', 'user__username', 'work_email', 'personal_email')
    fieldsets = (
        (None, {'fields': ('employee_number', 'user', 'organization', 'first_name', 'last_name', 'status', 'is_active')}),
        ('Contact', {'fields': ('birth_date', 'sex', 'personal_email', 'work_email', 'mobile_number', 'address', 'emergency_contact_name', 'emergency_contact_phone')}),
        ('Employment', {'fields': ('hire_date', 'regularization_date', 'separation_date', 'manager', 'department', 'position', 'employment_type')}),
    )
    inlines = (EmployeeAssignmentInline,)


@admin.register(EmployeeAssignment)
class EmployeeAssignmentAdmin(admin.ModelAdmin):
    list_display = ('employee', 'shift_template', 'start_date', 'end_date', 'is_primary')
    list_filter = ('is_primary', 'shift_template')
    search_fields = ('employee__employee_number', 'employee__last_name')
    fieldsets = ((None, {'fields': ('employee', 'shift_template', 'client', 'client_site', 'cost_center', 'start_date', 'end_date', 'is_primary')}),)


@admin.register(EmploymentHistory)
class EmploymentHistoryAdmin(admin.ModelAdmin):
    list_display = ('employee', 'status', 'effective_date', 'end_date', 'reason')
    list_filter = ('status',)
    search_fields = ('employee__employee_number', 'employee__last_name', 'reason')


@admin.register(EmployeeDocument)
class EmployeeDocumentAdmin(admin.ModelAdmin):
    list_display = ('employee', 'document_type', 'name', 'issued_date', 'expiry_date', 'is_required', 'status')
    list_filter = ('document_type', 'is_required', 'status')
    search_fields = ('employee__employee_number', 'employee__last_name', 'name')
