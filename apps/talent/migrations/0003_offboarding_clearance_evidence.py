import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('talent', '0002_offboarding_gates'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='OffboardingClearanceEvidence',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('clearance_key', models.CharField(max_length=100)),
                ('verified_at', models.DateTimeField()),
                ('notes', models.TextField()),
                ('evidence_reference', models.CharField(blank=True, help_text='Private evidence identifier only; never store a public URL or secret.', max_length=255)),
                ('offboarding', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='clearance_evidence', to='talent.offboardingrecord')),
                ('verified_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='verified_offboarding_clearances', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('clearance_key',)},
        ),
        migrations.AddConstraint(
            model_name='offboardingclearanceevidence',
            constraint=models.UniqueConstraint(fields=('offboarding', 'clearance_key'), name='unique_offboarding_clearance_evidence'),
        ),
    ]
