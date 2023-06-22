from bluepy import btle 
import time

SCAN_TIME_SEC = 5.0
MAX_VIBE = 20
TOY = None
SKIP_UNAMED = True
CURRENT_VIBE_LEVEL = 0

def scan():
    results = set()
    scanner = btle.Scanner()
    devices = scanner.scan(SCAN_TIME_SEC)
    for device in devices:
        name = None
        for (adtype, desc, value) in device.getScanData():
            if desc == "Complete Local Name":
                name = str(value)
                break

        if SKIP_UNAMED and name is None:
            continue
        elif name is None:
            name = '[No name specified]'
        
        results.add((device.addr, name))

    return list(results)

def connect(device_id, uuid = None):
    peripheral = None
    try:
        peripheral = btle.Peripheral(device_id, 'random')
    except:
        try:
            peripheral = btle.Peripheral(device_id)
        except:
            return None
            
    if uuid:
        global TOY
        TOY = peripheral.getCharacteristics(uuid = btle.UUID(uuid))[0]
        if not TOY:
            return None
        
    return peripheral

def vibe(level):
    global CURRENT_VIBE_LEVEL
    CURRENT_VIBE_LEVEL = level
    
    if TOY:
        TOY.write(f'Vibrate:{level}'.encode('ascii'))
    else:
        print(f'DEBUG: Not connected to send level {level}')
        
def stop():
    vibe(0)

def is_vibrating():
    return 0 != CURRENT_VIBE_LEVEL
