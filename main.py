import bleinterface
import asyncio
import wificonfigurer
from daos import FileDao

def wifiConfigChanged(wifi_config):
    print("Got notification of change:")
    print(f"ssid changed: '{wifi_config['wifi_ssid']}'")
    print(f"passwd changed: '{wifi_config['wifi_password']}'")

async def main():
    file_storage_dao = FileDao("wifi-config.txt")
    ble_config_service = bleinterface.device_configurer_service
    wifi_configurer = wificonfigurer.WifiConfigurer(ble_config_service, dao=file_storage_dao, onWifiConfigChange=wifiConfigChanged)
    ble = bleinterface.BleInterface([wifi_configurer])
    ble.start()

    while True:
        print(f"ssid: '{wifi_configurer.wifi_config['wifi_ssid']}'")
        print(f"passwd: '{wifi_configurer.wifi_config['wifi_password']}'")
        await asyncio.sleep_ms(5000)

asyncio.run(main())