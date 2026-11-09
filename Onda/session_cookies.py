"""Read protected Instagram sessions into memory; never export plaintext files."""

import io
from pathlib import Path

HEADER = b'ONDA-IG-DPAPI\0'
ANDROID_VAULT = 'onda-vault:instagram'


def cookie_source(source):
    if source == ANDROID_VAULT:
        from java import jclass
        text = jclass('br.com.onda.mobile.SecureVault').get('instagram-session')
        if not text:
            raise ValueError('Atualize a sessão do Instagram em Configurações → Contas.')
        return io.StringIO(str(text))
    if source and str(source).endswith('instagram-session.dpapi'):
        from credentials import _crypt
        data = Path(source).read_bytes()
        if not data.startswith(HEADER) or len(data) > 2 * 1024 * 1024:
            raise ValueError('Atualize a sessão do Instagram em Configurações → Contas.')
        return io.StringIO(_crypt(data[len(HEADER):], decrypt=True).decode('utf-8'))
    return source


def migrate_windows_session(root):
    """Encrypt an existing opted-in session before removing its legacy copy."""
    root = Path(root)
    plain, protected = root / 'instagram-session.txt', root / 'instagram-session.dpapi'
    if plain.is_file():
        from credentials import _crypt
        data = plain.read_bytes()
        if len(data) > 2 * 1024 * 1024 or not data.startswith(b'# Netscape HTTP Cookie File'):
            raise ValueError('Atualize a sessão do Instagram em Configurações → Contas.')
        temporary = protected.with_suffix('.dpapi.tmp')
        try:
            temporary.write_bytes(HEADER + _crypt(data))
            temporary.replace(protected)
            plain.unlink()
        finally:
            temporary.unlink(missing_ok=True)
    return protected if protected.is_file() else None
