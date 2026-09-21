from django.db.models import Q

from .models import PayrollRuleSet, PayrollWageRate


class PayrollConfidenceGate:
    """Resolve and validate the effective payroll rules for a period."""

    @staticmethod
    def _effective_rules(organization, as_of):
        return list(
            PayrollRuleSet.objects.filter(
                Q(organization=organization) | Q(organization__isnull=True),
                is_active=True,
                effective_from__lte=as_of,
            )
            .filter(Q(effective_to__isnull=True) | Q(effective_to__gte=as_of))
            .order_by("-effective_from", "-created_at")
        )

    @classmethod
    def resolve_rule_set(cls, organization, as_of):
        rules = cls._effective_rules(organization, as_of)
        return next((item for item in rules if item.organization_id == organization.id), None) or next(
            (item for item in rules if item.organization_id is None), None
        )

    @staticmethod
    def _effective_wage_rates(organization, as_of):
        return PayrollWageRate.objects.filter(
            Q(organization=organization) | Q(organization__isnull=True),
            is_active=True,
            effective_from__lte=as_of,
        ).filter(Q(effective_to__isnull=True) | Q(effective_to__gte=as_of))

    @classmethod
    def evaluate(cls, organization, period):
        selected = cls.resolve_rule_set(organization, period.end_date)
        errors = []
        warnings = []
        if selected is None:
            errors.append("No effective payroll rule set with provenance is configured.")
        else:
            if not selected.source_name:
                errors.append("Selected rule set has no source name.")
            if not selected.source_url:
                errors.append("Selected rule set has no source URL.")
            if not selected.version:
                errors.append("Selected rule set has no version identifier.")

        rates = cls._effective_wage_rates(organization, period.end_date)
        employees = organization.employees.filter(is_active=True).select_related("payroll_profile")
        missing_mwe_rates = []
        for employee in employees:
            profile = getattr(employee, "payroll_profile", None)
            if not profile or not profile.minimum_wage_earner:
                continue
            if not profile.wage_region or not profile.wage_category:
                missing_mwe_rates.append(employee.employee_number)
                continue
            match = rates.filter(
                region_code__iexact=profile.wage_region,
                category=profile.wage_category,
            ).filter(Q(organization=organization) | Q(organization__isnull=True)).order_by("-effective_from", "-created_at").first()
            if match is None:
                missing_mwe_rates.append(employee.employee_number)

        if missing_mwe_rates:
            errors.append("MWE employees missing an applicable effective wage rate: " + ", ".join(missing_mwe_rates))
        elif not rates.exists():
            warnings.append("No effective wage-rate table is configured; no MWE employees currently require one.")

        status = "BLOCKED" if errors else ("REVIEW" if warnings else "READY")
        summary = {
            "status": status,
            "as_of": period.end_date.isoformat(),
            "rule_set_id": selected.id if selected else None,
            "rule_set_version": selected.version if selected else None,
            "source_name": selected.source_name if selected else None,
            "source_url": selected.source_url if selected else None,
            "errors": errors,
            "warnings": warnings,
        }
        return status, summary, selected

    @classmethod
    def enforce(cls, organization, period):
        status, summary, selected = cls.evaluate(organization, period)
        period.confidence_status = status
        period.confidence_summary = summary
        period.rule_set = selected
        if status == "BLOCKED":
            return False, summary
        return True, summary
