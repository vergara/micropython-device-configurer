from bluetooth import UUID
import aioble
import asyncio
import json
from daos import InMemoryDao

_BLE_GENERIC_CONF_CHARACTERISTIC_UUID = UUID('19b10002-e8f2-537e-4f6c-d104768a1215')

def sanitize_data(data):
    return data.strip()

class GenericConfigurer:
    def __init__(self, ble_configuration_service, dao=None, onChange=None):
        self.generic_configurer_characteristic = aioble.BufferedCharacteristic(ble_configuration_service,
                                                                    _BLE_GENERIC_CONF_CHARACTERISTIC_UUID, read=True,
                                                                    write=True, notify=True, capture=True, max_len=1024)
        self.dao = dao
        if self.dao is None:
            self.dao = InMemoryDao()

        self.onChange = onChange

        self.generic_config = {}

        data = self.dao.retrieve_raw_data()
        self.generic_config = self._parse_data(data)

        if self.onChange is not None:
            self.onChange(self.generic_config)

    def start(self):
        data = self.dao.retrieve_raw_data()
        if data is not None and len(data) > 1:
            binary_data = data.encode('utf-8')
            self.generic_configurer_characteristic.write(binary_data, send_update=False)

        return asyncio.create_task(self._wait_for_write())

    async def _wait_for_write(self):
        while True:
            try:
                connection, data = await self.generic_configurer_characteristic.written()
                print('Received data: ', data)
                data = data.decode()
                print('Decoded data: ', data)
                data = sanitize_data(data)
                #print('Sanitized data: ', data)

                previous_config_state = json.loads(json.dumps(self.generic_config))

                self.generic_config = self._parse_data(data)

                if self.generic_config != previous_config_state:
                    self.dao.save_raw_data(data)
                    if self.onChange is not None:
                        #print(f"Doing change. onChange: {self.onChange}. previous_config_state: {previous_config_state}. self.generic_config: {self.generic_config}")
                        self.onChange(self.generic_config)

                # Write it to make it readily available to ble client reads
                # Note that what's written has been sanitized
                self.generic_configurer_characteristic.write(data.encode('utf-8'), send_update=True)
            except asyncio.CancelledError:
                # Catch the CancelledError
                print("Generic Configurer task cancelled")
            except Exception as e:
                print("Error in _wait_for_write:", e)

    # Requires sanitized data
    def _parse_data(self, data):
        result = self.generic_config
        if len(data) == 0:
            return result

        try:
            result = json.loads(data)
        except Exception as e:
            print(f"Failed to parse json data: {e}\ndata: '{data}'")

        return result