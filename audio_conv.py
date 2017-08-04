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
            description='Converts audio files using ffmpeg,'
                        ' preserves dir structure.',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('indir', help='Input directory.')
    parser.add_argument('outdir', help='Output directory.')
    parser.add_argument('-b', '--bitrate', type=str,
                        help='Target bitrate, e.g. 320k.')
    parser.add_argument('-c', '--copyexts', type=str, nargs='+',
                        default=['jpg', 'jpeg', 'png', 'gif', 'log', 'cue'],
                        help='Copy other files (e.g. images) to new dir.')
    parser.add_argument('-C', '--nocopyexts', action='store_true',
                        help='Prevent copying of other files.')
    parser.add_argument('-i', '--inexts', type=str, nargs='+',
                        default=['flac', 'alac', 'wav'],
                        help='File types to convert.')
    parser.add_argument('-p', '--pretend', action='store_true',
                        help='Perform no actions.')
    parser.add_argument('-o', '--outext', type=str,
                        help='Target file type for conversion.')
    parser.add_argument('-q', '--quality', type=str,
                        help='Quality to pass to ffmpeg.')
    # parser.add_argument('-r', '--recurse', action='store_true',
    #                     help='Recurse the input directory.')
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

    # Init logger and killer
    logger = setup_logger()
    killer = CleanKiller()
    converter = Converter(options, args['threads'])

    start_time = time.time()

    # Get files then filter existing
    in_files = fileops.search_exts(args['indir'], args['inexts'])
    skipped = 0
    for f in in_files:
        if os.path.exists(
                fileops.convert_path(f, args['indir'], args['outdir'])):
            print('Skipping:', f)
            skipped += 1
            in_files.remove(f)
    in_files.sort(reverse=True)  # Optimise for pop later

    num_files = len(in_files)
    size_files = fileops.total_size(in_files)
    size_conv = 0
    update_progress = True

    while converter.num_converted() < num_files:
        # Check current processes
        if converter.check_processes() > 0:
            print('Logging errors...')
            converter.log_errors(logger)
            # update_progress = True

        if converter.can_add_process() and len(in_files) > 0:
            inf = in_files.pop()
            size_conv += os.stat(inf).st_size
            outf = fileops.convert_path(inf, args['indir'], args['outdir'])
            outf = os.path.splitext(outf)[0] + (os.extsep + args['outext'])
            converter.add_process(inf, outf, pretend=args['pretend'])
            update_progress = True

        # Update the progress
        if update_progress:
            time_left = time_remaining(size_conv, size_files - size_conv,
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
    if not args['nocopyexts']:
        copy_files = fileops.search_exts(args['indir'], args['copyexts'])
        for f in copy_files:
            new_f = fileops.convert_path(f, args['indir'], args['outdir'])
            if os.path.exists(new_f):
                print('Skipping other:', f)
            else:
                print('Copying other:', f)
                if not args['pretend']:
                    shutil.copy2(f, new_f)
                copied += 1

    # Display end msg
    print('Processed {} dirs, {} files in {:.2f} seconds.'.format(
        fileops.count_dirs(args['indir']),
        converter.num_converted() + skipped,
        time.time() - start_time))
    print('{} errors, {} skipped, {} converted.'.format(
        converter.failed, skipped, converter.completed))
    if args['copyexts']:
        print('{} other files copied.'.format(copied))

    # Remove empty logs
    logging.shutdown()
    if os.stat('audio_conv.log').st_size == 0:
        os.remove('audio_conv.log')


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    if args['outext'] is None:
        print('Please specify an output format.')
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
