"""Provider-independent AI extraction layer (STEP 06).

Application code must use `AIService.extract_land_record` (or the
`extract_land_record()` helper) — never import a provider adapter directly.
"""

from .service import AIService, extract_land_record, get_ai_service

__all__ = ["AIService", "extract_land_record", "get_ai_service"]
