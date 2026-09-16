"""Application-level confidence engine (STEP 09).

Combines three independent signals per field — OCR confidence, extraction
(self-reported) confidence, and deterministic validation outcomes — into
one explainable score (0-1) plus a workflow band:

  HIGH (>= 0.80)   -> eligible for normal workflow
  MEDIUM (>= 0.60) -> review depending on field/rule
  LOW (< 0.60)     -> human verification required
  REVIEW_REQUIRED  -> no score possible (missing value/inputs)

These thresholds are INITIAL OPERATIONAL values, not calibrated
probabilities (08 section 8, 12 section 6): they route work, they do not
prove correctness, and confidence is NEVER legal correctness. Validation
conflicts cap the score instead of averaging away: a FAIL/ERROR caps at
0.39 (forces LOW), a WARNING/REVIEW_REQUIRED caps at 0.69 (at most
MEDIUM). Every score carries reasons so a reviewer can see exactly why a
field was flagged.
"""
