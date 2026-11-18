"""Explicit study groupings; never mutate original reference or prediction labels."""

SCHEMES = {
    'five': ['NT1', 'NT2', 'IH', 'Uncertain', 'Not_NT_IH'],
    'combined': ['NT1', 'NT2_IH', 'Uncertain', 'Not_NT_IH'],
}


def labels_for(scheme='five'):
    if scheme not in SCHEMES:
        raise ValueError(f'Unknown label scheme: {scheme}')
    return list(SCHEMES[scheme])


def grouped_label(value, scheme='five'):
    labels_for(scheme)
    return 'NT2_IH' if scheme == 'combined' and isinstance(value, str) and value in ('NT2', 'IH') else value
