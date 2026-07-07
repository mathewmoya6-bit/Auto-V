# app/services/certificate_service.py
# =============================================================================
# AUTO-V API - CertificateService (STUB - NOT YET IMPLEMENTED)
# =============================================================================
# This is a placeholder created only to satisfy the import in
# app/services/__init__.py so the app can start. Replace with real logic.


class CertificateService:
    """
    STUB: no real implementation yet. Calling any method here will raise
    NotImplementedError until this service is properly built out.
    """

    def __init__(self):
        pass

    def __getattr__(self, name):
        def _not_implemented(*args, **kwargs):
            raise NotImplementedError(
                f"CertificateService.{name}() is not yet implemented (stub service)."
            )
        return _not_implemented
