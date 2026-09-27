import csv
import hashlib
from io import StringIO
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import PayrollPeriod, PayrollRecord


def build_bank_disbursement_csv(period):
    """Build a customer-uploadable CSV from approved/paid payroll records only.

    This deliberately does not submit funds to a bank. The customer remains the
    final approver and uploader in the bank portal.
    """
    records = list(
        PayrollRecord.objects.filter(
            payroll_period=period,
            employee__organization=period.organization,
            status__in=(PayrollRecord.Status.APPROVED, PayrollRecord.Status.PAID),
        ).select_related('employee', 'employee__payroll_profile').order_by('employee__employee_number')
    )
    missing = []
    rows = []
    for record in records:
        profile = getattr(record.employee, 'payroll_profile', None)
        if not profile or not profile.bank_account_number or not profile.bank_account_name:
            missing.append(record.employee.employee_number)
            continue
        rows.append([
            profile.bank_name,
            profile.bank_account_name,
            profile.bank_account_number,
            f'{record.net_pay:.2f}',
            record.employee.employee_number,
            period.name,
        ])
    if missing:
        raise ValueError(f'Missing bank payout details for employee(s): {", ".join(missing)}')
    if not rows:
        raise ValueError('No approved or paid payroll records are available for disbursement.')
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['Bank Name', 'Account Name', 'Account Number', 'Amount', 'Employee Number', 'Payroll Period'])
    writer.writerows(rows)
    payload = buffer.getvalue()
    return payload, hashlib.sha256(payload.encode('utf-8')).hexdigest(), len(rows), sum((Decimal(row[3]) for row in rows), Decimal('0.00'))


@transaction.atomic
def prepare_bank_disbursement(period, actor):
    if period.organization_id != getattr(actor, 'organization_id', None):
        raise ValueError('Payroll period and actor organization do not match.')
    if period.status not in (PayrollPeriod.Status.APPROVED, PayrollPeriod.Status.PAID):
        raise ValueError('Payroll must be approved before a bank disbursement file can be prepared.')
    payload, digest, count, total = build_bank_disbursement_csv(period)
    return {
        'filename': f'bank-disbursement-{period.end_date:%Y-%m-%d}.csv',
        'content': payload,
        'sha256': digest,
        'record_count': count,
        'total_net_pay': str(total),
        'prepared_at': timezone.now().isoformat(),
        'status': 'READY_FOR_BANK_UPLOAD',
    }
