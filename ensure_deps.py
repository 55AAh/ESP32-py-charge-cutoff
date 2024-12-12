_to_install = []

for _module in ['logging', 'sdcard', 'hmac']:
    try:
        exec('import ' + _module)
    except ImportError:
        _to_install.append(_module)

if _to_install:
    print('Modules not found:', _to_install)
    import network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    from credentials import Credentials
    from time import sleep
    print(f'Connecting to WiFi ({Credentials.network_ssid}): ', end='')
    wlan.connect(Credentials.network_ssid, Credentials.network_pass)
    while not wlan.isconnected():
        print('.')
        sleep(1)
    print(' ok!')

    import mip
    for _module in _to_install:
        mip.install(_module)
