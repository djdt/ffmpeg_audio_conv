#!/usr/bin/python3
import argparse
import logging
import os
import sys
import time

from util import fileops
from util.converter import Converter
from util.cleankiller import CleanKiller


def display_progress(count, total, elapsed_time):
    bar_len = 32
    filled = int(round(bar_len * count) / float(total))
    bar = '[' + '#' * filled + ' ' * (bar_len - filled) + ']'

    timeleft = 0 if count == 0 else (
            elapsed_time / float(total)) * (total - count)
    print('{} {:>6.1%} {}'.format(
            bar, count / float(total),
            time.strftime('%H:%M:%S', time.gmtime(timeleft))))
    print(u'\u001b[1A', end='')


def parse_args(args):
    parser = argparse.ArgumentParser(
        description='Converts audio files using ffmpeg.')
    parser.add_argument('indir', help='Input directory.')
    parser.add_argument('outdir', help='Output directory.')
    parser.add_argument('-i', '--informat', type=str, nargs='*',
                        help='Format(s) to convert (use ext(s)).')
    parser.add_argument('-o', '--outformat', type=str,
                        help='Target format (use ext.).')
    parser.add_argument('-r', '--recurse', action='store_true',
                        help='Recurse the input directory.')
    parser.add_argument('-q', '--quality', type=str,
                        help='Quality to pass to ffmpeg.')
    parser.add_argument('-b', '--bitrate', type=str,
                        help='Target bitrate, e.g. 320k.')
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


def main():
    args = parse_args(sys.argv[1:])
    if args['quality'] is not None:
        options = ['-q', args['quality']]
    elif args['bitrate'] is not None:
        options = ['-b', args['bitrate']]
    else:
        options = []

    logger = setup_logger()
    killer = CleanKiller()

    src_files = fileops.gather_files(args['indir'],
                                     args['informat'], args['recurse'])

    converter = Converter(options, args['threads'])
    num_files = len(src_files)
    skipped = 0

    start_time = time.time()
    elapsed_time = 0

    while converter.num_converted() < num_files:
        # Check current processes
        if converter.check_processes() > 0:
            converter.log_errors(logger)
            # update_progress = True

        if converter.can_add_process() and len(src_files) > 0:
            infile = src_files.pop()
            outfile = fileops.convert_path(
                infile, args['indir'], args['outdir'], args['outformat'])
            converter.add_process(infile, outfile)

        # Update the progress
        elapsed_time = time.time() - start_time
        display_progress(converter.num_converted() + skipped,
                         num_files, elapsed_time)
        time.sleep(0.05)

        if killer.kill_now:
            converter.kill_all()
            print("Exiting...")
            exit(1)

    # Display end msg
    print('Processed {} files in {:.2f} seconds.'.format(
        converter.num_converted(), elapsed_time))
    print('{} errors, {} skipped, {} converted.'.format(
        converter.failed, converter.skipped, converter.completed))

    # Remove empty logs
    logging.shutdown()
    if os.stat('audio_conv.log').st_size == 0:
        os.remove('audio_conv.log')


if __name__ == "__main__":
    main()
