"""Reviewed artist names with primary-source provenance; no surname guessing."""

from matching import words, without_guest_credit

# Keep groups explicit and sourced. Similar names alone do not establish identity.
GROUPS = (
    (
        (
            'Antonio Carlos Jobim',
            'Tom Jobim',
            'Antonio Carlos Brasileiro de Almeida Jobim',
        ),
        'https://www.jobim.org/jobim/handle/2010/15364?show=full',
    ),
)


def artist_names(name, record=None):
    primary = words(without_guest_credit(name)) - {'and', 'with'}
    groups = list(GROUPS)
    if record:
        from artist_alias_lookup import valid_groups

        groups.extend(
            (tuple(row["aliases"]), row["source_url"])
            for row in valid_groups(record.get("_verified_artist_aliases"))
        )
    result = [(primary, None)]
    seen = {frozenset(primary)}
    for names, source in groups:
        if any(primary == words(alias) for alias in names):
            for alias in names:
                tokens = words(alias)
                if frozenset(tokens) not in seen:
                    seen.add(frozenset(tokens))
                    result.append((tokens, source))
    return result


def artist_overlap(name, identity, record=None):
    return max(
        (
            len(alias & identity) / len(alias)
            for alias, _ in artist_names(name, record)
            if alias
        ),
        default=0,
    )


def alias_evidence(name, identity, record=None):
    options = artist_names(name, record)
    primary = options[0][0]
    if primary and len(primary & identity) / len(primary) >= 0.65:
        return None
    labels = [label for names, _ in GROUPS for label in names]
    if record:
        labels.extend(
            label
            for group in record.get('_verified_artist_aliases', [])
            for label in group.get('aliases', [])
        )
    for alias, source in options[1:]:
        if alias and alias <= identity:
            return {
                'original_artist': name,
                'matched_alias': next(
                    label for label in labels if words(label) == alias
                ),
                'source_url': source,
            }
    return None
