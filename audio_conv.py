#!/usr/bin/python3
import argparse
import logging
import os
import signal
import sys
import time

import multiline
from converter import Converter


class CleanupKiller:
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit)
        signal.signal(signal.SIGTERM, self.exit)

    def exit(self, signum, frame):
        self.kill_now = True


def find_files(base_dir, exts, recurse=False):
    matches = []
    if recurse:
        for root, dirs, files in os.walk(base_dir):
            for f in files:
                if os.path.splitext(f)[1][1:] in exts:
                    matches.append(os.path.join(root, f))
    else:
        for files in os.listdir(base_dir):
            f = os.path.join(base_dir, files)
            if os.path.isfile(f) and os.path.splitext(f)[1][1:] in exts:
                    matches.append(f)
    return matches


def get_output_file_path(in_path, in_base, out_base, new_ext):
    path = os.path.relpath(in_path, in_base)
    path = os.path.splitext(path)[0] + os.extsep + new_ext
    return os.path.join(out_base, path)


def progress_display(count, total, elapsed_time, msg, threads):
    bar_len = 32
    filled_len = int(round(bar_len * count) / float(total))

    bar = '#' * filled_len + ' ' * (bar_len - filled_len)
    bar_line = '[{}] {:>6.1%} {}'.format(
            bar, count / float(total),
            time.strftime('%H:%M:%S', time.gmtime(
                elapsed_time * (total - (total - count)))))

    lines = []
    for m in msg:
        lines.append('Current file: ' + m)
    for i in range(len(msg), threads):
        lines.append("Finished.")
    lines.append(bar_line)

    multiline.print_lines(lines)


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
    killer = CleanupKiller()

    source_path = os.path.abspath(os.path.expanduser(args['indir']))
    dest_path = os.path.abspath(os.path.expanduser(args['outdir']))

    # Gather input files
    source_files = find_files(source_path,
                              args['informat'], args['recurse'])

    # Sort reverse to allow for pop
    source_files.sort(reverse=True)

    converter = Converter(options, args['threads'])
    prog_total = len(source_files)
    prog_skipped = 0
    update_progress = True

    start_time = time.time()
    elapsed_time = 0

    while converter.num_converted() + prog_skipped < prog_total:
        # Check current processes
        if converter.check_processes() > 0:
            converter.log_errors(logger)
            # update_progress = True

        if converter.can_add_process() and len(source_files) > 0:
            infile = source_files.pop()
            # Remove source_path, change ext, prepend dest_path
            outfile = get_output_file_path(
                    infile, source_path, dest_path, args['outformat'])
            # If the file already exists, skip it
            if os.path.exists(outfile):
                prog_skipped += 1
            else:
                # Make new dir if needed
                dir_name = os.path.dirname(outfile)
                if not os.path.exists(dir_name):
                    os.makedirs(dir_name, exist_ok=True)
                    print('Creating dir:', dir_name)
                # Add new process to processes, store filename for print
                converter.new_process(infile, outfile)
            update_progress = True

        # Update the progress
        elapsed_time = time.time() - start_time
        if update_progress:
            progress_display(converter.num_converted() + prog_skipped,
                             prog_total, elapsed_time, converter.status())
            update_progress = False
        else:
            time.sleep(0.01)
        if killer.kill_now:
            converter.kill_all()
            multiline.skip_lines(args['threads'] + 1)
            print("Exiting...")
            exit(1)

    # Display end msg
    # progress_display(1, 1, 0, [], args['threads'])
    # multiline.skip_lines(args['threads'] + 1)
    print('Processed {} files in {:.2f} seconds.'.format(
        converter.num_converted(), elapsed_time))
    print('{} errors, {} skipped, {} converted.'.format(
        converter.failed, prog_skipped, converter.completed))

    # Remove empty logs
    logging.shutdown()
    if os.stat('audio_conv.log').st_size == 0:
        os.remove('audio_conv.log')


if __name__ == "__main__":
    main()
