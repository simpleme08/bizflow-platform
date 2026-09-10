import uuid
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

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(basic_salary__gte=0), name='employee_salary_non_negative')]

    def clean(self):
        super().clean()
        if self.basic_salary < 0:
            raise ValidationError('Salary cannot be negative.')


class EmployeeSalaryHistory(BaseModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='salary_history')
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)
    effective_date = models.DateField()
    reason = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('employee', 'effective_date'), name='unique_employee_salary_history_date'),
            models.CheckConstraint(condition=Q(basic_salary__gte=0), name='salary_history_non_negative'),
        ]
        ordering = ('-effective_date', '-created_at')

    def clean(self):
        super().clean()
        if self.basic_salary < 0:
            raise ValidationError('Salary cannot be negative.')


class PayrollProfile(BaseModel):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='payroll_profile')
    sss_number = models.CharField(max_length=20, blank=True)
    philhealth_number = models.CharField(max_length=20, blank=True)
    pagibig_number = models.CharField(max_length=20, blank=True)
    tin = models.CharField(max_length=20, blank=True)
    minimum_wage_earner = models.BooleanField(default=False)
    wage_region = models.CharField(max_length=20, blank=True)
    wage_category = models.CharField(max_length=40, blank=True, default='NON_AGRICULTURE')


class PayrollWageRate(BaseModel):
    organization = models.ForeignKey('organization.Organization', on_delete=models.CASCADE, null=True, blank=True, related_name='payroll_wage_rates')
    region_code = models.CharField(max_length=20)
    category = models.CharField(max_length=40, default='NON_AGRICULTURE')
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    wage_order = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('-effective_from', '-created_at')
        constraints = [
            models.CheckConstraint(condition=Q(daily_rate__gt=0), name='payroll_wage_rate_positive'),
            models.CheckConstraint(condition=Q(effective_to__isnull=True) | Q(effective_to__gte=models.F('effective_from')), name='payroll_wage_rate_valid_dates'),
        ]

    def clean(self):
        super().clean()
        if self.daily_rate <= 0:
            raise ValidationError('Daily wage rate must be greater than zero.')
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValidationError('Wage rate end date cannot be before its effective date.')


class PayrollHoliday(BaseModel):
    class Kind(models.TextChoices):
        REGULAR = 'REGULAR', 'Regular holiday'
        SPECIAL_NON_WORKING = 'SPECIAL_NON_WORKING', 'Special non-working day'
        SPECIAL_WORKING = 'SPECIAL_WORKING', 'Special working day'

    organization = models.ForeignKey('organization.Organization', on_delete=models.CASCADE, null=True, blank=True, related_name='payroll_holidays')
    holiday_date = models.DateField()
    name = models.CharField(max_length=150)
    kind = models.CharField(max_length=30, choices=Kind.choices)
    is_double = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('organization', 'holiday_date'), name='unique_payroll_holiday_per_org_date')]
        ordering = ('holiday_date',)

    def clean(self):
        super().clean()
        if self.kind == self.Kind.SPECIAL_WORKING and self.is_double:
            raise ValidationError('A special working day cannot be a double holiday.')


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

    def clean(self):
        super().clean()
        if self.end_date < self.start_date:
            raise ValidationError('Payroll period end date cannot be before its start date.')
        if self.organization_id:
            overlap = type(self).objects.filter(organization_id=self.organization_id, start_date__lte=self.end_date, end_date__gte=self.start_date).exclude(pk=self.pk)
            if overlap.exists():
                raise ValidationError('Payroll period overlaps an existing period for this organization.')

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
        if self.pk and not self._state.adding:
            previous = type(self).objects.get(pk=self.pk)
            if previous.status in (self.Status.APPROVED, self.Status.PAID):
                changed_fields = []
                for field in self._meta.fields:
                    if field.name == 'updated_at':
                        continue
                    if getattr(previous, field.attname) != getattr(self, field.attname):
                        changed_fields.append(field.name)
                if changed_fields != ['status']:
                    raise ValidationError('Approved or paid payroll records are immutable except for their lifecycle status.')
                if previous.status == self.Status.PAID and self.status != self.Status.PAID:
                    raise ValidationError('Paid payroll records cannot be reopened.')
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def statutory_deductions(self):
        return self.sss_employee + self.philhealth_employee + self.pagibig_employee

    @property
    def total_deductions(self):
        return self.late_deduction + self.undertime_deduction + self.leave_without_pay + self.loan_deductions + self.statutory_deductions + self.withholding_tax + self.other_deductions

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
        if self.payroll_record_id and self.payroll_record.status in (PayrollRecord.Status.APPROVED, PayrollRecord.Status.PAID):
            raise ValidationError('Adjustments cannot be changed after payroll approval.')

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
