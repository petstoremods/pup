#!/usr/bin/python3

import sys, time
import argparse

ADDRESS_RANGE_SECTION = 0
PROTECTION_SECTION = 1
READ_WRITE = 'rw'
HEX_BASE = 16
DEBUG = True
POINTER_WIDTH = 8
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
        with open("/proc/%d/mem" % pid, 'rb', 0) as mem_file:
            for offset in picklist:
                mem_file.seek(offset)
                chunk = mem_file.read(width)
                if match_function(chunk, value):
                    addresses.append(offset)

        return addresses
    
    with open("/proc/%d/maps" % pid, 'r') as maps_file:
        with open("/proc/%d/mem" % pid, 'rb', 0) as mem_file:
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

class Scanner:
    def __init__(self, pid, value, width, scan):
        self.pid = pid
        self.value = value
        self.width = width
        self.scan = scan
        self.matches = scan()
        

    def ui_help(self):
        print("""Selection:
        - [(p)rint] : show matches
        - [(r)escan] : rerun last scan
        - [(f)ollow] <int (useful for redirection)> <self.width> : find matches to the given integer
        - [(t)est] <addr>: increments the value at the location to verify the address is the one you're looking for
        """)

    def print_matches(self):
        print(self.matches)
        
    def ui(self):
        print(f'{len(self.matches)} matches')
        option = input("> ").lower()

        if option.startswith('p'):
            self.print_matches()
            
        elif option.startswith('r'):
            new_matches = set(self.scan(self.matches))
            
        elif option.startswith('f'):
            tokens = option.split(' ')
            if len(tokens) > 1:
                self.value = int(tokens[1])

            if len(tokens) > 2:
                self.width = int(tokens[2])
            
            #todo: can improve later with error handling and keeping track of trail
            debug(f'Scanning for {self.value}:{self.width}')
            self.scan = lambda picklist: get_matching_memory_of_pid(self.pid, self.value, self.width, compare_bytes_to_int, picklist)
            self.matches = set(self.scan())
            
        elif option.startswith('t'):
            addr = int(option.split(' ')[1])

            current_value = 0
            with open("/proc/%d/mem" % self.pid, 'rb', 0) as mem_file:
                mem_file.seek(addr)
                current_value = get_int_from_bytes(mem_file.read(self.width))

            new_value = get_bytes_from_int(current_value + 1, self.width)
            with open("/proc/%d/mem" % self.pid, 'wb', 0) as mem_file:
                mem_file.seek(addr)
                mem_file.write(new_value)
                
        else:
            self.ui_help()
            
        
def daemon(pid, offset, callback):
    previous_value = None
    
    while True:
        with open("/proc/%d/mem" % pid, 'rb', 0) as mem_file:
            mem_file.seek(offset)
            value = get_int_from_bytes(mem_file.read(4))
            if previous_value is not None:
                if value != previous_value:
                    callback(value)

            previous_value = value
            time.sleep(1)
            

def parse_lookup_table(pid, path):
    # todo: if "exact"
    offsets = open(path).read().split()
    offset = int(offsets[0])
    
    with open("/proc/%d/mem" % pid, 'wb', 0) as mem_file:
        mem_file.seek(offset)
        mem_file.write(get_bytes_from_int(6969, 4)) #nice
        
    return
    
    # todo: if "offset", see example test
    offsets = open(path).read().split()
    offset = int(offsets[0]) #todo: multiple redirection/offset support

    with open("/proc/%d/maps" % pid, 'r') as maps_file:
        with open("/proc/%d/mem" % pid, 'rb', 0) as mem_file:
            for line in maps_file.readlines():

                #todo: commonize this
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

                #todo: end commonize
                break

    with open("/proc/%d/mem" % pid, 'wb', 0) as mem_file:
        mem_file.seek(start + offset)
        mem_file.write(get_bytes_from_int(69, 4)) #nice
        
    return
            
def main():
    parser = argparse.ArgumentParser(
        prog="scanner",
        description="Find memory location for mods."
    )
    
    parser.add_argument(
        "pid",
        type=int
    )

    parser.add_argument(
        "--int",
        nargs="?",
        help="Value of integer to search for."
    )

    parser.add_argument(
        "--width",
        nargs="?",
        help="Byte width of integer to search for."
    )
    
    parser.add_argument(
        "--string",
        nargs="?",
        help="String value to search for."
    )

    parser.add_argument(
        "--table",
        nargs="?",
        help="Use pointer redirection/offset lookup table to get a specific address. Writes a nice value as an ad-hoc test"
    )

    args = parser.parse_args()

    if args.table:
        parse_lookup_table(args.pid, args.table)
        return
    
    if (args.int and args.string) or not (args.int or args.string):
        print('pick int or string dummy')
        sys.exit(1)

    if args.int and not args.width:
        print('int search requires self.width argument')
        sys.exit(1)

    scanner = None
    if args.int:
        def scan(picklist = None):
            return get_matching_memory_of_pid(args.pid, int(args.int), int(args.width), compare_bytes_to_int, picklist)

        scanner = Scanner(args.pid, int(args.int), int(args.width), scan)
    else:
        def scan(picklist = None):
            return get_matching_memory_of_pid(args.pid, args.string, len(args.string), compare_bytes_to_string, picklist)

        scanner = Scanner(args.pid, args.string, len(args.string), scan)
    
    while True:
        scanner.ui()
        
                    
if __name__ == '__main__':
    main()
