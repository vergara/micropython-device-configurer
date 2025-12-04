from bluetooth import UUID
import aioble
import asyncio
import os
import machine

DEVICE_CONF_SERVICE_UUID = UUID(0x002B)
device_configurer_service = aioble.Service(DEVICE_CONF_SERVICE_UUID)

default_advertising_device_name = None
try:
    default_advertising_device_name = os.uname().machine.split()[0] + "-" + ''.join(['{:02x}'.format(b) for b in machine.unique_id()])
except Exception as e:
    default_advertising_device_name = None

_ADV_INTERVAL_US = const(250000)

class BleInterface:
    def __init__(self, device_configurations=[], advertising_device_name=None, other_services=[], other_services_uuids=[]):
        aioble.register_services(device_configurer_service, *other_services)

        self.device_configurations = device_configurations

        if advertising_device_name is not None:
            self.advertising_device_name = advertising_device_name
        elif default_advertising_device_name is not None:
            self.advertising_device_name = default_advertising_device_name
        else:
            self.advertising_device_name = "ble_capable_device"

        self.other_services_uuids = other_services_uuids
        self.connections = []

    def start(self):
        advertiser_task = asyncio.create_task(self._advertise_task())
        config_tasks = list(map(lambda config: config.start(), self.device_configurations))
        return asyncio.gather(advertiser_task, *config_tasks)

    def get_device_name(self):
        global default_advertising_device_name
        return default_advertising_device_name

    async def _advertise_task(self):
        while True:
            try:
                async with await aioble.advertise(
                        _ADV_INTERVAL_US,
                        name=self.advertising_device_name,
                        services=[DEVICE_CONF_SERVICE_UUID] + self.other_services_uuids,
                ) as connection:
                    self.connections.append(connection)
                    #print("Connection from", connection.device)
                    await connection.disconnected()
                    if connection in self.connections:
                        self.connections.remove(connection)
            except asyncio.CancelledError:
                # Catch the CancelledError
                print("Peripheral task cancelled")
            except Exception as e:
                print("Error in _advertise_task:", e)
            finally:
                # Ensure the loop continues to the next iteration
                await asyncio.sleep_ms(100)