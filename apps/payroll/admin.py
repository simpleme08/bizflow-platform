from django.contrib import admin

from .models import EmployeeSalary, PayrollPeriod, PayrollRecord

@admin.register(EmployeeSalary)
class EmployeeSalaryAdmin(admin.ModelAdmin):
	list_display = ('employee', 'basic_salary', 'effective_date')


@admin.register(PayrollPeriod)
class PayrollPeriodAdmin(admin.ModelAdmin):
	list_display = ('name', 'start_date', 'end_date', 'status')
	list_filter = ('status',)


@admin.register(PayrollRecord)
class PayrollRecordAdmin(admin.ModelAdmin):
	list_display = ('employee', 'payroll_period', 'gross_pay', 'net_pay', 'status')
	list_filter = ('status', 'payroll_period')
	readonly_fields = ('gross_pay', 'net_pay')
