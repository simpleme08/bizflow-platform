from django.contrib import admin

from .models import EmployeeSalary, EmployeeSalaryHistory, PayrollAdjustment, PayrollHoliday, PayrollPeriod, PayrollProfile, PayrollRecord, PayrollWageRate


@admin.register(EmployeeSalary)
class EmployeeSalaryAdmin(admin.ModelAdmin):
    list_display = ('employee', 'basic_salary', 'effective_date')


@admin.register(EmployeeSalaryHistory)
class EmployeeSalaryHistoryAdmin(admin.ModelAdmin):
    list_display = ('employee', 'basic_salary', 'effective_date', 'reason')
    list_filter = ('effective_date',)
    search_fields = ('employee__employee_number', 'employee__first_name', 'employee__last_name', 'reason')
    date_hierarchy = 'effective_date'


@admin.register(PayrollProfile)
class PayrollProfileAdmin(admin.ModelAdmin):
    list_display = ('employee', 'sss_number', 'philhealth_number', 'pagibig_number', 'tin', 'minimum_wage_earner', 'wage_region', 'wage_category')
    list_filter = ('minimum_wage_earner', 'wage_category', 'wage_region')
    search_fields = ('employee__employee_number', 'employee__first_name', 'employee__last_name', 'tin')


@admin.register(PayrollWageRate)
class PayrollWageRateAdmin(admin.ModelAdmin):
    list_display = ('region_code', 'category', 'daily_rate', 'effective_from', 'effective_to', 'wage_order', 'organization', 'is_active')
    list_filter = ('region_code', 'category', 'is_active')
    search_fields = ('region_code', 'category', 'wage_order', 'organization__name')
    date_hierarchy = 'effective_from'


@admin.register(PayrollHoliday)
class PayrollHolidayAdmin(admin.ModelAdmin):
    list_display = ('holiday_date', 'name', 'kind', 'is_double', 'organization', 'is_active')
    list_filter = ('kind', 'is_double', 'is_active')
    search_fields = ('name', 'organization__name')
    date_hierarchy = 'holiday_date'


@admin.register(PayrollPeriod)
class PayrollPeriodAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'start_date', 'end_date', 'frequency', 'status')
    list_filter = ('status', 'frequency')
    search_fields = ('name', 'organization__name')


@admin.register(PayrollRecord)
class PayrollRecordAdmin(admin.ModelAdmin):
    list_display = ('employee', 'payroll_period', 'gross_pay', 'total_deductions', 'net_pay', 'status')
    list_filter = ('status', 'payroll_period__frequency')
    search_fields = ('employee__employee_number', 'employee__first_name', 'employee__last_name')
    readonly_fields = ('gross_pay', 'net_pay')


@admin.register(PayrollAdjustment)
class PayrollAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('payroll_record', 'kind', 'description', 'amount', 'taxable', 'approved')
    list_filter = ('kind', 'taxable', 'approved')
