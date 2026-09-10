from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('organization', '0005_subscription_constraints')]

    operations = [
        migrations.CreateModel(
            name='BillingSubscription',
            fields=[
                ('id', models.UUIDField(default=__import__('uuid').uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('provider', models.CharField(default='paymongo', max_length=30)),
                ('provider_subscription_id', models.CharField(max_length=120, unique=True)),
                ('provider_customer_id', models.CharField(blank=True, max_length=120)),
                ('provider_plan_id', models.CharField(blank=True, max_length=120)),
                ('plan_code', models.CharField(max_length=20)),
                ('status', models.CharField(max_length=40)),
                ('current_period_end', models.DateField(blank=True, null=True)),
                ('canceled_at', models.DateTimeField(blank=True, null=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='billing_subscriptions', to='organization.organization')),
            ],
            options={'ordering': ('-created_at',)},
        ),
        migrations.CreateModel(
            name='BillingWebhookEvent',
            fields=[
                ('id', models.UUIDField(default=__import__('uuid').uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('provider', models.CharField(default='paymongo', max_length=30)),
                ('provider_event_id', models.CharField(max_length=120, unique=True)),
                ('event_type', models.CharField(max_length=100)),
                ('livemode', models.BooleanField(default=False)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('payload', models.JSONField(blank=True, default=dict)),
            ],
            options={'ordering': ('-created_at',)},
        ),
        migrations.CreateModel(
            name='BillingInvoice',
            fields=[
                ('id', models.UUIDField(default=__import__('uuid').uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('provider', models.CharField(default='paymongo', max_length=30)),
                ('provider_invoice_id', models.CharField(max_length=120, unique=True)),
                ('provider_payment_intent_id', models.CharField(blank=True, max_length=120)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('currency', models.CharField(default='PHP', max_length=3)),
                ('status', models.CharField(max_length=30)),
                ('due_date', models.DateField(blank=True, null=True)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('description', models.CharField(blank=True, max_length=255)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='billing_invoices', to='organization.organization')),
                ('subscription', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='invoices', to='organization.billingsubscription')),
            ],
            options={'ordering': ('-created_at',)},
        ),
        migrations.AddIndex(model_name='billingsubscription', index=models.Index(fields=['organization', 'status'], name='billingsub_org_status_idx')),
        migrations.AddIndex(model_name='billinginvoice', index=models.Index(fields=['organization', '-created_at'], name='billinginv_org_created_idx')),
        migrations.AddIndex(model_name='billingwebhookevent', index=models.Index(fields=['event_type', '-created_at'], name='billingwh_type_created_idx')),
    ]
