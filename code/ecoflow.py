import hmac
import random
from collections import OrderedDict

import aiohttp

from clock import Clock
from credentials import Credentials


class EcoflowApi:
    _session = aiohttp.ClientSession("https://api.ecoflow.com/iot-open/sign/device")

    class EcoflowApiException(Exception):
        pass

    def __init__(self, access_key: str, secret_key: str):
        self._access_key = access_key
        self._secret_key = secret_key

    @staticmethod
    def _flatten_json_body(json_value, into_dict: dict, full_key=""):
        # Top level object must be dict
        assert full_key is not None or isinstance(json_value, dict)

        if isinstance(json_value, int) or isinstance(json_value, str):
            into_dict[full_key] = json_value

        elif isinstance(json_value, dict):
            for child_key, child_value in json_value.items():
                if full_key:
                    child_full_key = full_key + "." + child_key
                else:
                    child_full_key = child_key
                EcoflowApi._flatten_json_body(child_value, into_dict, child_full_key)

        elif isinstance(json_value, list):
            for i, child_value in enumerate(json_value):
                child_full_key = full_key + "[" + str(i) + "]"
                EcoflowApi._flatten_json_body(child_value, into_dict, child_full_key)

        else:
            raise ValueError("Wrong query parameter type:", type(json_value))

    def _stringify_query(
        self,
        nonce: int,
        timestamp: int,
        json_body=None,
        query_params=None,
    ) -> str:
        # Collect all params from json body
        all_params: dict[str, str] = dict()
        self._flatten_json_body(json_body or {}, all_params)

        # Add optional explicit query params:
        all_params.update(query_params or {})

        # Sort alphabetically
        # noinspection PyTypeChecker
        all_params = OrderedDict(sorted(OrderedDict(all_params).items()))

        # Add mandatory params
        all_params["accessKey"] = self._access_key
        all_params["nonce"] = str(nonce)
        all_params["timestamp"] = str(timestamp)

        # Convert to query string
        quoted_params_list = []
        for key, value in all_params.items():
            quoted_params_list.append(key + "=" + str(value))
        query_str = "&".join(quoted_params_list)

        return query_str

    def _sign_query(self, query_str: str) -> str:
        digest = hmac.new(
            self._secret_key.encode(), msg=query_str.encode(), digestmod="sha256"
        )
        digest_hex = digest.hexdigest()
        return digest_hex

    class DeviceOffline(EcoflowApiException):
        pass

    async def _make_request(
        self,
        method: str,
        api_func: str,
        json_body=None,
        query_params=None,
    ) -> dict:
        url = f"/{api_func}"

        if query_params:
            url += "?" + "&".join([f"{k}={str(v)}" for k, v in query_params.items()])

        nonce = random.randint(100000, 999999)
        timestamp = Clock.get_unix_time_ms()

        query_str = self._stringify_query(nonce, timestamp, json_body, query_params)
        sign = self._sign_query(query_str)

        headers = {
            "accessKey": self._access_key,
            "nonce": str(nonce),
            "timestamp": str(timestamp),
            "sign": sign,
        }

        async with self._session.request(
            method.upper(), url, headers=headers, json=json_body
        ) as response:
            result_json: dict = await response.json()

        if result_json.get("code") == "1000":
            raise self.DeviceOffline
        assert result_json.get("code") == "0", result_json
        assert result_json.get("message") == "Success", result_json
        data = result_json.get("data", None)
        return data or {}

    async def get_devices_list(self):
        devices = await self._make_request("get", "list")
        return devices or []


class EcoflowDeviceApi(EcoflowApi):
    def __init__(self, access_key: str, secret_key: str, sn: str):
        super().__init__(access_key, secret_key)
        self._sn = sn

    class DeviceNotLinked(EcoflowApi.EcoflowApiException):
        pass

    async def is_online(self) -> bool:
        devices = await self.get_devices_list()
        for device in devices:
            if device["sn"] == self._sn:
                online = bool(device["online"])
                return online
        raise self.DeviceNotLinked

    async def get_all_params(self) -> dict:
        data = await self._make_request(
            "get", "quota/all", query_params={"sn": self._sn}
        )
        return data

    async def get_params(self, param_names: list):
        json_body = {
            "sn": self._sn,
            "params": {
                "quotas": param_names,
            },
        }
        data = await self._make_request("post", "quota", json_body=json_body)
        return data

    class ModuleType:
        PD = 1
        BMS = 2
        INV = 3
        BMS_SLAVE = 4
        MPPT = 5

    async def set_params(self, module_type: int, operate_type: str, params: dict):
        json_body = {
            "sn": self._sn,
            "moduleType": module_type,
            "operateType": operate_type,
            "params": params,
        }
        await self._make_request("put", "quota", json_body)


class Delta2:
    def __init__(self, api: EcoflowDeviceApi):
        self._api = api

    async def is_online(self) -> bool:
        online = await self._api.is_online()
        return online

    async def get_ac_enabled(self) -> bool:
        param = "mppt.cfgAcEnabled"
        data = await self._api.get_params([param])
        value = data[param]
        return value == 1

    async def set_ac_enabled(self, enabled: bool):
        await self._api.set_params(
            self._api.ModuleType.MPPT,
            "acOutCfg",
            {
                "enabled": int(enabled),
                "xboost": 0,
                "out_voltage": 230,
                "out_freq": 50,
            },
        )

    async def charging_line_plugged(self) -> bool:
        param = "bms_emsStatus.chgLinePlug"
        data = await self._api.get_params([param])
        value = data[param]
        return value == 1

    async def is_charging(self) -> bool:
        param = "bms_bmsStatus.chgState"
        data = await self._api.get_params([param])
        value = data[param]
        return value != 0

    async def remaining_time_minutes(self) -> int:
        param = "pd.remainTime"
        data = await self._api.get_params([param])
        value = int(data[param])
        return value

    async def soc(self) -> int:
        param = "pd.soc"
        data = await self._api.get_params([param])
        value = int(data[param])
        return value

    async def battery_status(self) -> dict:
        params = [
            "bms_bmsStatus.chgState",
            "pd.remainTime",
            "pd.soc",
        ]
        data = await self._api.get_params(params)
        values = {
            "is_charging": data["bms_bmsStatus.chgState"] != 0,
            "remaining_time_minutes": int(data["pd.remainTime"]),
            "soc": int(data["pd.soc"]),
        }
        return values


device_api = EcoflowDeviceApi(
    access_key=Credentials.ecoflow_access_key,
    secret_key=Credentials.ecoflow_secret_key,
    sn=Credentials.ecoflow_sn,
)
delta2 = Delta2(device_api)
