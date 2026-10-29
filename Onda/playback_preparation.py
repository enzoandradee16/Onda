"""The number of upcoming tracks to prepare, not concurrent processing jobs."""

CHOICES = (1, 2, 3, 5)


def preparation_ahead(value=2):
    return (
        int(value)
        if type(value) in (int, str) and str(value) in ('1', '2', '3', '5')
        else 2
    )
