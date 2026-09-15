from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from apps.organization.models import Organization

from apps.payroll.models import PayrollRuleSet, PayrollWageRate


class Command(BaseCommand):
    help = "Validate production payroll rule provenance and effective-dated wage configuration."

    def add_arguments(self, parser):
        parser.add_argument("--organization", help="Organization slug to validate")
        parser.add_argument("--date", dest="as_of", required=True, help="Payroll period end date (YYYY-MM-DD)")

    def handle(self, *args, **options):
        from datetime import date

        try:
            as_of = date.fromisoformat(options["as_of"])
        except ValueError as exc:
            raise CommandError("--date must use YYYY-MM-DD") from exc

        organizations = Organization.objects.filter(is_active=True)
        if options.get("organization"):
            organizations = organizations.filter(slug=options["organization"])

        if not organizations.exists():
            raise CommandError("No active organization matched the requested scope.")

        blocked = False
        for organization in organizations:
            rules = list(
                PayrollRuleSet.objects.filter(
                    Q(organization=organization) | Q(organization__isnull=True),
                    is_active=True,
                    effective_from__lte=as_of,
                )
                .filter(Q(effective_to__isnull=True) | Q(effective_to__gte=as_of))
                .order_by("-effective_from", "-created_at")
            )
            selected = next((item for item in rules if item.organization_id == organization.id), None)
            selected = selected or next((item for item in rules if item.organization_id is None), None)

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

            wage_count = PayrollWageRate.objects.filter(
                Q(organization=organization) | Q(organization__isnull=True),
                is_active=True,
                effective_from__lte=as_of,
            ).filter(Q(effective_to__isnull=True) | Q(effective_to__gte=as_of)).count()
            if wage_count == 0:
                warnings.append("No effective wage-rate table is configured; minimum-wage validation cannot be completed.")

            if errors:
                blocked = True
                status = "BLOCKED"
            elif warnings:
                status = "REVIEW"
            else:
                status = "READY"

            self.stdout.write(f"{organization.slug}: {status}")
            if selected:
                self.stdout.write(f"  rule_set={selected.version} source={selected.source_name}")
            for message in errors:
                self.stdout.write(self.style.ERROR(f"  ERROR: {message}"))
            for message in warnings:
                self.stdout.write(self.style.WARNING(f"  WARNING: {message}"))

        if blocked:
            raise CommandError("Payroll confidence check is BLOCKED; production payroll must not proceed.")
