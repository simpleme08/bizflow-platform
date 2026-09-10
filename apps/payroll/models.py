from decimal import Decimal

from django.db import models
from django.db.models import Q

from apps.core.models import BaseModel
from apps.employees.models import Employee


class EmployeeSalary(BaseModel):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='salary')
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)
    effective_date = models.DateField()


class PayrollPeriod(BaseModel):
    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        CALCULATED = 'CALCULATED', 'Calculated'
        APPROVED = 'APPROVED', 'Approved'
        PAID = 'PAID', 'Paid'

    organization = models.ForeignKey('organization.Organization', on_delete=models.PROTECT, related_name='payroll_periods')
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(end_date__gte=models.F('start_date')), name='payroll_period_valid_dates'),
            models.UniqueConstraint(fields=('organization', 'start_date', 'end_date'), name='unique_payroll_period_dates_per_organization'),
        ]
        ordering = ('-end_date', '-start_date')

    def __str__(self):
        return self.name


class PayrollRecord(BaseModel):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        APPROVED = 'APPROVED', 'Approved'
        PAID = 'PAID', 'Paid'

    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='payroll_records')
    payroll_period = models.ForeignKey(PayrollPeriod, on_delete=models.PROTECT, related_name='records')
    basic_pay = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    overtime_pay = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    late_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    undertime_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    other_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    gross_pay = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    net_pay = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('employee', 'payroll_period'), name='unique_employee_payroll_period'),
        ]

    @property
    def total_deductions(self):
        return self.late_deduction + self.undertime_deduction + self.other_deductions
