from pathlib import Path
from zipfile import BadZipFile, ZipFile

from django.core.exceptions import ValidationError


MAX_PRIVATE_DOCUMENT_BYTES = 10 * 1024 * 1024
_ALLOWED_SIGNATURES = {
    '.pdf': (b'%PDF-',),
    '.png': (b'\x89PNG\r\n\x1a\n',),
    '.jpg': (b'\xff\xd8\xff',),
    '.jpeg': (b'\xff\xd8\xff',),
}


def validate_private_document(upload):
    """Validate size, extension and basic file signature for private HR uploads.

    This is defense in depth, not malware scanning. Storage must remain private
    and uploads should be malware-scanned before any high-risk production use.
    """
    if not upload:
        return

    if upload.size <= 0 or upload.size > MAX_PRIVATE_DOCUMENT_BYTES:
        raise ValidationError('File must be non-empty and no larger than 10 MB.')

    extension = Path(upload.name).suffix.lower()
    if extension not in (*_ALLOWED_SIGNATURES.keys(), '.docx'):
        raise ValidationError('Allowed file types are PDF, DOCX, JPG, JPEG and PNG.')

    current_position = upload.tell()
    try:
        upload.seek(0)
        header = upload.read(8)
        if extension == '.docx':
            upload.seek(0)
            try:
                with ZipFile(upload) as archive:
                    names = set(archive.namelist())
                    if '[Content_Types].xml' not in names or 'word/document.xml' not in names:
                        raise ValidationError('The DOCX file is not a valid Word document.')
                    if archive.testzip() is not None:
                        raise ValidationError('The DOCX file is corrupted.')
            except (BadZipFile, OSError):
                raise ValidationError('The DOCX file is not a valid Word document.')
        elif not any(header.startswith(signature) for signature in _ALLOWED_SIGNATURES[extension]):
            raise ValidationError('File contents do not match the selected file type.')
    finally:
        upload.seek(current_position)
