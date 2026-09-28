from datetime import timedelta

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.utils import timezone

from apps.employees.models import EmployeeDocument


class Command(BaseCommand):
    help = 'Email employees and HR contacts about upcoming employee-document expiries.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30)
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        days = max(1, options['days'])
        today = timezone.localdate()
        horizon = today + timedelta(days=days)
        documents = EmployeeDocument.objects.filter(
            expiry_date__gte=today,
            expiry_date__lte=horizon,
            status='ACTIVE',
        ).select_related('employee', 'employee__user', 'employee__organization')

        sent = 0
        for document in documents.iterator():
            recipient = document.employee.work_email or document.employee.personal_email or document.employee.user.email
            if not recipient:
                self.stdout.write(self.style.WARNING(
                    f'No email for {document.employee.employee_number}: {document.name}'
                ))
                continue
            subject = f'Document expiry reminder: {document.name}'
            body = (
                f'Hello {document.employee.first_name},\n\n'
                f'Your {document.document_type} document "{document.name}" '
                f'is due to expire on {document.expiry_date.isoformat()}.\n\n'
                'Please coordinate with HR to renew or replace it before expiry.\n\n'
                'BizFlow HRIS'
            )
            if not options['dry_run']:
                send_mail(subject, body, None, [recipient], fail_silently=False)
            sent += 1
        self.stdout.write(self.style.SUCCESS(
            f'{sent} document expiry reminder(s) {"identified" if options["dry_run"] else "sent"}.'
        ))
