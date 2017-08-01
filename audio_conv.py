import os
import subprocess
import time


def find_all_files(base_dir, ext='flac'):
    matches = []
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if f.split(os.extsep)[-1] == ext:
                matches.append(os.path.abspath(os.path.join(root, f)))

    return matches


def progress_display(count, total, msg, end='\r'):
    bar_len = 32
    filled_len = int(round(bar_len * count) / float(total))

    percent = count / float(total)
    bar = '#' * filled_len + ' ' * (bar_len - filled_len)

    fill = ' ' * (32 - len(msg))
    print('[{}] {:>6.1%} [{}]{}'.format(
        bar, percent, msg[:32], fill), end=end)


def get_output_file_path(in_path, in_base, out_base, new_ext):
    path = os.path.relpath(in_path, in_base)
    path = os.path.splitext(path)[0] + os.extsep + new_ext
    return os.path.join(out_base, path)


def parse_args(argc, argv):



def main(argc, argv):
    start = time.time()
    max_procs = 4
    procs = []
    quality = 5
    source_path = os.path.abspath(os.path.expanduser(
        "~/Music/flac/Boris/Pink (2006)"))
    dest_path = os.path.abspath(os.path.expanduser("~/Music/test"))
    source_files = find_all_files(source_path)
    prog_total = len(source_files)
    prog_complete = 0

    last_file = ""

    while prog_complete < prog_total:
        # Check current processes
        for proc in procs:
            ret = proc.poll()
            if ret is not None:
                if ret > 0:
                    print("ffmpeg error: ")
                    for line in proc.stderr:
                        print(line)
                    for p in procs:
                        p.kill
                    return
                procs.remove(proc)
                prog_complete += 1
                break

        if len(procs) < max_procs and len(source_files) > 0:
            in_file = source_files.pop()
            # Remove source_path, change ext, prepend dest_path
            out_file = get_output_file_path(
                    in_file, source_path, dest_path, 'ogg')
            if not os.path.exists(out_file):
                p = subprocess.Popen(['ffmpeg', '-i', in_file,
                                      '-q', str(quality),
                                      out_file],
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.PIPE)
                procs.append(p)
            else:
                prog_complete += 1

        last_file = os.path.basename(out_file)
        progress_display(prog_complete, prog_total, last_file)
        time.sleep(0.01)

    finish = time.time()
    progress_display(100, 100, '', '\n')
    print('{} files converted in {:.2f} seconds.'.format(
        prog_total, finish - start))


if __name__ == "__main__":
    main()
