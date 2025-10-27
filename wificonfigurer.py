from bluetooth import UUID
import aioble
import asyncio
import json
from daos import InMemoryDao

_BLE_WIFI_CONF_CHARACTERISTIC_UUID = UUID('19b10002-e8f2-537e-4f6c-d104768a1214')

def sanitize_data(data):
    return data.strip()

class WifiConfigurer:
    def __init__(self, ble_configuration_service, dao=None, onWifiConfigChange=None):
        self.wifi_configurer_characteristic = aioble.Characteristic(ble_configuration_service,
                                                                    _BLE_WIFI_CONF_CHARACTERISTIC_UUID, read=True,
                                                                    write=True, notify=True, capture=True)
        if dao is None:
            self.dao = InMemoryDao()
        else:
            self.dao = dao

        self.onWifiConfigChange = onWifiConfigChange

        self.wifi_config = {"wifi_ssid": None, "wifi_password": None}

        data = self.dao.retrieve_raw_data()
        self.wifi_config = self._parse_data(data)

        if self.onWifiConfigChange is not None:
            self.onWifiConfigChange(self.wifi_config)

        if data is not None and len(data) > 1:
            binary_data = data.encode('utf-8')
            # You can write to the characteristic before bluetooth is even turned on and advertising
            # We write the current config to make it accessible via bluetooth
            self.wifi_configurer_characteristic.write(binary_data, send_update=False)

    def start(self):
        return asyncio.create_task(self._wait_for_write())

    async def _wait_for_write(self):
        while True:
            try:
                connection, data = await self.wifi_configurer_characteristic.written()
                #print('Received data: ', data)
                data = data.decode()
                #print('Decoded data: ', data)
                data = sanitize_data(data)
                #print('Sanitized data: ', data)

                previous_config_state = json.loads(json.dumps(self.wifi_config))
                self.dao.save_raw_data(data)

                self.wifi_config = self._parse_data(data)
                
                # Write it to make it readily available to ble client reads
                encodedBinaryData = data.encode('utf-8')
                self.wifi_configurer_characteristic.write(encodedBinaryData, send_update=True)

                if self.onWifiConfigChange is not None and self.wifi_config != previous_config_state:
                    #print(f"Doing change. onWifiConfigChange: {self.onWifiConfigChange}. previous_config_state: {previous_config_state}. self.wifi_config: {self.wifi_config}")
                    self.onWifiConfigChange(self.wifi_config)
            except asyncio.CancelledError:
                # Catch the CancelledError
                print("WIFI-Configurer task cancelled")
            except Exception as e:
                print("Error in _wait_for_write:", e)
            finally:
                # Ensure the loop continues to the next iteration
                await asyncio.sleep_ms(10)

    # Requires sanitized data
    # This method is final and should be called by save_raw_data
    def _parse_data(self, data):
        result = {}
        if len(data) == 0:
            result["wifi_ssid"] = None
            result["wifi_password"] = None
            return result

        tokens = data.split()
        result["wifi_ssid"] = tokens[0]
        if len(tokens) > 1:
            result["wifi_password"] = " ".join(tokens[1:])

        return result