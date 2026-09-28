from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models import AuditEvent
from apps.organization.models import Organization


class Command(BaseCommand):
    help = 'Apply organization-configured audit-log retention policies.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Report deletions without deleting records.')

    def handle(self, *args, **options):
        now = timezone.now()
        dry_run = options['dry_run']
        total = 0
        for organization in Organization.objects.filter(is_active=True).iterator():
            cutoff = now - timedelta(days=organization.audit_retention_days)
            qs = AuditEvent.objects.filter(organization=organization, created_at__lt=cutoff)
            count = qs.count()
            if count and not dry_run:
                qs.delete()
            total += count
            if count:
                self.stdout.write(f'{organization.name}: {count} audit events {"would be deleted" if dry_run else "deleted"}')
        self.stdout.write(self.style.SUCCESS(f'Total: {total} audit events {"eligible" if dry_run else "processed"}.'))
