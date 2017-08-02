import argparse
import os
import subprocess
import sys
import time


def find_files(base_dir, exts):
    matches = []
    for files in os.listdir(base_dir):
        f = os.path.join(base_dir, files)
        if os.path.isfile(f) and os.path.splitext(f)[1][1:] in exts:
                matches.append(f)
    return matches


def find_all_files(base_dir, exts):
    matches = []
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if os.path.splitext(f)[1][1:] in exts:
                matches.append(os.path.join(root, f))
    return matches


def progress_display(count, total, msg, end='\r'):
    bar_len = 32
    filled_len = int(round(bar_len * count) / float(total))

    percent = count / float(total)
    bar = '#' * filled_len + ' ' * (bar_len - filled_len)

    line1 = str(msg)
    line2 = '[{}] {:>6.1%}'.format(bar, percent)

    print('\033[K', end='')
    print(line1)
    print(line2, end='')
    print('\b' * len(line2), end='')
    print('\033[F', end='')


def get_output_file_path(in_path, in_base, out_base, new_ext):
    path = os.path.relpath(in_path, in_base)
    path = os.path.splitext(path)[0] + os.extsep + new_ext
    return os.path.join(out_base, path)


def parse_args(args):
    parser = argparse.ArgumentParser(
        description='Converts audio files using ffmpeg.')
    parser.add_argument('indir', help='Input directory.')
    parser.add_argument('outdir', help='Output directory.')
    parser.add_argument('-i', '--informat', default=None, nargs='*',
                        help='Format(s) to convert (use ext(s)).')
    parser.add_argument('-o', '--outformat', default=None,
                        help='Target format (use ext.).')
    parser.add_argument('-r', '--recurse', action='store_true',
                        help='Recurse the input directory.')
    parser.add_argument('-q', '--quality', type=str, default=None,
                        help='Quality to pass to ffmpeg.')
    parser.add_argument('-b', '--bitrate', type=str, default=None,
                        help='Target bitrate, e.g. 320k.')
    parser.add_argument('-t', '--threads', type=int, default=4,
                        help='Maximum number of threads used.')
    return vars(parser.parse_args(args))


def main():
    start = time.time()
    args = parse_args(sys.argv[1:])
    if args['quality'] is not None and args['bitrate'] is not None:
        print('Cannot define quality AND bitrate, use one.')
        sys.exit(1)

    source_path = os.path.abspath(os.path.expanduser(args['indir']))
    dest_path = os.path.abspath(os.path.expanduser(args['outdir']))

    # Gather input files
    source_files = []
    if args['recurse']:
        source_files = find_all_files(source_path, args['informat'])
    else:
        source_files = find_files(source_path, args['informat'])

    procs = []
    prog_total = len(source_files)
    prog_complete = 0
    update_progress = True

    while prog_complete < prog_total:
        # Check current processes
        for proc, fn in procs:
            ret = proc.poll()
            if ret is not None:
                # If error, print and exit
                if ret > 0:
                    print("ffmpeg error: ")
                    for line in proc.stderr:
                        print(line)
                    for p in procs:
                        p.kill
                    sys.exit(1)
                procs.remove((proc, fn))
                prog_complete += 1
                update_progress = True
                break

        if len(procs) < args['threads'] and len(source_files) > 0:
            in_file = source_files.pop()
            # Remove source_path, change ext, prepend dest_path
            out_file = get_output_file_path(
                    in_file, source_path, dest_path, args['outformat'])
            # If the file already exists, skip it
            if not os.path.exists(out_file):
                # Build ffmpeg cmd
                cmd = ['ffmpeg', '-i', in_file]
                if args['quality'] is not None:
                    cmd.extend(['-q', args['quality']])
                elif args['bitrate'] is not None:
                    cmd.extend(['-b', args['bitrate']])
                cmd.append(out_file)
                # Add new process to processes, store filename for print
                p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.PIPE)
                procs.append((p, os.path.basename(out_file)))
            else:
                prog_complete += 1
            update_progress = True

        # Update the progress
        if update_progress:
            progress_display(prog_complete, prog_total, [x[1] for x in procs])
            update_progress = False
        time.sleep(0.01)

    # Display end msg
    finish = time.time()
    progress_display(1, 1, [])
    print('\n')
    print('{} files converted in {:.2f} seconds.'.format(
        prog_total, finish - start))


if __name__ == "__main__":
    main()
