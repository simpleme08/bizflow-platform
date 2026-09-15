from datetime import date
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.organization.models import Organization

from .models import PayrollRuleSet, PayrollWageRate


class PayrollConfidenceCommandTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Confidence Co", slug="confidence-co")

    def test_blocks_without_effective_provenance(self):
        output = StringIO()
        with self.assertRaises(Exception):
            call_command(
                "payroll_confidence_check",
                organization="confidence-co",
                as_of="2026-09-15",
                stdout=output,
            )
        self.assertIn("BLOCKED", output.getvalue())

    def test_ready_when_rule_and_wage_sources_exist(self):
        PayrollRuleSet.objects.create(
            organization=self.organization,
            version="PH-2026-09",
            effective_from=date(2026, 1, 1),
            source_name="Official payroll rules",
            source_url="https://example.gov/payroll",
            rules={"source_year": 2026},
        )
        PayrollWageRate.objects.create(
            organization=self.organization,
            region_code="NCR",
            category="NON_AGRICULTURE",
            daily_rate="695.00",
            effective_from=date(2026, 1, 1),
            wage_order="WO-TEST",
        )
        output = StringIO()
        call_command(
            "payroll_confidence_check",
            organization="confidence-co",
            as_of="2026-09-15",
            stdout=output,
        )
        self.assertIn("confidence-co: READY", output.getvalue())
