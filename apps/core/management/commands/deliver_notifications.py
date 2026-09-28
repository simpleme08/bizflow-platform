from django.core.management.base import BaseCommand
from apps.core.models import Notification
from apps.core.notifications import deliver_notification


class Command(BaseCommand):
    help = 'Deliver pending/failed HR notifications with bounded retries.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=100)
        parser.add_argument('--max-attempts', type=int, default=5)

    def handle(self, *args, **options):
        qs = Notification.objects.filter(
            status__in=(Notification.Status.PENDING, Notification.Status.FAILED),
            attempts__lt=options['max_attempts'],
        ).order_by('created_at')[:options['limit']]
        sent = failed = 0
        for notification in qs:
            deliver_notification(notification)
            if notification.status == Notification.Status.SENT:
                sent += 1
            else:
                failed += 1
        self.stdout.write(self.style.SUCCESS(f'notifications sent={sent} failed={failed}'))
