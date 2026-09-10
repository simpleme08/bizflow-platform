from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel
from apps.employees.models import Employee, EmployeeAssignment


class AttendanceRecord(BaseModel):
    class Status(models.TextChoices):
        PRESENT = 'PRESENT', 'Present'
        ABSENT = 'ABSENT', 'Absent'
        LEAVE = 'LEAVE', 'Leave'
        HOLIDAY = 'HOLIDAY', 'Holiday'

    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='attendance_records')
    assignment = models.ForeignKey(EmployeeAssignment, on_delete=models.PROTECT, related_name='attendance_records')
    attendance_date = models.DateField()
    time_in = models.DateTimeField(null=True, blank=True)
    time_out = models.DateTimeField(null=True, blank=True)
    clock_in_photo = models.ImageField(upload_to='attendance/proofs/%Y/%m/%d/', null=True, blank=True)
    clock_out_photo = models.ImageField(upload_to='attendance/proofs/%Y/%m/%d/', null=True, blank=True)
    late_minutes = models.PositiveIntegerField(default=0)
    undertime_minutes = models.PositiveIntegerField(default=0)
    overtime_minutes = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PRESENT)
    remarks = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('employee', 'attendance_date'),
                name='unique_employee_attendance_date',
            ),
        ]
        ordering = ('-attendance_date',)

    def clean(self):
        if self.assignment_id and self.assignment.employee_id != self.employee_id:
            raise ValidationError('The assignment must belong to the selected employee.')
        if self.time_in and timezone.localtime(self.time_in).date() != self.attendance_date:
            raise ValidationError('Time in must use the attendance date in Asia/Manila.')
        if self.time_in and self.time_out and self.time_out <= self.time_in:
            raise ValidationError('Time out must be later than time in.')
        if self.time_out and self.assignment_id:
            time_out_date = timezone.localtime(self.time_out).date()
            is_overnight = self.assignment.shift_template.end_time <= self.assignment.shift_template.start_time
            allowed_date = self.attendance_date + timedelta(days=1) if is_overnight else self.attendance_date
            if time_out_date != allowed_date:
                raise ValidationError('Time out must match the shift date or the following day for overnight shifts.')

    @property
    def hours_worked(self):
        if not self.time_in or not self.time_out:
            return None
        return self.time_out - self.time_in

    def __str__(self):
        return f'{self.employee} - {self.attendance_date}'
