import os.path
import subprocess

def is_image(path):
    image_exts = ['jpeg', 'jpg', 'gif', 'bmp', 'png']
    ext = os.path.splitext(path)[1].lower().lstrip('.')

    return ext in image_exts

def convert_image(oldpath, newpath):
    cmd = ['magick', 'convert', oldpath, newpath]

    ret = subprocess.run(cmd, capture_output=True)

    ret.check_returncode()
