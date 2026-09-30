import os
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.attendance.models import AttendanceRecord
from apps.attendance.services import AttendanceCalculator
from apps.employees.models import Employee
from apps.leave.models import LeaveApplication, LeaveType
from apps.payroll.models import EmployeeSalary, PayrollPeriod, PayrollRecord


class Command(BaseCommand):
    help = "Seed a complete September 2026 inspection dataset on top of seed_demo."

    def handle(self, *args, **options):
        if not os.environ.get("BIZFLOW_DEMO_PASSWORD"):
            raise CommandError("Set BIZFLOW_DEMO_PASSWORD before running seed_inspection_demo.")

        call_command("seed_demo")

        User = get_user_model()
        organization = Employee.objects.get(employee_number="EMP-000001").organization
        hr_user = User.objects.get(username="demo_hr")
        superuser = User.objects.get(username="demo_superuser")

        demo_employee = Employee.objects.get(employee_number="DEMO-EMPLOYEE")
        EmployeeSalary.objects.update_or_create(
            employee=demo_employee,
            defaults={"basic_salary": Decimal("30000.00"), "effective_date": date(2026, 1, 1)},
        )

        approved_period, _ = PayrollPeriod.objects.update_or_create(
            organization=organization,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 15),
            defaults={
                "name": "September 1-15, 2026 — Approved",
                "frequency": PayrollPeriod.Frequency.SEMI_MONTHLY,
                "status": PayrollPeriod.Status.APPROVED,
                "processed_by": hr_user,
                "approved_by": superuser,
                "confidence_status": "READY",
                "confidence_summary": {"demo": True, "attendance_complete": True},
            },
        )
        draft_period, _ = PayrollPeriod.objects.update_or_create(
            organization=organization,
            start_date=date(2026, 9, 16),
            end_date=date(2026, 9, 30),
            defaults={
                "name": "September 16-30, 2026 — Draft",
                "frequency": PayrollPeriod.Frequency.SEMI_MONTHLY,
                "status": PayrollPeriod.Status.OPEN,
                "processed_by": hr_user,
                "confidence_status": "READY",
                "confidence_summary": {"demo": True, "attendance_complete": True},
            },
        )

        employees = list(organization.employees.filter(is_active=True).select_related("user"))
        workdays = [
            date(2026, 9, 1) + timedelta(days=offset)
            for offset in range(30)
            if (date(2026, 9, 1) + timedelta(days=offset)).weekday() < 5
        ]

        for employee in employees:
            assignment = (
                employee.assignments.filter(start_date__lte=date(2026, 9, 30))
                .filter(end_date__isnull=True)
                .select_related("shift_template")
                .order_by("-is_primary", "-start_date")
                .first()
            )
            if not assignment:
                continue
            shift = assignment.shift_template
            for attendance_day in workdays:
                start_dt = timezone.make_aware(datetime.combine(attendance_day, shift.start_time))
                end_day = attendance_day + timedelta(days=1) if shift.end_time <= shift.start_time else attendance_day
                end_dt = timezone.make_aware(datetime.combine(end_day, shift.end_time))
                late = 5 if employee.employee_number in {"EMP-000001", "EMP-000003"} and attendance_day.day % 5 == 0 else 0
                overtime = 30 if employee.employee_number == "EMP-000007" and attendance_day.day % 4 == 0 else 0
                record, _ = AttendanceRecord.objects.update_or_create(
                    employee=employee,
                    attendance_date=attendance_day,
                    segment_number=1,
                    defaults={
                        "assignment": assignment,
                        "clock_shift": shift,
                        "clock_in_mode": AttendanceRecord.ClockInMode.SCHEDULED,
                        "time_in": start_dt + timedelta(minutes=late),
                        "time_out": end_dt + timedelta(minutes=overtime),
                        "status": AttendanceRecord.Status.PRESENT,
                        "remarks": "Demo full-attendance dataset.",
                    },
                )
                AttendanceCalculator.update_record(record)

        for employee in employees:
            salary = getattr(employee, "salary", None)
            monthly = salary.basic_salary if salary else Decimal("30000.00")
            half = (monthly / Decimal("2")).quantize(Decimal("0.01"))
            for period in (approved_period, draft_period):
                status = PayrollRecord.Status.APPROVED if period == approved_period else PayrollRecord.Status.DRAFT
                PayrollRecord.objects.update_or_create(
                    employee=employee,
                    payroll_period=period,
                    defaults={
                        "basic_pay": half,
                        "overtime_pay": Decimal("500.00"),
                        "gross_pay": half + Decimal("500.00"),
                        "late_deduction": Decimal("100.00"),
                        "other_deductions": Decimal("200.00"),
                        "net_pay": half + Decimal("200.00"),
                        "status": status,
                    },
                )

        leave_type = LeaveType.objects.get(code="VL")
        pending_requests = (
            ("EMP-000001", date(2026, 10, 5), date(2026, 10, 6), "Family vacation — demo pending approval."),
            ("EMP-000003", date(2026, 10, 12), date(2026, 10, 13), "Personal leave — demo pending approval."),
            ("EMP-000005", date(2026, 10, 19), date(2026, 10, 19), "Personal appointment — demo pending approval."),
        )
        for employee_number, start, end, reason in pending_requests:
            employee = Employee.objects.get(employee_number=employee_number)
            days = Decimal((end - start).days + 1)
            LeaveApplication.objects.update_or_create(
                employee=employee,
                leave_type=leave_type,
                start_date=start,
                end_date=end,
                defaults={
                    "total_days": days,
                    "reason": reason,
                    "status": LeaveApplication.Status.PENDING,
                    "approver": None,
                    "approved_at": None,
                    "remarks": "",
                },
            )

        self.stdout.write(self.style.SUCCESS(
            "Inspection demo ready: approved Sep 1-15 payroll, draft Sep 16-30 payroll, "
            f"{len(workdays)} workdays of full attendance per active employee, and 3 pending leave requests."
        ))
