#!/usr/bin/python3

import sys, time
import argparse

ADDRESS_RANGE_SECTION = 0
PROTECTION_SECTION = 1
READ_WRITE = 'rw'
HEX_BASE = 16
DEBUG = True
POINTER_WIDTH = 4
PAGE_MATCH = None #PAGE_MATCH = '[heap]'

def debug(message):
    if DEBUG:
        print(message)

def get_int_from_bytes(bytes_to_parse):
    return int.from_bytes(bytes_to_parse, sys.byteorder)

def get_bytes_from_int(value, width):
    return value.to_bytes(width, sys.byteorder)

def compare_bytes_to_int(bytes_to_parse, value_to_match):
    return get_int_from_bytes(bytes_to_parse) == value_to_match

def compare_bytes_to_string(bytes_to_parse, value_to_match):
    return bytes_to_parse.decode('ascii') == value_to_match

def get_matching_memory_of_pid(pid, value, width, match_function, picklist = None):
    addresses = []
    if picklist:
        with open(f'/proc/{pid}/mem', 'rb', 0) as mem_file:
            for offset in picklist:
                mem_file.seek(offset)
                chunk = mem_file.read(width)
                if match_function(chunk, value):
                    addresses.append(offset)

        return addresses
    
    with open(f'/proc/{pid}/maps', 'r') as maps_file:
        with open(f'/proc/{pid}/mem', 'rb', 0) as mem_file:
            for line in maps_file.readlines():  # for each mapped region
                if PAGE_MATCH and PAGE_MATCH not in line:
                    continue
                
                sections = line.split(' ')
                if not READ_WRITE in sections[PROTECTION_SECTION]:
                    continue

                start, end = sections[ADDRESS_RANGE_SECTION].split('-')
                start = int(start, HEX_BASE)
                end = int(end, HEX_BASE)
                    
                if start > 0xFFFFFFFFFFFF:
                    continue

                debug(f'Scanning {start}-{end}')

                # read in everything, but only increase by one to account for unaligned memory
                for offset in range(start, end - width, 1):
                    mem_file.seek(offset)
                    chunk = mem_file.read(width)
                    if match_function(chunk, value):
                        addresses.append(offset)

                # read in last chunk
                mem_file.seek(end - width)
                chunk = mem_file.read(width)
                if match_function(chunk, value):
                    addresses.append(end - width)

    return set(addresses)

def read_bytes_at_address(pid, address, width):
    with open(f'/proc/{pid}/mem', 'rb', 0) as mem_file:
        mem_file.seek(address)
        return mem_file.read(width)

def get_address_from_lookup_list(pid, base_address, lookup_list):
    pointer = base_address
    mem_file = open(f'/proc/{pid}/mem', 'rb', 0)
    mem_file.seek(pointer)
    pointer = get_int_from_bytes(mem_file.read(POINTER_WIDTH))
    for offset in lookup_list:
        print(pointer)
        pointer += offset
        print(pointer)
        mem_file.seek(pointer)
        pointer = get_int_from_bytes(mem_file.read(POINTER_WIDTH))

    return pointer

def daemon(pid, offset, width, callback):
    previous_value = None
    
    while True:
        with open(f'/proc/{pid}/mem', 'rb', 0) as mem_file:
            mem_file.seek(offset)
            value = mem_file.read(width)
            if previous_value is not None:
                if value != previous_value:
                    callback(value)

            previous_value = value
            time.sleep(1)
                                
if __name__ == '__main__':
    main()
