"""User-facing download details derived only from reported engine events."""


def failure_advice(message):
    text = str(message).casefold()
    if any(
        word in text
        for word in (
            '403',
            '401',
            'private',
            'login',
            'cookies',
            'permission',
            'forbidden',
            'acesso',
            'privado',
        )
    ):
        return 'A plataforma pode exigir autenticação ou permissão.', 'Verificar acesso'
    if any(
        word in text
        for word in (
            '404',
            'not found',
            'removed',
            'deleted',
            'unsupported url',
            'inválid',
            'removido',
            'não encontrado',
        )
    ):
        return 'O link pode ter mudado ou o conteúdo foi removido.', 'Atualizar link'
    if any(
        word in text
        for word in (
            'timeout',
            'timed out',
            'connection',
            'network',
            '429',
            '502',
            '503',
            'conexão',
        )
    ):
        return (
            'A conexão ou a plataforma pode estar temporariamente indisponível.',
            'Tentar novamente',
        )
    return (
        'Não foi possível concluir. Consulte os detalhes da falha.',
        'Tentar novamente',
    )


def download_detail(event):
    kind = event.get('type')
    if kind == 'processing':
        return 'Convertendo'
    if kind in ('file', 'done'):
        return 'Salvando'
    if kind == 'stage':
        return event.get('message') or 'Consultando'
    if kind != 'progress':
        return 'Consultando'
    if event.get('status') == 'finished':
        return 'Salvando'
    parts = ['Baixando']
    downloaded = event.get('downloaded') or event.get('downloaded_bytes') or 0
    total = (
        event.get('total')
        or event.get('total_bytes')
        or event.get('total_bytes_estimate')
        or 0
    )
    if total > 0:
        parts.append(f'{downloaded/1048576:.1f} / {total/1048576:.1f} MB')
    elif downloaded > 0:
        parts.append(f'{downloaded/1048576:.1f} MB')
    speed = event.get('speed') or 0
    if speed > 0:
        parts.append(f'{speed/1048576:.2f} MB/s')
    return ' · '.join(parts)
