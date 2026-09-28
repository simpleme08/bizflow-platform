import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0001_auditevent')]
    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.UUIDField(default=__import__('uuid').uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('event', models.CharField(max_length=80)),
                ('subject', models.CharField(max_length=200)),
                ('body', models.TextField()),
                ('channel', models.CharField(choices=[('EMAIL','Email')], default='EMAIL', max_length=20)),
                ('status', models.CharField(choices=[('PENDING','Pending'),('SENT','Sent'),('FAILED','Failed')], default='PENDING', max_length=20)),
                ('attempts', models.PositiveIntegerField(default=0)),
                ('last_error', models.TextField(blank=True)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='organization.organization')),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={'indexes':[models.Index(fields=('status','created_at'),name='notif_status_created_idx')]},
        ),
    ]
