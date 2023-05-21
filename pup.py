#!/usr/bin/python3

import argparse
import Plug
import scanner
import time
import subprocess, sys, os
from simple_term_menu import TerminalMenu
from termcolor import colored
import graceful_kill

HOME = os.path.expanduser('~')
GAMES_FILE_PATH = f'{HOME}/proj/.gamelist'
DEVICES_FILE_PATH = f'{HOME}/proj/.devices'

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

def scan_for_running_games():
    for game in GAME_NAMES:
        try:
            match = subprocess.check_output(['pgrep', game])
        except:
            continue
        
        if match:
            return game, int(match)

    return None, None

def create_vibrate_on_update(intensity):
    def generated(new_value):
        Plug.vibe(intensity)
        time.sleep(1)
        Plug.stop()

    return generated

def get_intensity():
    print('Intensity?')
    return menu(list(map(lambda val: str(val), range(1, 21))))
        
def fetch():
    device = None
    print('Fetch what?')
    option = menu(["Game", "Device", "Offset"])

    if 0 == option:
        game = read_name('Game Name: ')
        save_list(GAMES_FILE_PATH, GAMES + [game])
    elif 1 == option:
        name = read_name('Name: ')
        device = read_name('Device Bluetooth ID: ')
        uuid = read_name('UUID: ')
        save_list(DEVICES_FILE_PATH, DEVICES + [f'{name} {device} {uuid}'])
    elif 2 == option:
        print('Which game?')
        game_index = menu(GAME_NAMES)
        name = read_name('Address name: ')
        offset = int(input('Offset (hex): '), 16)
        GAMES[game_index] += f'|{name} {offset}'
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
    print('Which device?')
    device_info = DEVICES[menu(DEVICE_NAMES)].split()
    Plug.DEVICE = device_info[1]
    Plug.UUID = device_info[2]

    print('Connecting to device...')
    Plug.connect()
    print('Done!')


def game_offset_names(game):
    return list(map(lambda offset_entry: offset_entry.split()[0], game_offset_list(game)))

def play():
    game_name, pid = scan_for_running_games()
    if not game_name:
        fatal('No game found')

    print(f'Play with {game_name}?')
    if not confirm():
        return

    game = game_from_name(game_name)

    print('Which value?')
    hack = menu(game_offset_names(game))
    offset = int(game_offset_list(game)[hack].split(' ')[1])

    get_device_and_connect()
    
    print('How shall we play?')
    mode = menu(['Change Detection', 'Continuous Scale'])

    callback = None
    if 0 == mode:
        callback = create_vibrate_on_update(get_intensity())
    else:
        callback = create_vibrate_to_scale()
        
    scanner.daemon(pid, offset, callback)

def main():
    option = menu(['Play', 'Fetch'])
    if 0 == option:
        play()
    else:
        fetch()
    
if __name__ == '__main__':
    main()
