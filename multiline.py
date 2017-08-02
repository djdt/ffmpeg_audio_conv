#!/usr/bin/python3


def skip_lines(num):
    print('\033[' + str(num - 1) + 'B')


def print_lines(lines):
    for line in lines:
        print('\033[K' + line)  # Clear the line
    print('\033[' + str(len(lines)) + 'A', end='')
