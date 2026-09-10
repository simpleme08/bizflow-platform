from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from .wage_config import is_mwe_candidate, regional_wage_reference


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
