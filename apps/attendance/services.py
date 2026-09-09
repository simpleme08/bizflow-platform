from datetime import datetime, timedelta

from django.utils import timezone

from .models import AttendanceRecord


class AttendanceCalculator:
    @staticmethod
    def calculate(record):
        if not record.assignment_id or not record.assignment.shift_template_id:
            return {'late_minutes': 0, 'undertime_minutes': 0, 'overtime_minutes': 0}
        if not record.time_in or not record.time_out:
            return {'late_minutes': 0, 'undertime_minutes': 0, 'overtime_minutes': 0}

        shift = record.assignment.shift_template
        scheduled_start = timezone.make_aware(datetime.combine(record.attendance_date, shift.start_time))
        scheduled_end = timezone.make_aware(datetime.combine(record.attendance_date, shift.end_time))
        if shift.end_time <= shift.start_time:
            scheduled_end += timedelta(days=1)

        late = max(0, int((record.time_in - scheduled_start).total_seconds() // 60))
        undertime = max(0, int((scheduled_end - record.time_out).total_seconds() // 60))
        overtime = max(0, int((record.time_out - scheduled_end).total_seconds() // 60))
        return {
            'late_minutes': late,
            'undertime_minutes': undertime,
            'overtime_minutes': overtime,
        }

    @classmethod
    def update_record(cls, record):
        metrics = cls.calculate(record)
        AttendanceRecord.objects.filter(pk=record.pk).update(**metrics)
        for field, value in metrics.items():
            setattr(record, field, value)
        return record