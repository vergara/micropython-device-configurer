from bluetooth import UUID
import aioble
import asyncio
import os
import machine
import json

_WIFI_CONF_SERVICE_UUID = UUID(0x181A)
_BLE_WIFI_CONF_CHARACHTERISTIC_UUID = UUID('19b10002-e8f2-537e-4f6c-d104768a1214')

_ADV_INTERVAL_US = const(250000)

wifi_configurer_service = aioble.Service(_WIFI_CONF_SERVICE_UUID)
wifi_configurer_characteristic = aioble.Characteristic(wifi_configurer_service, _BLE_WIFI_CONF_CHARACHTERISTIC_UUID, read=True, write=True, notify=True, capture=True)

aioble.register_services(wifi_configurer_service)

default_advertising_device_name = None
try:
    default_advertising_device_name = os.uname().machine.split()[0] + "-" + ''.join(['{:02x}'.format(b) for b in machine.unique_id()])
except Exception as e:
    default_advertising_device_name = None

class BleInterface:
    def __init__(self, dao=None, advertising_device_name=None, onWifiConfigChange=None):
        if dao is None:
            self.dao = InMemoryDao()
        else:
            self.dao = dao

        self.dao.initialize_dao()

        if advertising_device_name is not None:
            self.advertising_device_name = advertising_device_name
        elif default_advertising_device_name is not None:
            self.advertising_device_name = default_advertising_device_name
        else:
            self.advertising_device_name = "ble_capable_device"

        self.onWifiConfigChange = onWifiConfigChange
        self.connections = []

        data = self.dao.retrieve_raw_data()
        binary_data = data.encode('utf-8')
        # You can write to the characteristic before bluetooth is even turned on and advertising
        wifi_configurer_characteristic.write(binary_data, send_update=False)

    def start(self):
        advertiser_task = asyncio.create_task(self._advertise_task())
        ble_write_task = asyncio.create_task(self._wait_for_write())
        return asyncio.gather(advertiser_task, ble_write_task)


    async def _advertise_task(self):
        while True:
            try:
                async with await aioble.advertise(
                        _ADV_INTERVAL_US,
                        name=self.advertising_device_name,
                        services=[_WIFI_CONF_SERVICE_UUID],
                ) as connection:
                    self.connections.append(connection)
                    print("Connection from", connection.device)
                    await connection.disconnected()
                    if connection in self.connections:
                        self.connections.remove(connection)
            except asyncio.CancelledError:
                # Catch the CancelledError
                print("Peripheral task cancelled")
            except Exception as e:
                print("Error in advertise_task:", e)
            finally:
                # Ensure the loop continues to the next iteration
                await asyncio.sleep_ms(100)

    async def _wait_for_write(self):
        while True:
            try:
                connection, data = await wifi_configurer_characteristic.written()
                #print('Received data: ', data)
                data = data.decode()
                #print('Decoded data: ', data)
                data = self.dao.sanitize_data(data)
                #print('Sanitized data: ', data)

                previous_config_state = json.loads(json.dumps(self.dao.wifi_config))
                self.dao.save_raw_data(data)

                # Write it to make it readily available to ble client reads
                encodedBinaryData = data.encode('utf-8')
                wifi_configurer_characteristic.write(encodedBinaryData, send_update=True)

                if self.onWifiConfigChange is not None and self.dao.wifi_config != previous_config_state:
                    #print(f"Doing change. onWifiConfigChange: {self.onWifiConfigChange}. previous_config_state: {previous_config_state}. self.dao.wifi_config: {self.dao.wifi_config}")
                    self.onWifiConfigChange(self.dao.wifi_config)
            except asyncio.CancelledError:
                # Catch the CancelledError
                print("Peripheral task cancelled")
            except Exception as e:
                print("Error in wait_for_write:", e)
            finally:
                # Ensure the loop continues to the next iteration
                await asyncio.sleep_ms(10)

class InMemoryDao:
    def __init__(self):
        self.wifi_config = {"wifi_ssid": None, "wifi_password": None}

    def initialize_dao(self):
        self._parse_data(self.sanitize_data(self.retrieve_raw_data()))

    def sanitize_data(self, data):
        return data.strip()

    # Requires sanitized data
    # This method is final and should be called by save_raw_data
    def _parse_data(self, data):
        if len(data) == 0:
            self.wifi_config["wifi_ssid"] = None
            self.wifi_config["wifi_password"] = None
            return

        tokens = data.split()
        self.wifi_config["wifi_ssid"] = tokens[0]
        if len(tokens) > 1:
            self.wifi_config["wifi_password"] = " ".join(tokens[1:])

    def save_raw_data(self, data):
        data = self.sanitize_data(data)
        self._parse_data(data)

    def retrieve_raw_data(self):
        data = " ".join([self.wifi_config["wifi_ssid"] or "", self.wifi_config["wifi_password"] or ""]).strip()
        return data

class FileDao(InMemoryDao):
    def __init__(self, file_name):
        InMemoryDao.__init__(self)
        self.file_name = file_name

    def save_raw_data(self, data):
        data = self.sanitize_data(data)
        self._parse_data(data)
        with open(self.file_name, "w") as storage_file:
            storage_file.write(data)

    def retrieve_raw_data(self):
        try:
            with open(self.file_name, "r") as storage_file:
                file_content = storage_file.readlines()
                #print(f"file_content: {file_content}")
                if len(file_content) > 1:
                    print(f"Warning: found {len(file_content)} lines in storage file for wifi config. Expected was 1.")
                if len(file_content) == 0:
                    # No config found
                    return ""
                return file_content[0]
        except Exception as e:
            print("Failed to read wifi config file:", e)
            return ""