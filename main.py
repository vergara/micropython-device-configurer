import bleinterface
import asyncio

def wifiConfigChanged(wifi_config):
    print("Got notification of change:")
    print(f"ssid changed: {wifi_config['wifi_ssid']}")
    print(f"passwd changed: {wifi_config['wifi_password']}")

async def main():
    file_storage_dao = bleinterface.FileDao("wifi-config.txt")
    ble = bleinterface.BleInterface(dao=file_storage_dao, onWifiConfigChange=wifiConfigChanged)
    ble.start()

    while True:
        print(f"ssid: {ble.dao.wifi_config['wifi_ssid']}")
        print(f"passwd: {ble.dao.wifi_config['wifi_password']}")
        await asyncio.sleep_ms(5000)

asyncio.run(main())