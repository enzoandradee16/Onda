"""Windows current-user DPAPI storage. Never falls back to plaintext."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import tempfile


class CredentialError(ValueError):
    pass


def _crypt(data, decrypt=False):
    if os.name != "nt":
        raise CredentialError("Salvar credenciais está disponível apenas no Windows. Use os campos durante a sessão.")

    class Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]

    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    function = crypt32.CryptUnprotectData if decrypt else crypt32.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p if decrypt else wintypes.LPCWSTR,
                        ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    target = Blob()
    try:
        # UI_FORBIDDEN only: no LOCAL_MACHINE flag, so protection is per Windows user.
        if not function(ctypes.byref(source), None if decrypt else "Onda Spotify", None,
                        None, None, 1, ctypes.byref(target)):
            raise CredentialError("O Windows não conseguiu acessar as credenciais protegidas. "
                                  "Use a mesma conta do Windows ou salve as credenciais novamente.")
        return ctypes.string_at(target.data, target.size)
    finally:
        ctypes.memset(buffer, 0, len(buffer))
        if target.data:
            ctypes.memset(target.data, 0, target.size)
            kernel32.LocalFree(ctypes.cast(target.data, ctypes.c_void_p))


class CredentialStore:
    def __init__(self, path=None):
        local = os.environ.get("LOCALAPPDATA")
        self.path = Path(path) if path is not None else (Path(local) / "Onda" / "spotify.dpapi" if local else None)

    def load(self):
        if self.path is None or not self.path.exists():
            return None
        try:
            encrypted = self.path.read_bytes()
            if len(encrypted) > 65536:
                raise CredentialError("O arquivo de credenciais é inválido. Salve-as novamente.")
            record = json.loads(_crypt(encrypted, decrypt=True).decode("utf-8"))
            if (not isinstance(record, dict) or record.get("version") != 1
                    or not isinstance(record.get("client_id"), str) or not record["client_id"]
                    or not isinstance(record.get("client_secret"), str) or not record["client_secret"]):
                raise CredentialError("O arquivo de credenciais é inválido. Salve-as novamente.")
            return record["client_id"], record["client_secret"]
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise CredentialError("Não foi possível ler as credenciais salvas. Salve-as novamente.") from None

    def save(self, client_id, client_secret):
        client_id, client_secret = client_id.strip(), client_secret.strip()
        if not client_id or not client_secret:
            raise CredentialError("Preencha Client ID e Client Secret antes de salvar.")
        if len(client_id) > 4096 or len(client_secret) > 4096:
            raise CredentialError("Credenciais muito longas. Confira os campos.")
        if self.path is None:
            raise CredentialError("A pasta de dados do Windows não está disponível.")
        data = json.dumps({"version": 1, "client_id": client_id, "client_secret": client_secret}).encode("utf-8")
        encrypted = _crypt(data)
        temporary = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=self.path.parent, prefix="spotify-", suffix=".tmp", delete=False) as output:
                temporary = Path(output.name)
                output.write(encrypted)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, self.path)
        except OSError:
            raise CredentialError("Não foi possível salvar as credenciais na pasta do Onda.") from None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def forget(self):
        try:
            if self.path is not None:
                self.path.unlink(missing_ok=True)
        except OSError:
            raise CredentialError("Não foi possível remover as credenciais salvas.") from None
