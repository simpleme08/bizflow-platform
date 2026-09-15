from decimal import Decimal

from .models import PayrollRecord


ZERO = Decimal("0.00")


class PayrollReconciliation:
    """Centavo-exact reconciliation helpers for a payroll period."""

    MONEY_FIELDS = (
        "sss_employee", "sss_employer",
        "philhealth_employee", "philhealth_employer",
        "pagibig_employee", "pagibig_employer",
        "withholding_tax", "gross_pay", "net_pay",
    )

    @classmethod
    def summarize(cls, period):
        records = PayrollRecord.objects.filter(payroll_period=period, employee__organization=period.organization)
        totals = {field: sum((getattr(record, field) for record in records), ZERO) for field in cls.MONEY_FIELDS}
        totals["record_count"] = records.count()
        totals["total_deductions"] = sum((record.total_deductions for record in records), ZERO)
        totals["employer_contributions"] = sum((record.employer_contributions for record in records), ZERO)
        return totals

    @classmethod
    def validate(cls, period):
        totals = cls.summarize(period)
        errors = []
        if totals["record_count"] != period.organization.employees.filter(is_active=True).count():
            errors.append("Payroll record count does not match the active employee population.")
        for field in cls.MONEY_FIELDS:
            value = totals[field]
            if value != value.quantize(Decimal("0.01")):
                errors.append(f"{field} contains a sub-cent total: {value}.")
        expected_net = totals["gross_pay"] - totals["total_deductions"]
        if expected_net != totals["net_pay"]:
            errors.append(f"Net-pay reconciliation mismatch: expected {expected_net}, recorded {totals['net_pay']}.")
        expected_employer = totals["sss_employer"] + totals["philhealth_employer"] + totals["pagibig_employer"]
        if expected_employer != totals["employer_contributions"]:
            errors.append("Employer statutory contribution reconciliation mismatch.")
        return {"ok": not errors, "errors": errors, "totals": totals}

    @classmethod
    def enforce(cls, period):
        result = cls.validate(period)
        if not result["ok"]:
            raise ValueError("Payroll reconciliation failed: " + " ".join(result["errors"]))
        return result
