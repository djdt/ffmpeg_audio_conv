import os


def expand_path(path):
    return os.path.abspath(os.path.expanduser(path))


def create_dirs_if_not_exists(dir):
    dir = expand_path(dir)
    if not os.path.exists(dir):
        os.makedirs(dir, exist_ok=True)
        return True
    return False


def gather_files(dir, exts=None, recurse=False):
    dir = expand_path(dir)
    matches = []
    if recurse:
        for root, dirs, files in os.walk(dir):
            for f in files:
                if exts is None or os.path.splitext(f)[1][1:] in exts:
                    matches.append(os.path.join(root, f))
    else:
        for files in os.listdir(dir):
            f = os.path.join(dir, files)
            if os.path.isfile(f):
                if exts is None or os.path.splitext(f)[1][1:] in exts:
                    matches.append(f)
    matches.sort(reverse=True)
    return matches


def convert_path(file, indir, outdir, ext):
    path = os.path.relpath(file, expand_path(indir))
    path = os.path.splitext(path)[0] + os.extsep + ext
    return os.path.join(expand_path(outdir), path)
