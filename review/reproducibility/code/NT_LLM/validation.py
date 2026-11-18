"""Structural checks and evidence flags, without clinical adjudication."""
from datetime import date
import re
from NT_LLM.label_schemes import labels_for

LABELS = ['NT1', 'NT2', 'IH', 'Not_NT_IH', 'Uncertain']
EVIDENCE_FIELDS = ['EDS_chronic', 'cataplexy', 'MSLT_positive', 'CSF_hcrt_low', 'OSA_or_alt_dx']


def validate_output(value, patient_id, index_date, note_text, label_scheme='five'):
    if not isinstance(value, dict) or value.get('parse_error'):
        return ['empty_or_invalid_json']
    errors = []
    if str(value.get('patient_id')) != str(patient_id):
        errors.append('patient_id_mismatch')
    if value.get('index_date') != index_date:
        errors.append('index_date_mismatch')
    if value.get('final_label') not in labels_for(label_scheme):
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


def quote_support(quote, supplied_text):
    """Link a quote to an exact source span; tolerate whitespace/quote marks only.

    Wording, case, numbers, masking, negation and other punctuation stay strict.
    Apostrophes inside words are not treated as quotation delimiters.
    Offsets are Python character offsets, with an exclusive end.
    """
    result = {'raw_quote': quote, 'match_type': 'unsupported',
              'source_start': None, 'source_end': None, 'source_quote': None}
    if not isinstance(quote, str) or not quote.strip():
        return result
    start = supplied_text.find(quote)
    if start >= 0:
        end = start + len(quote); kind = 'exact'
    else:
        stripped = quote.strip(); pattern = []; position = 0
        marks = '\"\'“”‘’'
        while position < len(stripped):
            char = stripped[position]
            if char.isspace():
                pattern.append(r'\s+')
                while position + 1 < len(stripped) and stripped[position + 1].isspace():
                    position += 1
            elif char in marks and not (position > 0 and position + 1 < len(stripped)
                    and stripped[position - 1].isalnum() and stripped[position + 1].isalnum()):
                pattern.append('[' + re.escape(marks) + ']')
            else:
                pattern.append(re.escape(char))
            position += 1
        match = re.search(''.join(pattern), supplied_text)
        if match is None:
            return result
        start, end = match.span(); kind = 'formatting_only'
    result.update(match_type=kind, source_start=start, source_end=end,
                  source_quote=supplied_text[start:end])
    return result


def evidence_quote_support(value, supplied_text):
    quotes = value.get('key_evidence_quotes') or []
    return [quote_support(q, supplied_text) for q in quotes] if isinstance(quotes, list) else []


def evidence_flags(value, supplied_text):
    flags = []
    matches = evidence_quote_support(value, supplied_text)
    if any(q['match_type'] == 'unsupported' for q in matches):
        flags.append('nonverbatim_or_unsupported_quote')
    if any(q['match_type'] == 'formatting_only' for q in matches):
        flags.append('quote_formatting_normalized')
    anchor = value.get('diagnosis_anchor_date')
    if anchor and anchor not in supplied_text:
        flags.append('date_requires_source_review')
    if value.get('final_label') in ['NT1', 'NT2', 'IH', 'NT2_IH']:
        flags.append('candidate_requires_clinical_verification')
    return flags
