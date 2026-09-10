from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.core.models import BaseModel
from apps.employees.models import Employee


class EmployeeSalary(BaseModel):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='salary')
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)
    effective_date = models.DateField()


class PayrollProfile(BaseModel):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='payroll_profile')
    sss_number = models.CharField(max_length=20, blank=True)
    philhealth_number = models.CharField(max_length=20, blank=True)
    pagibig_number = models.CharField(max_length=20, blank=True)
    tin = models.CharField(max_length=20, blank=True)
    minimum_wage_earner = models.BooleanField(default=False)


class PayrollPeriod(BaseModel):
    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        CALCULATED = 'CALCULATED', 'Calculated'
        APPROVED = 'APPROVED', 'Approved'
        PAID = 'PAID', 'Paid'

    class Frequency(models.TextChoices):
        SEMI_MONTHLY = 'SEMI_MONTHLY', 'Semi-monthly'
        MONTHLY = 'MONTHLY', 'Monthly'

    organization = models.ForeignKey('organization.Organization', on_delete=models.PROTECT, related_name='payroll_periods')
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    frequency = models.CharField(max_length=20, choices=Frequency.choices, default=Frequency.SEMI_MONTHLY)

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
    holiday_pay = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    night_differential = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    allowances = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    commissions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    bonuses = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    taxable_supplementary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    thirteenth_month = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    sss_employee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    sss_employer = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    philhealth_employee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    philhealth_employer = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    pagibig_employee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    pagibig_employer = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    withholding_tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    late_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    undertime_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    leave_without_pay = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    loan_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    other_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    gross_pay = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    net_pay = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('employee', 'payroll_period'), name='unique_employee_payroll_period')]

    def clean(self):
        super().clean()
        if self.employee_id and self.payroll_period_id and self.employee.organization_id != self.payroll_period.organization_id:
            raise ValidationError('Employee and payroll period must belong to the same organization.')
        if self.net_pay < 0:
            raise ValidationError('Payroll net pay cannot be negative.')

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def statutory_deductions(self):
        return self.sss_employee + self.philhealth_employee + self.pagibig_employee

    @property
    def total_deductions(self):
        return (self.late_deduction + self.undertime_deduction + self.leave_without_pay + self.loan_deductions + self.statutory_deductions + self.withholding_tax + self.other_deductions)

    @property
    def employer_contributions(self):
        return self.sss_employer + self.philhealth_employer + self.pagibig_employer


class PayrollAdjustment(BaseModel):
    class Kind(models.TextChoices):
        EARNING = 'EARNING', 'Earning'
        DEDUCTION = 'DEDUCTION', 'Deduction'

    payroll_record = models.ForeignKey(PayrollRecord, on_delete=models.PROTECT, related_name='adjustments')
    kind = models.CharField(max_length=20, choices=Kind.choices)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    taxable = models.BooleanField(default=True)
    approved = models.BooleanField(default=False)

    def clean(self):
        super().clean()
        if self.amount <= 0:
            raise ValidationError('Adjustment amount must be greater than zero.')
