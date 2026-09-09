from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from apps.core.models import BaseModel
from apps.employees.models import Employee


class LeaveType(BaseModel):
	name = models.CharField(max_length=100, unique=True)
	code = models.CharField(max_length=20, unique=True)
	annual_credits = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
	is_paid = models.BooleanField(default=True)
	is_active = models.BooleanField(default=True)

	class Meta:
		constraints = [models.UniqueConstraint(fields=('code',), name='unique_leave_type_code')]

	def __str__(self):
		return f'{self.code} - {self.name}'


class EmployeeLeaveBalance(BaseModel):
	employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_balances')
	leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name='balances')
	year = models.PositiveIntegerField()
	credits = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
	used = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))

	class Meta:
		constraints = [models.UniqueConstraint(fields=('employee', 'leave_type', 'year'), name='unique_employee_leave_balance')]

	@property
	def remaining(self):
		return max(Decimal('0.00'), self.credits - self.used)


class LeaveApplication(BaseModel):
	class Status(models.TextChoices):
		PENDING = 'PENDING', 'Pending'
		APPROVED = 'APPROVED', 'Approved'
		REJECTED = 'REJECTED', 'Rejected'
		CANCELLED = 'CANCELLED', 'Cancelled'

	employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_applications')
	leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name='applications')
	start_date = models.DateField()
	end_date = models.DateField()
	total_days = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
	reason = models.TextField()
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
	approver = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_leave_applications')
	approved_at = models.DateTimeField(null=True, blank=True)
	remarks = models.TextField(blank=True)

	class Meta:
		ordering = ('-created_at',)

	def clean(self):
		if self.end_date < self.start_date:
			raise ValidationError('End date cannot be earlier than start date.')
		if self.total_days <= 0:
			raise ValidationError('Leave duration must be greater than zero.')

	def approve(self, approver):
		if self.status != self.Status.PENDING:
			raise ValidationError('Only pending leave applications can be approved.')
		with transaction.atomic():
			balance, _ = EmployeeLeaveBalance.objects.select_for_update().get_or_create(
				employee=self.employee,
				leave_type=self.leave_type,
				year=self.start_date.year,
				defaults={'credits': self.leave_type.annual_credits},
			)
			if balance.remaining < self.total_days:
				raise ValidationError('The employee does not have enough leave balance to approve this request.')
			balance.used += self.total_days
			balance.save(update_fields=('used', 'updated_at'))
			self.status = self.Status.APPROVED
			self.approver = approver
			self.approved_at = timezone.now()
			self.save(update_fields=('status', 'approver', 'approved_at', 'updated_at'))

	def reject(self, approver, remarks=''):
		if self.status != self.Status.PENDING:
			raise ValidationError('Only pending leave applications can be rejected.')
		self.status = self.Status.REJECTED
		self.approver = approver
		self.remarks = remarks
		self.approved_at = timezone.now()
		self.save(update_fields=('status', 'approver', 'remarks', 'approved_at', 'updated_at'))
