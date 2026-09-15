from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.employees.models import Employee
from apps.organization.models import Organization
from apps.payroll.models import PayrollPeriod, PayrollRecord
from apps.payroll.reconciliation import PayrollReconciliation


class PayrollReconciliationTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Reconciliation Test", slug="reconciliation-test")

        self.period = PayrollPeriod.objects.create(
            organization=self.organization,
            name="September 1-15",
            start_date="2026-09-01",
            end_date="2026-09-15",
        )

    def make_employee(self, number="REC-001"):
        user = get_user_model().objects.create_user(
            username=f"{number.lower()}@example.test",
            password="test-password",
        )
        return Employee.objects.create(
            organization=self.organization,
            employee_number=number,
            user=user,
            first_name="Test",
            last_name="Employee",
        )

    def test_empty_period_is_not_consistent_with_active_population(self):
        self.make_employee()
        result = PayrollReconciliation.validate(self.period)
        self.assertFalse(result["ok"])
        self.assertTrue(any("record count" in error for error in result["errors"]))

    def test_record_totals_reconcile_to_net_pay(self):
        employee = self.make_employee()
        PayrollRecord.objects.create(
            employee=employee,
            payroll_period=self.period,
            gross_pay=Decimal("10000.00"),
            sss_employee=Decimal("250.00"),
            philhealth_employee=Decimal("250.00"),
            pagibig_employee=Decimal("100.00"),
            withholding_tax=Decimal("400.00"),
            net_pay=Decimal("9000.00"),
        )
        result = PayrollReconciliation.validate(self.period)
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["totals"]["net_pay"], Decimal("9000.00"))
