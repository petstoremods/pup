from bluepy import btle 
import time

MAX_VIBE = 20
DEVICE = "CD:2D:06:2E:C8:66"
UUID = "5a300002-0023-4bd4-bbd5-a6920e4c5653"
TOY = None

def connect():
    global TOY
    peripheral = None
    while True:
        try:
            peripheral = btle.Peripheral(DEVICE, "random")
            break
        except:
            time.sleep(1)
    
    TOY = peripheral.getCharacteristics(uuid = btle.UUID(UUID))[0]

def vibe(level):
    TOY.write(f'Vibrate:{level}'.encode('ascii'))
        
def stop():
    vibe(0)

