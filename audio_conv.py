#!/usr/bin/python3
import argparse
import logging
import os
import shutil
import sys
import time

from util import fileops
from util.converter import Converter
from util.cleankiller import CleanKiller


def time_remaining(completed, remaining, elapsed_time):
    if completed == 0:
        return 0
    return (remaining * (elapsed_time / float(completed)))


def display_progress(count, total, remaining_time):
    bar_len = 32
    filled = int(round(bar_len * count) / float(total))
    bar = '[' + '#' * filled + ' ' * (bar_len - filled) + ']'

    print('{} {:>6.1%} Time left: {}'.format(
            bar, count / float(total),
            time.strftime('%H:%M:%S', time.gmtime(remaining_time))))
    print(u'\u001b[1A', end='')


def parse_args(args):
    parser = argparse.ArgumentParser(
        description='Converts audio files using ffmpeg.')
    parser.add_argument('indir', help='Input directory.')
    parser.add_argument('outdir', help='Output directory.')
    parser.add_argument('-b', '--bitrate', type=str,
                        help='Target bitrate, e.g. 320k.')
    parser.add_argument('-c', '--copyother', action='store_true',
                        help='Copy other files (e.g. images) to new dir.')
    parser.add_argument('-i', '--informat', type=str, nargs='*',
                        help='Ext(s) to convert, \'*\' for all.')
    parser.add_argument('-p', '--pretend', action='store_true',
                        help='Perform no actions.')
    parser.add_argument('-o', '--outformat', type=str,
                        help='Target format (use ext.).')
    parser.add_argument('-q', '--quality', type=str,
                        help='Quality to pass to ffmpeg.')
    parser.add_argument('-r', '--recurse', action='store_true',
                        help='Recurse the input directory.')
    parser.add_argument('-t', '--threads', type=int, default=4,
                        help='Maximum number of threads used.')
    return vars(parser.parse_args(args))


def setup_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler('audio_conv.log', 'w')
    handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def main(args):
    if args['quality'] is not None:
        options = ['-q', args['quality']]
    elif args['bitrate'] is not None:
        options = ['-b', args['bitrate']]
    else:
        options = []

    logger = setup_logger()
    killer = CleanKiller()

    src_files, other_files = fileops.gather_files(
            args['indir'], args['informat'], args['recurse'], False)
    # For pop later
    src_files.sort(reverse=True)

    converter = Converter(options, args['threads'])
    num_files = len(src_files)

    start_time = time.time()
    elapsed_time = 0
    update_progress = True

    while converter.num_converted() < num_files:
        # Check current processes
        if converter.check_processes() > 0:
            print('Logging errors...')
            converter.log_errors(logger)
            # update_progress = True

        if converter.can_add_process() and len(src_files) > 0:
            infile = src_files.pop()
            outfile = fileops.convert_path(
                infile, args['indir'], args['outdir'])
            outfile = os.path.splitext(outfile)[0] + (
                    os.extsep + args['outformat'])
            converter.add_process(infile, outfile, pretend=args['pretend'])
            update_progress = True

        # Update the progress
        if update_progress:
            files_left = num_files - converter.num_converted()
            time_left = time_remaining(converter.completed, files_left,
                                       time.time() - start_time)
            display_progress(converter.num_converted(), num_files, time_left)
            update_progress = False
        # Sleep only if really waiting
        elif not args['pretend']:
            time.sleep(0.05)

        if killer.kill_now:
            converter.kill_all()
            print("Exiting...")
            exit(1)

    copied = 0
    if args['copyother']:
        for f in other_files:
            new_f = fileops.convert_path(f, args['indir'], args['outdir'])
            if os.path.exists(new_f):
                print('Skipping other:', f)
            else:
                print('Copying other:', f)
                if not args['pretend']:
                    shutil.copy2(f, new_f)
                copied += 1

    # Display end msg
    print('Processed {} files in {:.2f} seconds.'.format(
        converter.num_converted(), elapsed_time))
    print('{} errors, {} skipped, {} converted.'.format(
        converter.failed, converter.skipped, converter.completed))
    if args['copyother']:
        print('{} other files copied.'.format(copied))

    # Remove empty logs
    logging.shutdown()
    if os.stat('audio_conv.log').st_size == 0:
        os.remove('audio_conv.log')


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    if args['informat'] is None or args['outformat'] is None:
        print('Please specify an input and output format.')
        exit(1)
    if args['quality'] is not None and args['bitrate'] is not None:
        print('Only one of quality and bitrate may be specified.')
        exit(1)
    if args['threads'] < 1:
        print('Minimum threads allowed is one.')
        exit(1)
    if not os.path.exists(args['indir']):
        print('Input directory does not exist.')
        exit(1)
    main(args)
