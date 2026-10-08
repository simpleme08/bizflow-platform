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
from apps.leave.models import EmployeeLeaveBalance, LeaveApplication, LeaveType
from apps.payroll.models import EmployeeSalary, PayrollPeriod, PayrollRecord


class Command(BaseCommand):
    help = "Seed a complete September 2026 inspection dataset on top of seed_demo."

    def handle(self, *args, **options):
        if not os.environ.get("BIZFLOW_DEMO_PASSWORD"):
            raise CommandError("Set BIZFLOW_DEMO_PASSWORD before running seed_inspection_demo.")

        # Inspection seeding is an explicit demo workflow. Always synchronize demo account passwords\n        # with the configured BIZFLOW_DEMO_PASSWORD so repeated runs cannot leave stale credentials.\n        previous_reset = os.environ.get("BIZFLOW_DEMO_RESET_PASSWORDS")\n        os.environ["BIZFLOW_DEMO_RESET_PASSWORDS"] = "true"\n        try:\n            call_command("seed_demo")\n        finally:\n            if previous_reset is None:\n                os.environ.pop("BIZFLOW_DEMO_RESET_PASSWORDS", None)\n            else:\n                os.environ["BIZFLOW_DEMO_RESET_PASSWORDS"] = previous_reset

        User = get_user_model()
        organization = Employee.objects.get(employee_number="EMP-000001").organization
        hr_user = User.objects.get(username="demo_hr")
        superuser = User.objects.get(username="demo_superuser")

        demo_employee = Employee.objects.get(employee_number="DEMO-EMPLOYEE")
        EmployeeSalary.objects.update_or_create(
            employee=demo_employee,
            defaults={"basic_salary": Decimal("30000.00"), "effective_date": date(2026, 1, 1)},
        )

        # Historical payroll: two completed August periods + completed first-half September.
        # The values are intentionally synthetic demo data and are not statutory calculations.
        period_specs = (
            (date(2026, 8, 1), date(2026, 8, 15), "August 1-15, 2026 — Paid", PayrollPeriod.Status.PAID),
            (date(2026, 8, 16), date(2026, 8, 31), "August 16-31, 2026 — Paid", PayrollPeriod.Status.PAID),
            (date(2026, 9, 1), date(2026, 9, 15), "September 1-15, 2026 — Paid", PayrollPeriod.Status.PAID),
            (date(2026, 9, 16), date(2026, 9, 30), "September 16-30, 2026 — Open", PayrollPeriod.Status.OPEN),
        )
        periods = {}
        for start_date, end_date, name, status in period_specs:
            defaults = {
                "name": name,
                "frequency": PayrollPeriod.Frequency.SEMI_MONTHLY,
                "status": status,
                "processed_by": hr_user,
                "confidence_status": "READY",
                "confidence_summary": {
                    "demo": True,
                    "synthetic": True,
                    "attendance_complete": True,
                },
            }
            if status == PayrollPeriod.Status.PAID:
                defaults["approved_by"] = superuser
                defaults["paid_by"] = superuser
            period, _ = PayrollPeriod.objects.update_or_create(
                organization=organization,
                start_date=start_date,
                end_date=end_date,
                defaults=defaults,
            )
            periods[(start_date, end_date)] = period

        employees = list(organization.employees.filter(is_active=True).select_related("user"))
        attendance_start = date(2026, 8, 1)
        attendance_end = date(2026, 9, 30)
        workdays = [
            attendance_start + timedelta(days=offset)
            for offset in range((attendance_end - attendance_start).days + 1)
            if (attendance_start + timedelta(days=offset)).weekday() < 5
        ]

        for employee in employees:
            # Keep annual leave balances populated and make approved demo leave visible.
            for leave_type in LeaveType.objects.filter(is_active=True):
                EmployeeLeaveBalance.objects.update_or_create(
                    employee=employee,
                    leave_type=leave_type,
                    year=2026,
                    defaults={
                        "credits": leave_type.annual_credits,
                        "used": Decimal("0.00"),
                    },
                )

            assignment = (
                employee.assignments.filter(start_date__lte=attendance_end)
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
                # Give the demo one realistic absence and one leave day without
                # making the entire attendance history incomplete.
                if employee.employee_number == "EMP-000006" and attendance_day == date(2026, 8, 14):
                    AttendanceRecord.objects.update_or_create(
                        employee=employee,
                        attendance_date=attendance_day,
                        segment_number=1,
                        defaults={
                            "assignment": assignment,
                            "clock_shift": shift,
                            "clock_in_mode": AttendanceRecord.ClockInMode.SCHEDULED,
                            "time_in": None,
                            "time_out": None,
                            "status": AttendanceRecord.Status.ABSENT,
                            "remarks": "Demo absence.",
                        },
                    )
                    continue

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
                        "remarks": "Demo historical attendance.",
                    },
                )
                AttendanceCalculator.update_record(record)

        # Generate payroll history for every active employee so Payroll History
        # has useful records immediately after seeding.
        for employee in employees:
            salary = getattr(employee, "salary", None)
            monthly = salary.basic_salary if salary else Decimal("30000.00")
            half = (monthly / Decimal("2")).quantize(Decimal("0.01"))
            for (start_date, end_date), period in periods.items():
                if period.status == PayrollPeriod.Status.OPEN:
                    status = PayrollRecord.Status.DRAFT
                else:
                    status = PayrollRecord.Status.PAID
                overtime = Decimal("500.00") if employee.employee_number in {"EMP-000001", "EMP-000007"} else Decimal("250.00")
                late = Decimal("100.00") if employee.employee_number in {"EMP-000001", "EMP-000003"} else Decimal("0.00")
                other = Decimal("200.00")
                gross = half + overtime
                statutory = Decimal("0.00")
                net = gross - late - other - statutory
                defaults = {
                    "basic_pay": half,
                    "overtime_pay": overtime,
                    "gross_pay": gross,
                    "late_deduction": late,
                    "other_deductions": other,
                    "net_pay": net,
                    "status": status,
                    "calculation_rule_version": "DEMO-2026",
                    "calculation_snapshot": {
                        "demo": True,
                        "synthetic": True,
                        "period": f"{start_date.isoformat()}:{end_date.isoformat()}",
                    },
                }
                existing = PayrollRecord.objects.filter(
                    employee=employee,
                    payroll_period=period,
                ).first()
                if existing is None:
                    PayrollRecord.objects.create(
                        employee=employee,
                        payroll_period=period,
                        **defaults,
                    )
                elif existing.status != PayrollRecord.Status.PAID or status != PayrollRecord.Status.PAID:
                    # Draft/open records may be refreshed. Approved/paid records are
                    # immutable financially; only lifecycle status may advance.
                    if existing.status == PayrollRecord.Status.PAID:
                        continue
                    if status == PayrollRecord.Status.PAID:
                        existing.status = PayrollRecord.Status.PAID
                        existing.save(update_fields=["status"])
                    else:
                        for field, value in defaults.items():
                            setattr(existing, field, value)
                        existing.save()

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

        # Historical leave examples: approved and rejected requests plus the three pending requests above.
        leave_examples = (
            ("EMP-000001", date(2026, 8, 10), date(2026, 8, 11), LeaveApplication.Status.APPROVED, "Family vacation — approved demo history."),
            ("EMP-000003", date(2026, 8, 24), date(2026, 8, 24), LeaveApplication.Status.REJECTED, "Personal appointment — rejected demo history."),
        )
        for employee_number, start, end, status, reason in leave_examples:
            employee = Employee.objects.get(employee_number=employee_number)
            application, _ = LeaveApplication.objects.update_or_create(
                employee=employee,
                leave_type=leave_type,
                start_date=start,
                end_date=end,
                defaults={
                    "total_days": Decimal((end - start).days + 1),
                    "reason": reason,
                    "status": status,
                    "approver": hr_user,
                    "approved_at": timezone.now(),
                    "remarks": "Demo historical workflow record.",
                },
            )
            if status == LeaveApplication.Status.APPROVED:
                EmployeeLeaveBalance.objects.update_or_create(
                    employee=employee,
                    leave_type=leave_type,
                    year=2026,
                    defaults={
                        "credits": leave_type.annual_credits,
                        "used": Decimal((end - start).days + 1),
                    },
                )

        self.stdout.write(self.style.SUCCESS(
            "Complete inspection demo ready: organization, SME/HR/manager/employee roles, employees, assignments, "
            f"{len(workdays)} historical workdays, leave balances/history, 3 paid payroll periods, "
            "and the current open payroll period."
        ))
