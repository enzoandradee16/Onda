"""Readable summaries for operation results; raw fields belong in diagnostics."""


def cache_message(result, translate=lambda text: text):
    remaining = translate('Cache em disco: {size} MB.').format(
        size=f"{result.get('bytes', 0) / 1048576:.2f}"
    )
    if 'removed' not in result:
        return remaining
    lines = [
        translate('Cache limpo. Espaço liberado: {size} MB.').format(
            size=f"{result.get('removed', 0) / 1048576:.2f}"
        ),
        remaining,
    ]
    if result.get('failed', 0):
        lines.append(
            translate(
                'Alguns arquivos não puderam ser removidos. Tente novamente depois de fechar as operações em andamento.'
            )
        )
    return '\n'.join(lines)
