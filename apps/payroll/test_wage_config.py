from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from .wage_config import is_mwe_candidate, mwe_tax_exempt_income, regional_wage_reference


class RegionalWageReferenceTests(SimpleTestCase):
    def test_uniform_rate_can_be_used_for_mwe_candidate_check(self):
        reference = regional_wage_reference('CAR', as_of=date(2026, 9, 10))
        self.assertTrue(reference['exact_rate_available'])
        self.assertEqual(reference['minimum_daily_rate'], Decimal('505.00'))
        self.assertTrue(is_mwe_candidate(Decimal('505.00'), 'CAR', as_of=date(2026, 9, 10)))

    def test_rate_range_does_not_guess_exact_local_mwe_rate(self):
        reference = regional_wage_reference('NCR', as_of=date(2026, 9, 10))
        self.assertFalse(reference['exact_rate_available'])
        self.assertFalse(is_mwe_candidate(Decimal('718.00'), 'NCR', as_of=date(2026, 9, 10)))

    def test_mwe_exempt_income_requires_exact_rate_and_includes_qualifying_premiums(self):
        exempt = mwe_tax_exempt_income(
            daily_wage=Decimal('505.00'), days_worked=10,
            regular_pay=Decimal('5050.00'), overtime_pay=Decimal('100.00'),
            holiday_pay=Decimal('200.00'), night_differential=Decimal('50.00'),
            region_code='CAR', as_of=date(2026, 9, 10),
        )
        self.assertEqual(exempt, Decimal('5400.00'))

    def test_mwe_exempt_income_is_zero_without_exact_local_rate(self):
        exempt = mwe_tax_exempt_income(
            daily_wage=Decimal('718.00'), days_worked=10,
            regular_pay=Decimal('7180.00'), region_code='NCR',
            as_of=date(2026, 9, 10),
        )
        self.assertEqual(exempt, Decimal('0.00'))
