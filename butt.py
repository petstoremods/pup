#!/usr/bin/python3

import ReadWriteMemory
import argparse
import Plug
import time, sys, os
import importlib

def is_root():
    return os.geteuid() == 0

parser = argparse.ArgumentParser(
    prog="butt"
)
parser.add_argument(
    "--intensity"
)
parser.add_argument(
    "--duration"
)
parser.add_argument(
    "--profile"
)
args = parser.parse_args()

if args.intensity:
    Plug.vibe(args.intensity)
    if args.duration and int(args.duration) > 0:
        time.sleep(int(args.duration))
    else:
        time.sleep(1)
    Plug.stop()
elif args.profile:
    if not is_root():
        print('Need to be root')
        sys.exit(1)

    print('Importing profile...')
    profile = importlib.import_module(args.profile)
    print('Done.\n')

    print('Getting process...')
    mem = ReadWriteMemory.ReadWriteMemory()
    process = mem.get_process_by_id(profile.get_process_id())
    process.open()
    print('Done.\n')

    print('Sending values...')
    pointer, offsets = profile.get_value_address()
    addr = process.get_pointer(pointer, offsets)
    while True:
        value = process.read(addr)
        profile.main(value)
        time.sleep(1)
