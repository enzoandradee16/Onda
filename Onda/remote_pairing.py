"""Local pairing QR: short-lived code, never a permanent bearer credential."""

import base64
import io
from urllib.parse import urlencode


def pairing_payload(address, code):
    return 'onda://pair?' + urlencode(dict(address=address, code=code))


def pairing_qr(address, code):
    import qrcode

    image = qrcode.make(pairing_payload(address, code), box_size=6, border=4)
    output = io.BytesIO()
    image.save(output, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(output.getvalue()).decode(
        'ascii'
    )
