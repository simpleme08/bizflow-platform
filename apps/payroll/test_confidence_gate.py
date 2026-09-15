from datetime import date

from django.test import TestCase

from apps.organization.models import Organization

from .confidence import PayrollConfidenceGate
from .models import PayrollPeriod, PayrollRuleSet, PayrollWageRate


class PayrollConfidenceGateTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Confidence Co", slug="confidence-co")
        self.period = PayrollPeriod(
            organization=self.organization,
            name="August 2026",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 15),
        )

    def test_missing_rule_set_blocks(self):
        status, summary, selected = PayrollConfidenceGate.evaluate(self.organization, self.period)
        self.assertEqual(status, "BLOCKED")
        self.assertIsNone(selected)
        self.assertTrue(summary["errors"])

    def test_organization_rule_set_takes_precedence_over_global(self):
        PayrollRuleSet.objects.create(
            version="global-2026",
            effective_from=date(2026, 1, 1),
            source_name="Global source",
            source_url="https://example.com/global",
        )
        organization_rule = PayrollRuleSet.objects.create(
            organization=self.organization,
            version="org-2026",
            effective_from=date(2026, 7, 1),
            source_name="Organization source",
            source_url="https://example.com/org",
        )
        status, summary, selected = PayrollConfidenceGate.evaluate(self.organization, self.period)
        self.assertEqual(status, "READY")
        self.assertEqual(selected, organization_rule)
        self.assertEqual(summary["rule_set_version"], "org-2026")

    def test_expired_rule_set_does_not_pass(self):
        PayrollRuleSet.objects.create(
            organization=self.organization,
            version="expired",
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 7, 31),
            source_name="Old source",
            source_url="https://example.com/old",
        )
        status, _, _ = PayrollConfidenceGate.evaluate(self.organization, self.period)
        self.assertEqual(status, "BLOCKED")

    def test_wage_table_is_ready_when_configured(self):
        PayrollRuleSet.objects.create(
            organization=self.organization,
            version="2026.1",
            effective_from=date(2026, 1, 1),
            source_name="Official rules",
            source_url="https://example.com/rules",
        )
        PayrollWageRate.objects.create(
            organization=self.organization,
            region_code="NCR",
            category="NON_AGRICULTURE",
            daily_rate="700.00",
            effective_from=date(2026, 1, 1),
        )
        status, summary, selected = PayrollConfidenceGate.evaluate(self.organization, self.period)
        self.assertEqual(status, "READY")
        self.assertEqual(selected.version, "2026.1")
        self.assertFalse(summary["errors"])
