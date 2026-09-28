from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models import AuditEvent
from apps.employees.models import EmployeeDocument
from apps.attendance.models import AttendanceRecord
from apps.organization.models import Organization


class Command(BaseCommand):
    help = 'Apply organization-configured audit-log and archived-document retention policies.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Report deletions without deleting records.')

    def handle(self, *args, **options):
        now = timezone.now()
        dry_run = options['dry_run']
        total_audit = 0
        total_documents = 0
        total_photos = 0
        today = timezone.localdate()
        for organization in Organization.objects.filter(is_active=True).iterator():
            cutoff = now - timedelta(days=organization.audit_retention_days)
            audit_qs = AuditEvent.objects.filter(organization=organization, created_at__lt=cutoff)
            audit_count = audit_qs.count()
            if audit_count and not dry_run:
                audit_qs.delete()
            total_audit += audit_count
            if audit_count:
                self.stdout.write(f'{organization.name}: {audit_count} audit events {"would be deleted" if dry_run else "deleted"}')

            document_cutoff = today - timedelta(days=organization.document_retention_days)
            document_qs = EmployeeDocument.objects.filter(
                employee__organization=organization,
                status='ARCHIVED',
                expiry_date__isnull=False,
                expiry_date__lt=document_cutoff,
            )
            document_count = document_qs.count()
            if document_count and not dry_run:
                for document in document_qs.iterator():
                    if document.file:
                        document.file.delete(save=False)
                    document.delete()
            total_documents += document_count
            if document_count:
                self.stdout.write(f'{organization.name}: {document_count} archived documents {"would be deleted" if dry_run else "deleted"}')

            photo_cutoff = today - timedelta(days=organization.attendance_photo_retention_days)
            photo_qs = AttendanceRecord.objects.filter(employee__organization=organization, attendance_date__lt=photo_cutoff).exclude(clock_in_photo='', clock_out_photo='')
            photo_count = 0
            for record in photo_qs.iterator():
                changed = False
                if record.clock_in_photo:
                    photo_count += 1
                    changed = True
                    if not dry_run:
                        record.clock_in_photo.delete(save=False)
                if record.clock_out_photo:
                    photo_count += 1
                    changed = True
                    if not dry_run:
                        record.clock_out_photo.delete(save=False)
                if changed and not dry_run:
                    record.save(update_fields=('clock_in_photo', 'clock_out_photo', 'updated_at'))
            total_photos += photo_count
            if photo_count:
                self.stdout.write(f'{organization.name}: {photo_count} attendance proof photos {"would be deleted" if dry_run else "deleted"}')

        self.stdout.write(self.style.SUCCESS(
            f'Total: {total_audit} audit events, {total_documents} archived documents and {total_photos} attendance photos '
            f'{"eligible" if dry_run else "processed"}.'
        ))
