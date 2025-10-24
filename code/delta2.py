from ecoflow_api import EcoflowDeviceApi


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
                "xboost": 1,
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

    async def remain_time_minutes(self) -> int:
        param = "pd.remainTime"
        data = await self._api.get_params([param])
        value = data[param]
        return value
