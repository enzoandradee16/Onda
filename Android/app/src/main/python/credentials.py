"""Android credential adapter: encrypted storage is owned by Android Keystore."""
import json

class CredentialError(ValueError):
    pass

class CredentialStore:
    def __init__(self, path):
        self.key = str(path).split('/')[-1]

    def load(self):
        from java import jclass
        text = jclass('br.com.onda.mobile.SecureVault').get(self.key)
        return tuple(json.loads(text)) if text else None

    def save(self, client_id, secret):
        from java import jclass
        jclass('br.com.onda.mobile.SecureVault').put(self.key, json.dumps([client_id, secret]))

    def forget(self):
        from java import jclass
        jclass('br.com.onda.mobile.SecureVault').remove(self.key)
