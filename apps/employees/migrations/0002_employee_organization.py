import uuid

import django.db.models.deletion
from django.db import migrations, models


def create_default_organization(apps, schema_editor):
	Organization = apps.get_model('organization', 'Organization')
	Employee = apps.get_model('employees', 'Employee')
	organization, _ = Organization.objects.get_or_create(
		slug='default',
		defaults={'name': 'Default Organization', 'id': uuid.uuid4()},
	)
	Employee.objects.filter(organization__isnull=True).update(organization=organization)


class Migration(migrations.Migration):

	dependencies = [
		('employees', '0001_initial'),
		('organization', '0001_initial'),
	]

	operations = [
		migrations.AddField(
			model_name='employee',
			name='organization',
			field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='employees', to='organization.organization'),
		),
		migrations.RunPython(create_default_organization, migrations.RunPython.noop),
		migrations.AlterField(
			model_name='employee',
			name='organization',
			field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='employees', to='organization.organization'),
		),
	]