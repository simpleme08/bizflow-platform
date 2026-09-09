import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
	initial = True
	dependencies = [('employees', '0002_employee_organization'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
	operations = [
		migrations.CreateModel(name='LeaveType', fields=[('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)), ('name', models.CharField(max_length=100)), ('code', models.CharField(max_length=20)), ('annual_credits', models.DecimalField(decimal_places=2, default=0.0, max_digits=6)), ('is_paid', models.BooleanField(default=True)), ('is_active', models.BooleanField(default=True))]),
		migrations.CreateModel(name='EmployeeLeaveBalance', fields=[('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)), ('year', models.PositiveIntegerField()), ('credits', models.DecimalField(decimal_places=2, default=0.0, max_digits=6)), ('used', models.DecimalField(decimal_places=2, default=0.0, max_digits=6)), ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='leave_balances', to='employees.employee')), ('leave_type', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='balances', to='leave.leavetype'))]),
		migrations.CreateModel(name='LeaveApplication', fields=[('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)), ('start_date', models.DateField()), ('end_date', models.DateField()), ('total_days', models.DecimalField(decimal_places=2, default=0.0, max_digits=6)), ('reason', models.TextField()), ('status', models.CharField(choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('CANCELLED', 'Cancelled')], default='PENDING', max_length=20)), ('approved_at', models.DateTimeField(blank=True, null=True)), ('remarks', models.TextField(blank=True)), ('approver', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_leave_applications', to=settings.AUTH_USER_MODEL)), ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='leave_applications', to='employees.employee')), ('leave_type', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='applications', to='leave.leavetype'))]),
		migrations.AddConstraint(model_name='leavetype', constraint=models.UniqueConstraint(fields=('code',), name='unique_leave_type_code')),
		migrations.AddConstraint(model_name='employeeleavebalance', constraint=models.UniqueConstraint(fields=('employee', 'leave_type', 'year'), name='unique_employee_leave_balance')),
	]