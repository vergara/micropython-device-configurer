import bleinterface
import asyncio
import wificonfigurer
import genericconfigurer
from daos import FileDao

def wifiConfigChanged(wifi_config):
    print("Got notification of change:")
    print(f"ssid changed: '{wifi_config['wifi_ssid']}'")
    print(f"passwd changed: '{wifi_config['wifi_password']}'")

def genericConfigChanged(generic_config):
    print(f"Got notification of change: '{generic_config}'")

async def main():
    file_storage_dao_wifi = FileDao("wifi-config.txt")
    file_storage_dao_generic = FileDao("generic-config.txt")
    ble_config_service = bleinterface.device_configurer_service
    wifi_configurer = wificonfigurer.WifiConfigurer(ble_config_service, dao=file_storage_dao_wifi, onChange=wifiConfigChanged)
    generic_configurer = genericconfigurer.GenericConfigurer(ble_config_service, dao=file_storage_dao_generic,
                                                    onChange=genericConfigChanged)
    ble = bleinterface.BleInterface([wifi_configurer, generic_configurer])
    ble.start()

    while True:
        print(f"ssid: '{wifi_configurer.wifi_config['wifi_ssid']}'")
        print(f"passwd: '{wifi_configurer.wifi_config['wifi_password']}'")
        print(f"Generic config: '{generic_configurer.generic_config}'")
        await asyncio.sleep_ms(6000)

asyncio.run(main())