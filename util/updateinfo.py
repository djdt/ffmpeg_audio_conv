import mutagen


def replace_tags(source, dest):
    source = mutagen.File(source)
    dest = mutagen.File(dest)

    dest.tags = source.tags
    dest.save()


def compare_tags(file1, file2):
    """Returns True if tags are the same."""
    return mutagen.File(file1).tags == mutagen.File(file2).tags
    # tags1 = mutagen.File(file1).tags
    # tags2 = mutagen.File(file2).tags

    # for k, v in tags1:
    #     if k not in tags2:
    #         return False
    #     if tags1[k] != tags2[k]:
    #         return False
    # return True
