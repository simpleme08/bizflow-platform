from datetime import date
from decimal import Decimal

WAGE_CATEGORIES = {
    'NON_AGRICULTURE': 'Non-agriculture',
    'AGRICULTURE': 'Agriculture',
    'OTHER': 'Other wage category',
}

# NWPC reference snapshot. Ranges are retained where the official table has
# city/municipality or category differences; the engine must not guess a rate.
REGIONAL_WAGE_RATES = {
    'NCR': {'effective_from': date(2026, 7, 25), 'wage_order': 'NCR-27', 'NON_AGRICULTURE': (Decimal('718.00'), Decimal('755.00'))},
    'CAR': {'effective_from': date(2025, 12, 30), 'wage_order': 'CAR-24', 'NON_AGRICULTURE': (Decimal('505.00'), Decimal('505.00'))},
    'I': {'effective_from': date(2025, 11, 19), 'wage_order': 'RB1-24', 'NON_AGRICULTURE': (Decimal('480.00'), Decimal('505.00'))},
    'II': {'effective_from': date(2025, 11, 5), 'wage_order': 'RTWPB-2-24', 'NON_AGRICULTURE': (Decimal('500.00'), Decimal('500.00'))},
    'III': {'effective_from': date(2026, 4, 16), 'wage_order': 'RBIII-26', 'NON_AGRICULTURE': (Decimal('515.00'), Decimal('600.00'))},
    'IVA': {'effective_from': date(2026, 4, 1), 'wage_order': 'IVA-22', 'NON_AGRICULTURE': (Decimal('508.00'), Decimal('600.00'))},
    'IVB': {'effective_from': date(2026, 1, 1), 'wage_order': 'RB-MIMAROPA-13', 'NON_AGRICULTURE': (Decimal('455.00'), Decimal('455.00'))},
    'V': {'effective_from': date(2026, 4, 8), 'wage_order': 'RBV-23', 'NON_AGRICULTURE': (Decimal('455.00'), Decimal('455.00'))},
    'VI': {'effective_from': date(2025, 11, 19), 'wage_order': 'RBVI-29', 'NON_AGRICULTURE': (Decimal('520.00'), Decimal('550.00'))},
    'VII': {'effective_from': date(2025, 10, 4), 'wage_order': 'ROVII-26', 'NON_AGRICULTURE': (Decimal('500.00'), Decimal('540.00'))},
    'VIII': {'effective_from': date(2026, 6, 1), 'wage_order': 'RBVIII-25', 'NON_AGRICULTURE': (Decimal('440.00'), Decimal('470.00'))},
    'IX': {'effective_from': date(2026, 6, 1), 'wage_order': 'RIX-24', 'NON_AGRICULTURE': (Decimal('451.00'), Decimal('464.00'))},
    'X': {'effective_from': date(2026, 5, 1), 'wage_order': 'RX-24', 'NON_AGRICULTURE': (Decimal('485.00'), Decimal('500.00'))},
    'XI': {'effective_from': date(2026, 9, 1), 'wage_order': 'RB XI-24', 'NON_AGRICULTURE': (Decimal('525.00'), Decimal('540.00'))},
    'XII': {'effective_from': date(2025, 12, 15), 'wage_order': 'RXII-25', 'NON_AGRICULTURE': (Decimal('443.00'), Decimal('460.00'))},
    'XIII': {'effective_from': date(2026, 5, 1), 'wage_order': 'RXIII-20', 'NON_AGRICULTURE': (Decimal('475.00'), Decimal('475.00'))},
    'BARMM': {'effective_from': date(2026, 8, 6), 'wage_order': 'BARMM-05', 'NON_AGRICULTURE': (Decimal('401.00'), Decimal('436.00'))},
}


def regional_wage_reference(region_code, category='NON_AGRICULTURE', as_of=None):
    as_of = as_of or date.today()
    region = REGIONAL_WAGE_RATES.get(region_code.upper())
    if not region or as_of < region['effective_from']:
        return None
    rate_range = region.get(category)
    if not rate_range:
        return None
    minimum, maximum = rate_range
    return {
        'region_code': region_code.upper(),
        'category': category,
        'minimum_daily_rate': minimum,
        'maximum_daily_rate': maximum,
        'wage_order': region['wage_order'],
        'effective_from': region['effective_from'],
        'exact_rate_available': minimum == maximum,
    }


def is_mwe_candidate(daily_wage, region_code, category='NON_AGRICULTURE', as_of=None):
    reference = regional_wage_reference(region_code, category, as_of)
    if not reference or not reference['exact_rate_available']:
        return False
    return Decimal(daily_wage) <= reference['minimum_daily_rate']
