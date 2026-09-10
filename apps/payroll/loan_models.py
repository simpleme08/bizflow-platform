from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.core.models import BaseModel
from apps.employees.models import Employee


class EmployeeLoan(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        PAID = 'PAID', 'Paid'
        SUSPENDED = 'SUSPENDED', 'Suspended'
        CANCELLED = 'CANCELLED', 'Cancelled'

    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='loans')
    lender = models.CharField(max_length=120)
    loan_type = models.CharField(max_length=80)
    reference_number = models.CharField(max_length=80, blank=True)
    principal = models.DecimalField(max_digits=12, decimal_places=2)
    interest = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    installment_amount = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    balance = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ('start_date', 'created_at')
        constraints = [
            models.CheckConstraint(condition=Q(principal__gt=0), name='employee_loan_positive_principal'),
            models.CheckConstraint(condition=Q(interest__gte=0), name='employee_loan_nonnegative_interest'),
            models.CheckConstraint(condition=Q(installment_amount__gt=0), name='employee_loan_positive_installment'),
            models.CheckConstraint(condition=Q(balance__gte=0), name='employee_loan_nonnegative_balance'),
            models.CheckConstraint(condition=Q(end_date__gte=models.F('start_date')), name='employee_loan_valid_dates'),
        ]

    def clean(self):
        super().clean()
        if self.principal <= 0:
            raise ValidationError('Loan principal must be greater than zero.')
        if self.interest < 0:
            raise ValidationError('Loan interest cannot be negative.')
        if self.installment_amount <= 0:
            raise ValidationError('Loan installment must be greater than zero.')
        if self.balance < 0:
            raise ValidationError('Loan balance cannot be negative.')
        if self.end_date < self.start_date:
            raise ValidationError('Loan end date cannot be before its start date.')
        if self.balance > self.principal + self.interest:
            raise ValidationError('Loan balance cannot exceed principal plus interest.')
        if self.employee_id and not self.employee.organization_id:
            raise ValidationError('Loan employee must belong to an organization.')

    @property
    def remaining_installments(self):
        if self.installment_amount <= 0:
            return 0
        return int((self.balance / self.installment_amount).to_integral_value(rounding='ROUND_CEILING'))
