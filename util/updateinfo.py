import mutagen

REPLACE_TAGS = []
IGNORE_TAGS = []


def replace_tags(source, dest, tags):
    source = mutagen.File(source)
    dest = mutagen.File(dest)

    for tag in tags:
        dest.tags[tag] = source.tags[tag]

    dest.save()


def compare_tags(file1, file2):
    """Returns keys of file1 that differ from file2."""
    # return mutagen.File(file1).tags == mutagen.File(file2).tags
    tags1 = mutagen.File(file1).tags
    tags2 = mutagen.File(file2).tags

    diff = []

    for k, v in tags1:
        if k.upper() not in [t.upper() for t, v in tags2]:
            diff.append(k)
            continue
        if tags1[k] != tags2[k]:
            diff.append(k)
            continue
    return diff
