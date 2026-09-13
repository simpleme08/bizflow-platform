import hashlib
import json
from decimal import Decimal

from django.db import transaction

from apps.attendance.models import AttendanceRecord

from .models import PayrollRecord, PayrollRuleSet
from .services import PayrollCalculator, PhilippinePayrollRules, PhilippineWithholdingTax


class PayrollConfidence:
    """Production guardrails around the legacy calculator.

    The existing calculator remains the executable engine. This layer makes each run
    explainable, effective-dated and tamper-evident without changing its public API.
    """

    @staticmethod
    def _hash(payload):
        encoded = json.dumps(payload, sort_keys=True, separators=(',', ':'), default=str).encode('utf-8')
        return hashlib.sha256(encoded).hexdigest()

    @classmethod
    def rule_set_for(cls, period, organization):
        return (
            PayrollRuleSet.objects.filter(
                is_active=True,
                organization=organization,
                effective_from__lte=period.end_date,
            )
            .filter(models_q_effective_to(period.end_date))
            .order_by('-effective_from', '-created_at')
            .first()
            or PayrollRuleSet.objects.filter(
                is_active=True,
                organization__isnull=True,
                effective_from__lte=period.end_date,
            )
            .filter(models_q_effective_to(period.end_date))
            .order_by('-effective_from', '-created_at')
            .first()
        )

    @classmethod
    def preflight(cls, period, organization):
        result = PayrollCalculator.preflight(period, organization)
        rule_set = cls.rule_set_for(period, organization)
        errors = list(result.get('errors', []))
        warnings = list(result.get('warnings', []))
        if rule_set is None:
            errors.append('No effective payroll rule set with source provenance is configured for this period.')
        else:
            warnings.append(f'Rule set {rule_set.version} is recorded for provenance; verify agency schedules before production use.')
        if errors:
            confidence = 'BLOCKED'
        elif warnings:
            confidence = 'REVIEW'
        else:
            confidence = 'READY'
        result.update({'confidence': confidence, 'rule_set': rule_set.version if rule_set else None, 'errors': errors, 'warnings': warnings})
        return result

    @classmethod
    def _apply_absence_deductions(cls, period, organization):
        records = PayrollRecord.objects.filter(
            payroll_period=period,
            employee__organization=organization,
            status=PayrollRecord.Status.DRAFT,
        ).select_related('employee', 'employee__salary', 'employee__payroll_profile')
        changed = 0
        for record in records:
            absent = AttendanceRecord.objects.filter(
                employee=record.employee,
                attendance_date__range=(period.start_date, period.end_date),
                status=AttendanceRecord.Status.ABSENT,
            ).order_by('attendance_date')
            absent_days = absent.count()
            if not absent_days:
                continue
            salary = PayrollCalculator._salary_for_period(record.employee, period)
            if salary is None:
                continue
            deduction = PhilippinePayrollRules.money((salary.basic_salary / PayrollCalculator.WORKING_DAYS) * Decimal(absent_days))
            existing_absence = Decimal(record.calculation_snapshot.get('absence_deduction', '0.00')) if record.calculation_snapshot else Decimal('0.00')
            incremental = deduction - existing_absence
            if incremental <= 0:
                continue
            record.basic_pay = PhilippinePayrollRules.money(max(Decimal('0.00'), record.basic_pay - incremental))
            record.gross_pay = PhilippinePayrollRules.money(max(Decimal('0.00'), record.gross_pay - incremental))
            record.other_deductions = PhilippinePayrollRules.money(record.other_deductions)
            statutory = record.statutory_deductions
            taxable_regular = PhilippinePayrollRules.money(record.basic_pay + record.allowances - statutory)
            withholding = PhilippineWithholdingTax.calculate(
                max(Decimal('0.00'), taxable_regular + record.taxable_supplementary),
                period.frequency,
            )
            record.withholding_tax = withholding
            record.net_pay = PhilippinePayrollRules.money(
                record.gross_pay
                - record.late_deduction
                - record.undertime_deduction
                - record.leave_without_pay
                - record.loan_deductions
                - record.statutory_deductions
                - record.withholding_tax
                - record.other_deductions
            )
            record.calculation_snapshot = dict(record.calculation_snapshot or {})
            record.calculation_snapshot['absence_deduction'] = str(deduction)
            record.calculation_snapshot['absent_days'] = absent_days
            record.calculation_snapshot['absent_dates'] = [item.attendance_date.isoformat() for item in absent]
            record.save()
            changed += 1
        return changed

    @classmethod
    def _record_provenance(cls, period, organization):
        rule_set = cls.rule_set_for(period, organization)
        for record in PayrollRecord.objects.filter(payroll_period=period, employee__organization=organization):
            attendance = AttendanceRecord.objects.filter(
                employee=record.employee,
                attendance_date__range=(period.start_date, period.end_date),
            ).order_by('attendance_date', 'id')
            salary = PayrollCalculator._salary_for_period(record.employee, period)
            snapshot = {
                'employee_id': str(record.employee_id),
                'period_id': str(period.id),
                'period': [period.start_date.isoformat(), period.end_date.isoformat()],
                'salary': str(salary.basic_salary) if salary else None,
                'attendance': [
                    {
                        'id': str(item.id),
                        'date': item.attendance_date.isoformat(),
                        'status': item.status,
                        'time_in': item.time_in.isoformat() if item.time_in else None,
                        'time_out': item.time_out.isoformat() if item.time_out else None,
                        'overtime_minutes': item.overtime_minutes,
                        'late_minutes': item.late_minutes,
                        'undertime_minutes': item.undertime_minutes,
                    }
                    for item in attendance
                ],
                'rule_set': rule_set.version if rule_set else None,
                'rule_payload_hash': cls._hash(rule_set.rules if rule_set else {}),
                'absence_deduction': record.calculation_snapshot.get('absence_deduction') if record.calculation_snapshot else None,
            }
            output = {
                field: str(getattr(record, field))
                for field in (
                    'basic_pay', 'overtime_pay', 'holiday_pay', 'night_differential', 'allowances',
                    'commissions', 'bonuses', 'taxable_supplementary', 'thirteenth_month',
                    'sss_employee', 'philhealth_employee', 'pagibig_employee', 'withholding_tax',
                    'late_deduction', 'undertime_deduction', 'leave_without_pay', 'loan_deductions',
                    'other_deductions', 'gross_pay', 'net_pay',
                )
            }
            record.calculation_rule_version = rule_set.version if rule_set else ''
            record.calculation_input_hash = cls._hash(snapshot)
            record.calculation_output_hash = cls._hash(output)
            record.calculation_snapshot = {**(record.calculation_snapshot or {}), 'provenance': snapshot}
            record.save()

    @classmethod
    @transaction.atomic
    def process_period(cls, period, organization, actor=None):
        check = cls.preflight(period, organization)
        period.confidence_status = check['confidence']
        period.confidence_summary = check
        if check['confidence'] == 'BLOCKED':
            period.save(update_fields=('confidence_status', 'confidence_summary', 'updated_at'))
            raise ValueError('Payroll confidence preflight is BLOCKED: ' + '; '.join(check['errors']))
        rule_set = cls.rule_set_for(period, organization)
        period.rule_set = rule_set
        processed = PayrollCalculator.process_period(period, organization)
        cls._apply_absence_deductions(period, organization)
        cls._record_provenance(period, organization)
        period.confidence_status = check['confidence']
        period.confidence_summary = {**check, 'processed_records': processed}
        if actor is not None:
            period.processed_by = actor
        period.save(update_fields=('confidence_status', 'confidence_summary', 'rule_set', 'processed_by', 'updated_at'))
        return processed


def models_q_effective_to(as_of):
    from django.db.models import Q
    return Q(effective_to__isnull=True) | Q(effective_to__gte=as_of)
