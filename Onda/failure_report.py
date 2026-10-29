"""Failure reports deliberately exclude configs, credentials and completed jobs."""

from i18n import tr
from metadata import parse_link
from queue_details import queue_info
from queue_titles import record_name

AUDIO_MODES = {"original", "mp3", "m4a", "flac", "wav", "opus", "ogg", "aac"}


def failed_rows(jobs, ids=None):
    allowed = set(ids) if ids is not None else None
    return [
        dict(
            id=key,
            title=job.get("display_name") or job.get("url", ""),
            url=job.get("failure_original_url") or job.get("url", ""),
            reason=job.get("last_error") or tr("Motivo não informado"),
        )
        for key, job in jobs.items()
        if job.get("state") == "Falhou" and (allowed is None or key in allowed)
    ]


def report_text(rows):
    return (
        tr("Falhas da fila")
        + "\n\n"
        + "\n\n".join(
            f"{index}. {row['title']}\n{row['url']}\n"
            + tr("Motivo: {reason}").format(reason=tr(row['reason']))
            for index, row in enumerate(rows, 1)
        )
        + "\n"
    )


def replace_metadata(job, record):
    if job.get("mode") not in AUDIO_MODES or job.get("playlist"):
        return False
    service, _, _, url = parse_link(record.get("source_url", ""))
    if service not in ("deezer", "apple"):
        return False
    job.setdefault("failure_original_url", job.get("url", ""))
    job.update(
        url=url,
        display_name=record_name(record),
        queue_info=queue_info(record),
        state="Na fila",
    )
    for key in (
        "catalog_record",
        "selected_catalog_url",
        "selected_version",
        "youtube_match",
        "last_error",
    ):
        job.pop(key, None)
    return True
