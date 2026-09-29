from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from apps.core.notifications import queue_notification
from apps.core.models import Notification
from apps.employees.models import EmployeeDocument


class Command(BaseCommand):
    help = "Queue expiry notifications for employee documents."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30, help="Notify for documents expiring within this many days.")
        parser.add_argument("--dry-run", action="store_true", help="Report notifications without creating them.")

    def handle(self, *args, **options):
        days = options["days"]
        if days < 0 or days > 3650:
            raise CommandError("--days must be between 0 and 3650.")

        today = timezone.localdate()
        horizon = today + timedelta(days=days)
        documents = (
            EmployeeDocument.objects
            .select_related("employee__user", "employee__organization")
            .filter(
                expiry_date__isnull=False,
                expiry_date__gte=today,
                expiry_date__lte=horizon,
                status="ACTIVE",
                employee__is_active=True,
            )
            .filter(Q(employee__user__is_active=True))
            .order_by("expiry_date", "id")
        )

        queued = 0
        skipped = 0
        for document in documents.iterator():
            event = f"DOCUMENT_EXPIRY:{document.pk}"
            already_queued = Notification.objects.filter(
                organization=document.employee.organization,
                recipient=document.employee.user,
                event=event,
            ).exists()
            if already_queued:
                skipped += 1
                continue

            days_left = (document.expiry_date - today).days
            subject = f"Document expiring: {document.name}"
            body = (
                f"Your {document.document_type} document, '{document.name}', "
                f"expires on {document.expiry_date:%B %d, %Y} ({days_left} day"
                f"{'' if days_left == 1 else 's'} remaining). "
                "Please coordinate with HR if renewal or replacement is required."
            )
            if not options["dry_run"]:
                queue_notification(
                    organization=document.employee.organization,
                    recipient=document.employee.user,
                    event=event,
                    subject=subject,
                    body=body,
                )
            queued += 1

        action = "would queue" if options["dry_run"] else "queued"
        self.stdout.write(
            self.style.SUCCESS(
                f"Document expiry scan complete: {queued} notification(s) {action}; "
                f"{skipped} already queued."
            )
        )
