"""Bounded alternate-video recovery; all normal matching checks remain active."""


def download_recording(
    record, selected, logger, choose, download, saved, *, automatic=False, confirm=False
):
    from matching import NoCompatibleMatch, resolve_youtube

    previous = getattr(logger, 'excluded_youtube_ids', ())
    excluded = set(previous)
    try:
        for attempt in range(3):
            try:
                return download(selected)
            except Exception as error:
                text = str(error).lower()
                recoverable = isinstance(error, NoCompatibleMatch) or any(
                    term in text
                    for term in (
                        'detalhes completos do áudio não confirmam',
                        'sign in to confirm your age',
                    )
                )
                if (
                    not recoverable
                    or saved
                    or attempt == 2
                    or selected.get('selection') in ('user', 'remembered')
                ):
                    raise
                failed = selected.get('id')
                if not failed:
                    raise
                excluded.add(failed)
                logger.excluded_youtube_ids = excluded
                logger.warning(str(error))
                selected = resolve_youtube(
                    record, logger, choose, automatic=automatic, confirm=confirm
                )
                if selected.get('id') in excluded:
                    raise NoCompatibleMatch(str(error)) from error
    finally:
        logger.excluded_youtube_ids = previous
