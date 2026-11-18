"""Structural checks and evidence flags, without clinical adjudication."""
from datetime import date

LABELS = ['NT1', 'NT2', 'IH', 'Not_NT_IH', 'Uncertain']
EVIDENCE_FIELDS = ['EDS_chronic', 'cataplexy', 'MSLT_positive', 'CSF_hcrt_low', 'OSA_or_alt_dx']


def validate_output(value, patient_id, index_date, note_text):
    if not isinstance(value, dict) or value.get('parse_error'):
        return ['empty_or_invalid_json']
    errors = []
    if str(value.get('patient_id')) != str(patient_id):
        errors.append('patient_id_mismatch')
    if value.get('index_date') != index_date:
        errors.append('index_date_mismatch')
    if value.get('final_label') not in LABELS:
        errors.append('invalid_label')
    if value.get('confidence') not in ['high', 'medium', 'low']:
        errors.append('invalid_confidence')
    if 'diagnosis_anchor_date' not in value:
        errors.append('missing_diagnosis_anchor_date')
    anchor = value.get('diagnosis_anchor_date')
    if anchor is not None:
        try:
            if not isinstance(anchor, str) or date.fromisoformat(anchor).isoformat() != anchor:
                raise ValueError()
        except (ValueError, TypeError):
            errors.append('invalid_diagnosis_date')
    evidence = value.get('key_evidence')
    if not isinstance(evidence, dict) or any(evidence.get(k) not in ['Yes', 'No', 'Unclear', 'NotMentioned'] for k in EVIDENCE_FIELDS):
        errors.append('invalid_key_evidence')
    quotes = value.get('key_evidence_quotes')
    if not isinstance(quotes, list) or not quotes or any(not isinstance(q, str) or not q.strip() for q in quotes):
        errors.append('missing_evidence_quotes')
    if not isinstance(value.get('reasoning'), str) or not value.get('reasoning', '').strip():
        errors.append('missing_reasoning')
    # Quote/date support is a review flag, never proof of clinical correctness.
    return errors


def evidence_flags(value, supplied_text):
    flags = []
    quotes = value.get('key_evidence_quotes') or []
    if any(not isinstance(q, str) or q not in supplied_text for q in quotes):
        flags.append('nonverbatim_or_unsupported_quote')
    anchor = value.get('diagnosis_anchor_date')
    if anchor and anchor not in supplied_text:
        flags.append('date_requires_source_review')
    if value.get('final_label') in ['NT1', 'NT2', 'IH']:
        flags.append('candidate_requires_clinical_verification')
    return flags
