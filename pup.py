#!/usr/bin/python3

import argparse
import Plug
import scanner
import time
import subprocess, sys, os
from simple_term_menu import TerminalMenu
from termcolor import colored
import graceful_kill
import json
import pup_modes

import contextlib
with contextlib.redirect_stdout(None):
    import pygame.mixer

SCRIPT_ROOT = os.path.dirname(os.path.realpath(__file__))
graceful_kill.on_kill(lambda: sys.exit(0))

def try_get_pid(process_name):
    try:
        pids = subprocess.check_output(['pgrep', '-fl', process_name]).decode('ascii').split('\n')
        for line in pids:
            if process_name in line:
                return line.split()[0]
    except:
        return None

def fatal(message):
    print(colored(message, 'red'))
    sys.exit(1)

def clear():
    os.system('clear')
    
def root_check(extra_args):
    euid = os.geteuid()
    if euid == 0:
        return
    
    print("Script not started as root. Running sudo...")
    args = ['sudo', sys.executable] + sys.argv + extra_args + [os.environ]
    os.execlpe('sudo', *args)

def start_sound():
    pygame.mixer.Sound(f'{SCRIPT_ROOT}/start.wav').play()

def select_sound():
    pygame.mixer.Sound(f'{SCRIPT_ROOT}/click.wav').play()
    
def menu(options):
    clear()
    start_sound()
    option = TerminalMenu(options).show()
    if option is None:
        fatal('No selection, exiting...')
        
    print(f'> {options[option]}')
    select_sound()
    while pygame.mixer.get_busy():
        time.sleep(0.1)
        
    return option

def connect_to_game(game_name):
    game_pid = 0
    while not game_pid:
        game_pid = try_get_pid(game_name)
        time.sleep(1)

    return game_pid

def wait_for(thing, callback):
    print(f'Waiting for {thing}... ', end='', flush=True)
    result = callback()
    print('Done!')
    return result

class Feature:
    def __init__(self, feature_format, feature_config):
        self.min_value = feature_config['min']
        self.max_value = feature_config['max']
        self.feature_format = feature_format
        self.feature_string = feature_config['string']

    def eval_feature_insertion(self, insertion_string, arg):
        string_to_eval = insertion_string.replace('$', str(arg))
        insertion = eval(string_to_eval)

        if self.feature_format == 'binary':
            return '{:02x}'.format(insertion)

        return str(insertion)

    def get_min(self):
        return self.min_value

    def get_max(self):
        return self.max_value
    
    def get_execute_string(self, arg):
        inserting_value = False
        insertion_string = ''
        
        result = ''
        for c in self.feature_string:
            if not inserting_value and c != '{':
                result += c
                continue

            if (inserting_value and c == '{') or (not inserting_value and c == '}'):
                fatal('Syntax error: Unbalanced insertion')

            if c == '{':
                inserting_value = True
                continue

            if c == '}':
                result += self.eval_feature_insertion(insertion_string, arg)
                insertion_string = ''
                continue

            insertion_string += c

        return result

    def run(self, execute_string):
        if self.feature_format == 'binary':
            execute_string = bytearray.fromhex(execute_string)
                
        Plug.write(execute_string)

    def execute_string_from_input(self):
        value = int(input('> '))
        if value >= self.min_value and value <= self.max_value:
            return self.get_execute_string(value)
    
def run(device_name, feature_name, game_name, mode_name):
    if game_name:
        root_check(['-c', device_name, feature_name, game_name, mode_name])
    
    config_path = f'{SCRIPT_ROOT}/config.json'
    config = json.loads(open(config_path).read())

    device_config = config['devices'][device_name]
    feature_config = device_config['features'][feature_name]

    clear()
    if not wait_for('bluetooth device', lambda: Plug.connect(device_config['address'], device_config['uuid'])):
        fatal('Failed to connect to bluetooth device')


    feature = Feature(device_config['format'], feature_config)
    if not game_name:
        while True:
            try:
                exec_str = feature.execute_string_from_input()
                print(f'Sending: {exec_str}')
                feature.run(exec_str)
            except ValueError:
                continue

        return

    game_config = config['games'][game_name]
    mode_config = game_config[mode_name]
    game_pid = wait_for(game_name, lambda: connect_to_game(game_name))
        
    mode_callback = None
    callback_name = mode_config['function']
    for callback_index, callback in enumerate(pup_modes.modes):
        if callback.__name__ == callback_name:
            mode_callback = callback
            break

    generated_callback = mode_callback(feature, mode_config)
    scanner.daemon(game_pid, mode_config['address'], mode_config['width'], generated_callback)

def choose_options():
    pygame.mixer.init()
    
    config_path = f'{SCRIPT_ROOT}/config.json'
    config = json.loads(open(config_path).read())

    device_names = list(config['devices'].keys())
    device_index = menu(device_names)
    device_name = device_names[device_index]
    device_config = config['devices'][device_name]

    feature_names = list(device_config['features'].keys())
    feature_index = menu(feature_names)
    feature_name = feature_names[feature_index]
    
    game_names = ['<Manual>'] + list(config['games'].keys())
    game_index = menu(game_names)
    if game_index == 0:
        run(device_name, feature_name, None, None)
        return
        
    game_name = game_names[game_index]
    game_config = config['games'][game_name]

    mode_names = list(game_config.keys())
    mode_index = menu(mode_names)
    mode_name = mode_names[mode_index]

    run(device_name, feature_name, game_name, mode_name)

def main():
    parser = argparse.ArgumentParser(
        prog="pup",
        description="Connect programs with sex toys."
    )
    
    parser.add_argument(
        "-c",
        "--config",
        nargs=4,
        help="device_name feature_name game_name mode_name"
    )

    args = parser.parse_args()
    if args.config:
        run(args.config[0], args.config[1], args.config[2], args.config[3])
        return
    
    choose_options()

    
if __name__ == '__main__':
    main()
