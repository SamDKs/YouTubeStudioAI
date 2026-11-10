"""Reglas de preparación; no genera narración ni interpreta nombres de recursos."""


def preparation_state(report: dict) -> str:
    """Exige guion, cuatro timelines y recursos explícitos antes de producir."""
    if not report.get('has_script'):
        return 'NEEDS_SCRIPT'
    if report.get('missing'):
        return 'NEEDS_ASSETS'
    return 'READY_FOR_PRODUCTION'
