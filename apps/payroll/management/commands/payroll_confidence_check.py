from django.core.management.base import BaseCommand, CommandError

from apps.organization.models import Organization
from apps.payroll.confidence import PayrollConfidenceGate
from apps.payroll.models import PayrollPeriod


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
            period = PayrollPeriod(
                organization=organization,
                name="confidence-check",
                start_date=as_of,
                end_date=as_of,
            )
            status, summary, selected = PayrollConfidenceGate.evaluate(organization, period)
            self.stdout.write(f"{organization.slug}: {status}")
            if selected:
                self.stdout.write(f"  rule_set={selected.version} source={selected.source_name}")
            for message in summary["errors"]:
                self.stdout.write(self.style.ERROR(f"  ERROR: {message}"))
            for message in summary["warnings"]:
                self.stdout.write(self.style.WARNING(f"  WARNING: {message}"))
            blocked = blocked or status == "BLOCKED"

        if blocked:
            raise CommandError("Payroll confidence check is BLOCKED; production payroll must not proceed.")
