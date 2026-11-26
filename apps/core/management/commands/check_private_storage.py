from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Perform a read-only connectivity check against the configured private "
        "S3-compatible storage bucket. No objects are uploaded, changed, or deleted."
    )

    def handle(self, *args, **options):
        if getattr(settings, "STORAGE_BACKEND", "") != "s3":
            raise CommandError("Private S3 storage is not the active storage backend.")

        bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "").strip()
        if not bucket:
            raise CommandError("The private storage bucket is not configured.")

        if not getattr(settings, "AWS_QUERYSTRING_AUTH", False):
            raise CommandError("Signed URL authentication is disabled; private storage check aborted.")

        try:
            client = default_storage.connection.meta.client
            client.head_bucket(Bucket=bucket)
            self.stdout.write(self.style.SUCCESS("S3-compatible bucket authentication: passed"))

            # Generate a short-lived URL for a deliberately nonexistent probe key.
            # It is never printed or requested, so the check cannot expose files.
            client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": bucket,
                    "Key": "__bizflow_read_only_probe__/nonexistent-object",
                },
                ExpiresIn=60,
            )
            self.stdout.write(self.style.SUCCESS("Private signed-URL generation: passed"))
        except Exception:
            # Provider exceptions can contain endpoint or request details. Keep
            # credentials and signed request material out of command output.
            raise CommandError(
                "Private storage connectivity check failed. Verify the staging "
                "S3 credentials, endpoint, bucket, and bucket permissions in Render."
            ) from None

        self.stdout.write(
            self.style.SUCCESS(
                "Read-only check complete. No storage objects were read, written, or deleted."
            )
        )
