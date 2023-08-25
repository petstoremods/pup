#!/usr/bin/python3

import argparse
import Plug
import scanner
import time
import subprocess, sys, os
from simple_term_menu import TerminalMenu
from termcolor import colored
import graceful_kill

LOVENSE_ONLY = True
HOME = os.path.expanduser('~')

# probably should use a real database at some point, but this program is just a hack
GAMES_FILE_PATH = f'{HOME}/.pup_gamelist'
DEVICES_FILE_PATH = f'{HOME}/.pup_devices'

def fatal(message):
    print(colored(message, 'red'))
    sys.exit(1)

def menu(options):
    if 0 == len(options):
        fatal('Oops, no options. Use fetch to configure one.')
    
    option = TerminalMenu(options).show()
    print(f'> {options[option]}')
    return option
    
def save_list(path, things):
    open(path, 'w').write('\n'.join(things))

def load_list(path):
    return [thing for thing in open(path).read().split('\n') if thing != '']

def read_name(message):
    name = input(message)
    if ' ' in name:
        fatal('Value cannot have whitespace')

    return name

GAMES = load_list(GAMES_FILE_PATH)
GAME_NAMES = list(map(lambda game_line: game_line.split('|')[0], GAMES))
DEVICES = load_list(DEVICES_FILE_PATH)
DEVICE_NAMES = list(map(lambda dev_line: dev_line.split()[0], DEVICES))

def game_from_name(game_name):
    return GAMES[GAME_NAMES.index(game_name)]

def game_offset_list(game):
    return game.split('|')[1:]

def confirm():
    return 0 == menu(['Yes', 'No'])

def try_get_pid(process_name):
    try:
        return subprocess.check_output(['pgrep', process_name])
    except:
        return None

def scan_for_running_games():
    matches = []
    for game in GAME_NAMES:
        match = try_get_pid(game)
        if match:
            try:
                matches.append((game, int(match)))
            except:
                fatal('Multiple matches found. Reconfigure game to be more specific')

    return matches

def create_vibrate_on_update(intensity):
    def generated(new_value):
        Plug.vibe(intensity)
        time.sleep(1)
        Plug.stop()

    return generated

create_vibrate_to_diff_old_value = None
def create_vibrate_to_diff():
    def generated(new_value):
        global create_vibrate_to_diff_old_value

        new_int = scanner.get_int_from_bytes(new_value)
        if create_vibrate_to_diff_old_value:
            delta = new_int - create_vibrate_to_diff_old_value
            if delta < 0:
                delta = 1
            diff = min(delta, Plug.MAX_VIBE)
            Plug.vibe(diff)
        else:
            Plug.vibe(1)

        create_vibrate_to_diff_old_value = new_int
        time.sleep(1)
        Plug.stop()

    return generated

create_last_cont_value_old_value = None
def create_last_cont_value():
    def generated(new_value):
        global create_last_cont_value_old_value

        new_int = scanner.get_int_from_bytes(new_value)
        if create_last_cont_value_old_value:
            delta = new_int - create_last_cont_value_old_value
            if delta < 0:
                delta = 1
            diff = min(delta, Plug.MAX_VIBE)
            Plug.vibe(diff)
        else:
            Plug.vibe(1)

        create_last_cont_value_old_value = new_int
        time.sleep(1)

    return generated



def create_vibrate_until_update(intensity):
    def generated(new_value):
        if Plug.is_vibrating():
            Plug.stop()
        else:
            Plug.vibe(intensity)

    return generated

def get_intensity():
    print('Intensity?')
    return menu(list(map(lambda val: str(val), range(1, 21)))) + 1

def get_uuid_from_characteristic(characteristic):
    c_str = str(characteristic)
    return c_str[c_str.find('<')+1:c_str.find('>')]

def fetch_device():
    print('Scanning for devices...')
    devices_and_names = Plug.scan()
    if LOVENSE_ONLY:
        devices_and_names = list(filter(lambda device_and_name: 'LVS' in device_and_name[1], devices_and_names))

    device_names = list(map(lambda device_and_name: f'{device_and_name[1]}: {device_and_name[0]}', devices_and_names))
        
    print('Which device ID?' if len(device_names) != 0 else 'No devices found')
    device_index = menu(["Rescan", "Manual"] + device_names)
    if 0 == device_index:
        fetch_device()
    elif 1 == device_index:
        device = input('Device ID: ')
    else:
        device = devices_and_names[device_index - 2][0]

    print(f'connecting to {device}') 
    peripheral = Plug.connect(device)
    if not peripheral:
        fatal('Failed to connect')

    uuid = None
    if LOVENSE_ONLY:
        characteristics = peripheral.getCharacteristics()
        entry_set = set()
        for entry in characteristics:
            entry_string = str(entry)
            if '-' not in entry_string:
                continue

            # might be a fluke that both of my toys had duplicate entries, but finding this seems to be the key to the right uuid
            if entry_string in entry_set:
                uuid = entry
                break

            entry_set.add(entry_string)

        if not uuid:
            while True:
                entry_index = menu(list(map(str, characteristics)))
                uuid = get_uuid_from_characteristic(characteristics[entry_index])

                try:
                    print(f'Connecting to {device} {uuid}...')
                    if not Plug.connect(device, uuid):
                        Plug.connect(device, uuid)
                    print('Vibrating...')
                    Plug.vibe(1)
                    time.sleep(1)
                    Plug.vibe(0)

                    print('Use this device?')
                    if confirm():
                        break
                except:
                    print('Failed to connect')
                
    else:
        print('Which UUID?')
        characteristics = peripheral.getCharacteristics()
        characteristic_index = menu(list(map(str, characteristics)))
        uuid = get_uuid_from_characteristic(characteristics[characteristic_index])
    
    name = read_name('Name: ')
    save_list(DEVICES_FILE_PATH, DEVICES + [f'{name} {device} {uuid}'])

def fetch():
    device = None
    print('Fetch what?')
    option = menu(["Game", "Device", "Offset"])

    if 0 == option:
        game = read_name('Game Name: ')
        if game in GAME_NAMES:
            fatal(f'{game} is already registered')
        
        if not try_get_pid(game):
            print(f'{game} could not be found. Continue?')
            if not confirm():
                sys.exit(0)
            
        save_list(GAMES_FILE_PATH, GAMES + [game])
    elif 1 == option:
        fetch_device()
    elif 2 == option:
        print('Which game?')
        game_index = menu(GAME_NAMES)
        name = read_name('Address name: ')
        offset = int(input('Offset (hex): '), 16)
        width = int(input('Width (bytes): '))
        GAMES[game_index] += f'|{name} {offset} {width}'
        save_list(GAMES_FILE_PATH, GAMES)
    
    print('Saved for next time :3')

def create_vibrate_to_scale():
    print('Shall scale be inverted (0 -> highest vibrations)?')
    invert = confirm()
    max_value = int(input('Max value (stays at highest/lowest vibrations if over): '))
    
    def generated(new_value):
        intensity = 0
        if not invert:
            intensity = int(Plug.MAX_VIBE * (new_value / max_value))
        else:
            if new_value > max_value:
                new_value = max_value
                
            intensity = int(Plug.MAX_VIBE * ((Plug.MAX_VIBE * (MAX_VALUE - new_value)) / (Plug.MAX_VIBE * MAX_VALUE)))
            
        Plug.vibe(intensity)

    return generated

def get_device_and_connect():
    print('Debug?')
    if confirm():
        return
        
    print('Which device?')
    device_info = DEVICES[menu(DEVICE_NAMES)].split()

    print('Connecting to device...')
    Plug.connect(device_info[1], device_info[2])
    print('Done!')

def game_offset_names(game):
    return list(map(lambda offset_entry: offset_entry.split()[0], game_offset_list(game)))

def play():
    running_games = scan_for_running_games()
    if [] == running_games:
        fatal('No game found')

    game_name, pid = running_games[0]
    if 1 != len(running_games):
        print('Select game')
        game_index = menu(map(lambda proc_info: proc_info[0], running_games))
        game_name, pid = running_games[game_index]

    print(f'Play with {game_name}?')
    if not confirm():
        return

    game = game_from_name(game_name)

    print('Which value?')
    hack = menu(game_offset_names(game))
    entry = game_offset_list(game)[hack].split(' ')
    offset = int(entry[1])
    width = int(entry[2])

    get_device_and_connect()
    
    print('How shall we play?')
    mode = menu(['Change Detection', 'Switch', 'Continuous Scale', 'Value Scale', 'Continuous Diff'])

    callback = None
    if 0 == mode:
        callback = create_vibrate_on_update(get_intensity())
    elif 1 == mode:
        callback = create_vibrate_until_update(get_intensity())
    elif 2 == mode:
        callback = create_vibrate_to_scale()
    elif 3 == mode:
        callback = create_vibrate_to_diff()
    else:
        callback = create_last_cont_value()
        
    scanner.daemon(pid, offset, width, callback)

def root_check():
    euid = os.geteuid()
    if euid == 0:
        return
    
    print("Script not started as root. Running sudo...")
    args = ['sudo', sys.executable] + sys.argv + [os.environ]
    os.execlpe('sudo', *args)
    
def main():
    root_check()
    option = menu(['Play', 'Fetch'])
    if 0 == option:
        play()
    else:
        fetch()
    
if __name__ == '__main__':
    main()
