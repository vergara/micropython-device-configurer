from bluetooth import UUID
import aioble
import asyncio
import json
from daos import InMemoryDao

_BLE_WIFI_CONF_CHARACTERISTIC_UUID = UUID('19b10002-e8f2-537e-4f6c-d104768a1214')

def sanitize_data(data):
    return data.strip()

class WifiConfigurer:
    def __init__(self, ble_configuration_service, dao=None, onChange=None):
        self.wifi_configurer_characteristic = aioble.BufferedCharacteristic(ble_configuration_service,
                                                                    _BLE_WIFI_CONF_CHARACTERISTIC_UUID, read=True,
                                                                    write=True, notify=True, capture=True, max_len=512)
        self.dao = dao
        if self.dao is None:
            self.dao = InMemoryDao()

        self.onChange = onChange

        self.wifi_config = {"wifi_ssid": None, "wifi_password": None}

        data = self.dao.retrieve_raw_data()
        self.wifi_config = self._parse_data(data)

        if self.onChange is not None:
            self.onChange(self.wifi_config)

    def start(self):
        data = self.dao.retrieve_raw_data()
        if data is not None and len(data) > 1:
            binary_data = data.encode('utf-8')
            self.wifi_configurer_characteristic.write(binary_data, send_update=False)

        return asyncio.create_task(self._wait_for_write())

    async def _wait_for_write(self):
        while True:
            try:
                connection, data = await self.wifi_configurer_characteristic.written()
                print('Received data: ', data)
                data = data.decode()
                print('Decoded data: ', data)
                data = sanitize_data(data)
                #print('Sanitized data: ', data)

                previous_config_state = json.loads(json.dumps(self.wifi_config))

                self.wifi_config = self._parse_data(data)

                if self.wifi_config != previous_config_state:
                    self.dao.save_raw_data(data)
                    if self.onChange is not None:
                        #print(f"Doing change. onChange: {self.onChange}. previous_config_state: {previous_config_state}. self.wifi_config: {self.wifi_config}")
                        self.onChange(self.wifi_config)

                # Write it to make it readily available to ble client reads
                # Note that what's written has been sanitized
                self.wifi_configurer_characteristic.write(data.encode('utf-8'), send_update=True)
            except asyncio.CancelledError:
                # Catch the CancelledError
                print("WIFI-Configurer task cancelled")
            except Exception as e:
                print("Error in _wait_for_write:", e)

    # Requires sanitized data
    def _parse_data(self, data):
        result = {}
        if len(data) == 0:
            result["wifi_ssid"] = None
            result["wifi_password"] = None
            return result

        tokens = data.split()
        result["wifi_ssid"] = tokens[0]

        result["wifi_password"] = None
        if len(tokens) > 1:
            result["wifi_password"] = " ".join(tokens[1:])

        return result