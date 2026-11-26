from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings


class PrivateStorageCheckTests(SimpleTestCase):
    @override_settings(STORAGE_BACKEND="filesystem")
    def test_rejects_non_s3_backend(self):
        with self.assertRaisesMessage(CommandError, "not the active storage backend"):
            call_command("check_private_storage", stdout=StringIO())

    @override_settings(
        STORAGE_BACKEND="s3",
        AWS_STORAGE_BUCKET_NAME="bizflow-staging-private",
        AWS_QUERYSTRING_AUTH=True,
    )
    @patch("apps.core.management.commands.check_private_storage.default_storage")
    def test_checks_bucket_and_generates_signed_url_without_printing_it(self, storage):
        client = storage.connection.meta.client
        client.generate_presigned_url.return_value = (
            "https://example.invalid/private?signature=must-not-be-printed"
        )
        output = StringIO()

        call_command("check_private_storage", stdout=output)

        client.head_bucket.assert_called_once_with(Bucket="bizflow-staging-private")
        client.generate_presigned_url.assert_called_once()
        self.assertNotIn("signature=", output.getvalue())
        self.assertIn("Private signed-URL generation: passed", output.getvalue())

    @override_settings(
        STORAGE_BACKEND="s3",
        AWS_STORAGE_BUCKET_NAME="bizflow-staging-private",
        AWS_QUERYSTRING_AUTH=True,
    )
    @patch("apps.core.management.commands.check_private_storage.default_storage")
    def test_reports_provider_failure_without_leaking_exception(self, storage):
        storage.connection.meta.client.head_bucket.side_effect = Exception(
            "secret=do-not-leak"
        )
        with self.assertRaisesMessage(CommandError, "connectivity check failed"):
            call_command("check_private_storage", stdout=StringIO())
