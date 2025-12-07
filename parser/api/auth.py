import hashlib


class OKAuth:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        access_token: str = "",
        public_key: str = "",
        session_key: str = "",
        session_secret_key: str = "",
    ):
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token = access_token
        self._public_key = public_key
        self._session_key = session_key
        self._session_secret_key = session_secret_key

    @property
    def application_key(self) -> str:
        return self._public_key or self._client_id

    def generate_sig(self, params: dict) -> str:
        if self._session_secret_key:
            secret_key = self._session_secret_key
        elif self._session_key:
            secret_key = self._calc_secret(self._session_key)
        else:
            secret_key = self._calc_secret(self._access_token)
        
        sorted_params = sorted(params.items())
        params_str = "".join(f"{k}={v}" for k, v in sorted_params)
        
        sig_string = f"{params_str}{secret_key}"
        return hashlib.md5(sig_string.encode("utf-8")).hexdigest().lower()

    def _calc_secret(self, token: str) -> str:
        secret_string = f"{token}{self._client_secret}"
        return hashlib.md5(secret_string.encode("utf-8")).hexdigest().lower()

    def sign_params(self, params: dict) -> dict:
        signed_params = params.copy()
        signed_params["application_key"] = self.application_key
        signed_params["sig"] = self.generate_sig(signed_params)
        
        if self._session_key:
            signed_params["session_key"] = self._session_key
        elif self._access_token:
            signed_params["access_token"] = self._access_token
        
        return signed_params
