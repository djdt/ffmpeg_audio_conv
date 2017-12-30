import os


def total_size(files):
    """Calculates the total size of a list of files in bytes.
    """
    size = 0
    for f in files:
        size += os.stat(f).st_size
    return size


def expand_path(path):
    """Expands paths such as ., .. and ~.
    """
    return os.path.abspath(os.path.expanduser(path))


def count_dirs(base):
    """Counts all directories found recursivly in a base directory.
    """
    count = 0
    for root, dirs, files in os.walk(expand_path(base)):
        for d in dirs:
            count += 1
    return count


def search_exts(base, exts):
    """Recursivly finds all files that have a matching extension.
    """
    matches = []
    for root, dirs, files in os.walk(expand_path(base)):
        for f in files:
            if exts is None or os.path.splitext(f)[1][1:] in exts:
                matches.append(os.path.join(root, f))
    return matches


def convert_path(file, base, new_base):
    """Converters a path by changing the base directory.
    """
    path = os.path.relpath(file, expand_path(base))
    return os.path.join(expand_path(new_base), path)
