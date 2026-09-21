from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .confidence import PayrollConfidenceGate
from .models import PayrollPeriod


@receiver(pre_save, sender=PayrollPeriod)
def enforce_payroll_confidence(sender, instance, **kwargs):
    if settings.ENVIRONMENT != "production":
        return
    if instance.status != PayrollPeriod.Status.CALCULATED or not instance.organization_id:
        return
    status, summary, rule_set = PayrollConfidenceGate.evaluate(instance.organization, instance)
    instance.confidence_status = status
    instance.confidence_summary = summary
    instance.rule_set = rule_set
    if status == "BLOCKED":
        raise ValidationError("Payroll confidence gate blocked calculation: " + "; ".join(summary["errors"]))


@receiver(post_save, sender=PayrollPeriod)
def persist_payroll_confidence(sender, instance, **kwargs):
    if settings.ENVIRONMENT != "production" or instance.status != PayrollPeriod.Status.CALCULATED:
        return
    type(instance).objects.filter(pk=instance.pk).update(
        confidence_status=instance.confidence_status,
        confidence_summary=instance.confidence_summary,
        rule_set_id=instance.rule_set_id,
    )
