from django.core.mail import send_mail
from django.utils import timezone

from .models import Notification


def queue_notification(*, organization, recipient, event, subject, body):
    return Notification.objects.create(
        organization=organization, recipient=recipient, event=event,
        subject=subject, body=body,
    )


def deliver_notification(notification):
    if notification.status == Notification.Status.SENT:
        return notification
    try:
        email = getattr(notification.recipient, 'email', '')
        if not email:
            raise ValueError('Recipient has no email address.')
        send_mail(notification.subject, notification.body, None, [email], fail_silently=False)
        notification.status = Notification.Status.SENT
        notification.sent_at = timezone.now()
        notification.last_error = ''
    except Exception as exc:
        notification.status = Notification.Status.FAILED
        notification.last_error = str(exc)[:2000]
    notification.attempts += 1
    notification.save(update_fields=('status', 'sent_at', 'last_error', 'attempts', 'updated_at'))
    return notification
