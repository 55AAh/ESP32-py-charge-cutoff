import hmac
import binascii
import hashlib
import json

import aiohttp

from clock import Clock
from credentials import Credentials


class TuyaApi:
    _session = aiohttp.ClientSession("https://openapi.tuyaeu.com")

    class TuyaApiException(Exception):
        pass

    def __init__(self, access_id: str, access_key: str):
        self._access_id = access_id
        self._access_key = access_key
        self._access_token = None

    @classmethod
    # --- CRYPTO HELPERS ---
    def _sha256_hex(cls, data):
        return binascii.hexlify(hashlib.sha256(data.encode("utf-8")).digest()).decode(
            "utf-8"
        )

    @classmethod
    def _hmac_sha256_hex(cls, key, msg):
        return (
            binascii.hexlify(
                hmac.new(
                    key.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256
                ).digest()
            )
            .decode("utf-8")
            .upper()
        )

    # --- SIGNATURE CALCULATION (The Hard Part) ---
    def _calc_sign(self, method, url, body_str, token=""):
        t = Clock.get_unix_time_ms()

        # 1. Calculate Content-SHA256
        # If body is empty, hash an empty string
        content_sha256 = self._sha256_hex(body_str)

        # 2. Build "String to Sign"
        # Format: METHOD + \n + Content-SHA256 + \n + Headers + \n + URL
        # We use minimal headers, so the middle part is just \n\n
        string_to_sign = f"{method}\n{content_sha256}\n\n{url}"

        # 3. Sign it
        # Format: AccessID + Token + t + StringToSign
        str_to_encrypt = f"{self._access_id}{token}{t}{string_to_sign}"
        sign = self._hmac_sha256_hex(self._access_key, str_to_encrypt)

        return sign, t

    async def _send_request_with_token(
        self, method: str, url: str, json_body: dict | None = None, token: str = ""
    ):
        if json_body is None:
            body_str = ""
        else:
            body_str = json.dumps(json_body)

        # Calculate Signature
        sign, t = self._calc_sign(method, url, body_str, token)

        headers = {
            "t": t,
            "sign_method": "HMAC-SHA256",
            "client_id": self._access_id,
            "sign": sign,
            "access_token": token,
            "Content-Type": "application/json",
        }

        async with self._session.request(
            method.upper(), url, headers=headers, json=json_body
        ) as response:
            result_json = await response.json()

        if not result_json.get("success"):
            raise self.TuyaApiException(result_json)
        return result_json

    async def _send_request(self, method: str, url: str, body: dict | None = None):
        if self._access_token is None:
            # Get token
            token_response = await self._send_request_with_token(
                "GET", "/v1.0/token?grant_type=1"
            )
            self._access_token = token_response["result"]["access_token"]

        response = await self._send_request_with_token(
            method, url, body, self._access_token
        )
        return response


class TuyaDeviceApi:
    def __init__(self, api: TuyaApi, device_id: str):
        self._api = api
        self._device_id = device_id

    async def send_commands(self, commands: list[dict]):
        response = await self._api._send_request(
            "POST",
            f"/v1.0/iot-03/devices/{self._device_id}/commands",
            {"commands": commands},
        )
        return response


class TuyaSwitch(TuyaDeviceApi):
    async def set_switch(self, switch_on: bool):
        response = await self.send_commands([{"code": "switch", "value": switch_on}])
        return response


api = TuyaApi(Credentials.tuya_access_id, Credentials.tuya_access_key)
tuya_switch = TuyaSwitch(api, Credentials.tuya_device_id)
