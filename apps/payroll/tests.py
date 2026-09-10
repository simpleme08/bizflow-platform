from datetime import date, datetime, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.attendance.models import AttendanceRecord
from apps.employees.models import Employee, EmployeeAssignment
from apps.leave.models import LeaveApplication, LeaveType
from apps.organization.models import Organization, OrganizationMembership
from apps.workforce.models import ShiftTemplate

from .models import EmployeeSalary, PayrollHoliday, PayrollPeriod, PayrollRecord
from .services import PhilippinePayrollRules, PhilippineWithholdingTax, PayrollCalculator


class PayrollCalculatorTests(TestCase):
    def setUp(self):
        self.manager = get_user_model().objects.create_user(username='payroll-manager', password='password')
        organization = Organization.objects.create(name='Acme', slug='acme')
        OrganizationMembership.objects.create(organization=organization, user=self.manager, role=OrganizationMembership.Role.HR)
        employee_user = get_user_model().objects.create_user(username='payroll-employee', password='password')
        self.employee = Employee.objects.create(employee_number='EMP-100', user=employee_user, organization=organization, first_name='Ana', last_name='Reyes')
        shift = ShiftTemplate.objects.create(name='Payroll Shift', start_time=time(8), end_time=time(17))
        assignment = EmployeeAssignment.objects.create(employee=self.employee, shift_template=shift, start_date=date(2026, 1, 1), is_primary=True)
        AttendanceRecord.objects.create(employee=self.employee, assignment=assignment, attendance_date=date(2026, 8, 10), time_in=timezone.make_aware(datetime(2026, 8, 10, 8, 15)), time_out=timezone.make_aware(datetime(2026, 8, 10, 17, 30)), late_minutes=15, overtime_minutes=30)
        EmployeeSalary.objects.create(employee=self.employee, basic_salary=Decimal('20000.00'), effective_date=date(2026, 1, 1))
        self.period = PayrollPeriod.objects.create(organization=organization, name='August 1-15, 2026', start_date=date(2026, 8, 1), end_date=date(2026, 8, 15))

    def test_statutory_rules_match_current_schedules(self):
        self.assertEqual(PhilippinePayrollRules.sss(Decimal('20000.00')), (Decimal('1000.00'), Decimal('2030.00')))
        self.assertEqual(PhilippinePayrollRules.philhealth(Decimal('20000.00')), (Decimal('500.00'), Decimal('500.00')))
        self.assertEqual(PhilippinePayrollRules.pagibig(Decimal('20000.00')), (Decimal('100.00'), Decimal('100.00')))

    def test_withholding_tax_uses_bir_tables(self):
        self.assertEqual(PhilippineWithholdingTax.calculate(Decimal('10417.00')), Decimal('0.00'))
        self.assertEqual(PhilippineWithholdingTax.calculate(Decimal('12000.00')), Decimal('237.45'))
        self.assertEqual(PhilippineWithholdingTax.calculate(Decimal('40000.00')), Decimal('5937.45'))
        self.assertEqual(PhilippineWithholdingTax.calculate(Decimal('20833.00'), frequency='MONTHLY'), Decimal('0.00'))
        self.assertEqual(PhilippineWithholdingTax.calculate(Decimal('25000.00'), frequency='MONTHLY'), Decimal('625.05'))

    def test_calculator_returns_exact_decimal_components(self):
        result = PayrollCalculator.calculate(self.employee, self.period)
        self.assertEqual(result['basic_pay'], Decimal('10000.00'))
        self.assertEqual(result['overtime_pay'], Decimal('71.02'))
        self.assertEqual(result['late_deduction'], Decimal('28.41'))
        self.assertEqual(result['sss_employee'], Decimal('500.00'))
        self.assertEqual(result['sss_employer'], Decimal('1015.00'))
        self.assertEqual(result['philhealth_employee'], Decimal('250.00'))
        self.assertEqual(result['philhealth_employer'], Decimal('250.00'))
        self.assertEqual(result['pagibig_employee'], Decimal('50.00'))
        self.assertEqual(result['pagibig_employer'], Decimal('50.00'))
        self.assertEqual(result['gross_pay'], Decimal('10071.02'))
        self.assertEqual(result['net_pay'], Decimal('9242.61'))

    def test_night_differential_is_based_on_actual_hours_between_10pm_and_6am(self):
        assignment = self.employee.assignments.first()
        AttendanceRecord.objects.create(
            employee=self.employee,
            assignment=assignment,
            attendance_date=date(2026, 8, 11),
            time_in=timezone.make_aware(datetime(2026, 8, 11, 21, 0)),
            time_out=timezone.make_aware(datetime(2026, 8, 11, 23, 0)),
        )
        result = PayrollCalculator.calculate(self.employee, self.period)
        self.assertEqual(result['night_differential'], Decimal('11.36'))

    def test_regular_holiday_work_adds_the_holiday_premium(self):
        assignment = self.employee.assignments.first()
        AttendanceRecord.objects.create(
            employee=self.employee,
            assignment=assignment,
            attendance_date=date(2026, 8, 11),
            time_in=timezone.make_aware(datetime(2026, 8, 11, 8, 0)),
            time_out=timezone.make_aware(datetime(2026, 8, 11, 17, 0)),
        )
        PayrollHoliday.objects.create(
            organization=self.employee.organization,
            holiday_date=date(2026, 8, 11),
            name='Test Regular Holiday',
            kind=PayrollHoliday.Kind.REGULAR,
        )
        result = PayrollCalculator.calculate(self.employee, self.period)
        self.assertEqual(result['holiday_pay'], Decimal('909.09'))

    def test_approved_unpaid_leave_is_automatically_deducted(self):
        leave_type = LeaveType.objects.create(name='Unpaid Leave', code='UL', annual_credits=Decimal('10.00'), is_paid=False)
        LeaveApplication.objects.create(
            employee=self.employee,
            leave_type=leave_type,
            start_date=date(2026, 8, 12),
            end_date=date(2026, 8, 12),
            total_days=Decimal('1.00'),
            reason='Test unpaid leave',
            status=LeaveApplication.Status.APPROVED,
        )
        result = PayrollCalculator.calculate(self.employee, self.period)
        self.assertEqual(result['leave_without_pay'], Decimal('909.09'))

    def test_monthly_period_uses_monthly_salary_and_contributions(self):
        monthly_period = PayrollPeriod.objects.create(organization=self.employee.organization, name='August 2026 Monthly', start_date=date(2026, 8, 1), end_date=date(2026, 8, 31), frequency=PayrollPeriod.Frequency.MONTHLY)
        result = PayrollCalculator.calculate(self.employee, monthly_period)
        self.assertEqual(result['basic_pay'], Decimal('20000.00'))
        self.assertEqual(result['sss_employee'], Decimal('1000.00'))
        self.assertEqual(result['sss_employer'], Decimal('2030.00'))
        self.assertEqual(result['philhealth_employee'], Decimal('500.00'))
        self.assertEqual(result['pagibig_employee'], Decimal('100.00'))
        self.assertEqual(result['withholding_tax'], Decimal('0.00'))

    def test_thirteenth_month_is_one_twelfth_of_basic_pay_paid(self):
        PayrollCalculator.process_period(self.period, self.employee.organization)
        self.assertEqual(PayrollCalculator.thirteenth_month(self.employee, 2026), Decimal('833.33'))

    def test_preflight_reports_missing_profile_as_warning(self):
        result = PayrollCalculator.preflight(self.period, self.employee.organization)
        self.assertTrue(result['ok'])
        self.assertTrue(any('payroll profile' in warning for warning in result['warnings']))

    def test_process_period_creates_calculated_record(self):
        self.assertEqual(PayrollCalculator.process_period(self.period, self.employee.organization), 1)
        record = PayrollRecord.objects.get(employee=self.employee, payroll_period=self.period)
        self.assertEqual(record.status, PayrollRecord.Status.DRAFT)
        self.assertEqual(record.net_pay, Decimal('9242.61'))
        self.period.refresh_from_db()
        self.assertEqual(self.period.status, PayrollPeriod.Status.CALCULATED)

    def test_approved_period_cannot_be_recalculated(self):
        PayrollCalculator.process_period(self.period, self.employee.organization)
        self.period.refresh_from_db()
        self.period.status = PayrollPeriod.Status.APPROVED
        self.period.save(update_fields=('status', 'updated_at'))
        with self.assertRaises(ValueError):
            PayrollCalculator.process_period(self.period, self.employee.organization)

    def test_cross_organization_processing_is_rejected(self):
        other_org = Organization.objects.create(name='Other Co', slug='other-co')
        other_period = PayrollPeriod.objects.create(organization=other_org, name='Other Period', start_date=date(2026, 8, 1), end_date=date(2026, 8, 15))
        with self.assertRaises(Exception):
            PayrollCalculator.process_period(other_period, self.employee.organization)

    def test_employee_can_download_only_approved_payslip(self):
        PayrollCalculator.process_period(self.period, self.employee.organization)
        record = PayrollRecord.objects.get(employee=self.employee, payroll_period=self.period)
        record.status = PayrollRecord.Status.APPROVED
        record.save(update_fields=('status', 'updated_at'))
        self.client.login(username='payroll-employee', password='password')
        response = self.client.get(f'/api/payroll/{record.id}/payslip/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))
