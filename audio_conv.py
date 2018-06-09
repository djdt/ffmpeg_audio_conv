#!/usr/bin/python3
import argparse
import logging
import os
import shutil
import sys
import time
import datetime
from dateutil import parser as dateparse

from util import fileops
from util.converter import Converter
from util.cleankiller import CleanKiller


def time_remaining(completed, remaining, elapsed_time):
    """Returns the time estimated given the number of completed items,
    remaining items and the time elasped so far.
    Pass in total sizes of files for more accurate estimation.
    """
    if completed == 0:
        return 0
    return (remaining * (elapsed_time / float(completed)))


def display_progress(count, total, remaining_time):
    """Displays a progress bar and and print the remaining time.
    Moves the cursor up a line afterwards.
    """
    bar_len = 32
    filled = int(round(bar_len * count) / float(total))
    bar = '[' + '#' * filled + ' ' * (bar_len - filled) + ']'

    print('{} {:>6.1%} Time left: {}'.format(
            bar, count / float(total),
            time.strftime('%H:%M:%S', time.gmtime(remaining_time))))
    print(u'\u001b[1A\u001b[2K', end='')


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
    parser.add_argument('-o', '--outext', type=str, required=True,
                        help='Target file type for conversion.')
    parser.add_argument('-p', '--pretend', action='store_true',
                        help='Perform no actions.')
    parser.add_argument('-q', '--quality', type=str,
                        help='Quality to pass to ffmpeg.')
    parser.add_argument('-t', '--threads', type=int, default=4,
                        help='Maximum number of threads used.')
    parser.add_argument('-u', '--updatetags', nargs='?',
                        const='',
                        help='Update the tags of existing files, '
                             'optionally modified after a certain date..'
                             'Dates should be formatted as per ISO8601.')
    parser.add_argument('-U', '--updateonly', action='store_true',
                        help='Only perform updating, not conversion..')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Increase output.')

    args = parser.parse_args(args)

    if not os.path.exists(args.indir):
        parser.error("Input directory does not exist.")
    if args.bitrate is not None and args.quality is not None:
        parser.error("Cannot set both bitrate and quality options.")
    if args.updatetags is not None:
        if args.updatetags == '':
            args.updatetags = datetime.datetime.min
        else:
            args.updatetags = dateparse.parse(args.updatetags)

    return vars(args)


def setup_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler('audio_conv.log', 'w')
    handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def gather_files(args):
    """Searches directories for matching files.
    Returns the files for converting, updating and skipping.
    """
    convfiles, updatefiles, skipfiles = [], [], []
    for f in fileops.search_exts(args['indir'], args['inexts']):
        t = fileops.convert_path(f, args['indir'], args['outdir'])
        t = os.path.splitext(t)[0] + os.extsep + args['outext']
        if os.path.exists(t):
            moddate = datetime.datetime.fromtimestamp(os.path.getmtime(f))
            if args['updatetags'] is not None and \
                    moddate >= args['updatetags']:
                updatefiles.append(f)
            else:
                if args['verbose']:
                    print('Skipping:', f)
                skipfiles.append(f)
        else:
            convfiles.append(f)
    convfiles.sort(reverse=True)  # Optimise for pop later
    updatefiles.sort(reverse=True)  # Optimise for pop later

    return convfiles, updatefiles, skipfiles


def convert(infiles, args, logger, killer):
    """Takes input files for conversion.
    Returns the number of failed, completed and copied files,
    and the time taken to convert.
    """
    if args['quality'] is not None:
        options = ['-q:a', args['quality']]
    elif args['bitrate'] is not None:
        options = ['-b:a', args['bitrate']]
    else:
        options = []

    converter = Converter(options, args['threads'])

    start_time = time.time()

    num_files = len(infiles)
    size_files = fileops.total_size(infiles)
    update_progress = True

    while converter.num_converted() < num_files:
        # Check current processes
        if converter.check_processes() > 0:
            print('Logging errors...')
            converter.log_errors(logger)
            # update_progress = True

        if converter.can_add_process() and len(infiles) > 0:
            inf = infiles.pop()

            outf = fileops.convert_path(inf, args['indir'], args['outdir'])
            outf = os.path.splitext(outf)[0] + (os.extsep + args['outext'])
            converter.add_convert_process(inf, outf, pretend=args['pretend'])
            update_progress = True

        # Update the progress
        if update_progress:
            time_left = time_remaining(
                    converter.size_conv, size_files - converter.size_conv,
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

    return converter.failed, converter.completed, time.time() - start_time


def update_tags(infiles, args, logger, killer):
    """Updates the tags of infiles.
    Returns the number of successful updates and the time taken.
    """

    converter = Converter(threads=args['threads'])

    start_time = time.time()

    num_files = len(infiles)
    size_files = fileops.total_size(infiles)
    update_progress = True

    while converter.num_converted() < num_files:
        # Check current processes
        if converter.check_processes() > 0:
            print('Logging errors...')
            converter.log_errors(logger)
            # update_progress = True

        if converter.can_add_process() and len(infiles) > 0:
            inf = infiles.pop()

            outf = fileops.convert_path(inf, args['indir'], args['outdir'])
            outf = os.path.splitext(outf)[0] + (os.extsep + args['outext'])
            converter.add_update_process(inf, outf, pretend=args['pretend'])
            update_progress = True

        # Update the progress
        if update_progress:
            time_left = time_remaining(
                    converter.size_conv, size_files - converter.size_conv,
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

    return converter.completed, time.time() - start_time


def copy_other_files(args):
    """Copies files from the input ot output directory,
    preserving directory structures.
    """
    copied = 0
    if not args['nocopyexts']:
        copy_files = fileops.search_exts(args['indir'], args['copyexts'])
        for f in copy_files:
            new_f = fileops.convert_path(f, args['indir'], args['outdir'])
            if os.path.exists(new_f):
                if args['verbose']:
                    print('Skipping other:', f)
            else:
                print('Copying other:', f)
                if not args['pretend']:
                    shutil.copy2(f, new_f)
                copied += 1
    return copied


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])

    logger = setup_logger()
    killer = CleanKiller()

    convfiles, updatefiles, skipfiles = gather_files(args)
    num_files = len(convfiles) + len(updatefiles) + len(skipfiles)
    convert_time, update_time = 0.0, 0.0
    if not args['updateonly']:
        failed, completed, convert_time = convert(convfiles, args,
                                                  logger, killer)
        copied = copy_other_files(args)
        print("")
    updated, update_time = update_tags(updatefiles, args, logger, killer)
    print("")

    # Display end msg
    print('Processed {} dirs, {} files in {:.2f} seconds.'.format(
        fileops.count_dirs(args['indir']), num_files,
        convert_time + update_time))
    if not args['updateonly']:
        print('Convert: {} errors, {} skipped, {} converted.'.format(
            failed, num_files - (failed + completed), completed))
        if args['copyexts']:
            print('Copy: {} other files copied.'.format(copied))
    if updated > 0:
        print('Update: Updated tags in {} files, skipped {} files.'.format(
            updated, len(skipfiles)))

    # Remove empty logs
    logging.shutdown()
    if os.stat('audio_conv.log').st_size == 0:
        os.remove('audio_conv.log')
