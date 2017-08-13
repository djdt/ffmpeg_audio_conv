# ffmpeg_audio_conv

Multi thread audio converter script using ffmpeg.

Usage:
```
usage: audio_conv.py [-h] [-b BITRATE] [-c COPYEXTS [COPYEXTS ...]] [-C]
                     [-i INEXTS [INEXTS ...]] [-p] -o OUTEXT [-q QUALITY]
                     [-t THREADS] [-v]
                     indir outdir

Converts audio files using ffmpeg, preserves dir structure.

positional arguments:
  indir                 Input directory.
  outdir                Output directory.

optional arguments:
  -h, --help            show this help message and exit
  -b BITRATE, --bitrate BITRATE
                        Target bitrate, e.g. 320k. (default: None)
  -c COPYEXTS [COPYEXTS ...], --copyexts COPYEXTS [COPYEXTS ...]
                        Copy other files (e.g. images) to new dir. (default:
                        ['jpg', 'jpeg', 'png', 'gif', 'log', 'cue'])
  -C, --nocopyexts      Prevent copying of other files. (default: False)
  -i INEXTS [INEXTS ...], --inexts INEXTS [INEXTS ...]
                        File types to convert. (default: ['flac', 'alac',
                        'wav'])
  -p, --pretend         Perform no actions. (default: False)
  -o OUTEXT, --outext OUTEXT
                        Target file type for conversion. (default: None)
  -q QUALITY, --quality QUALITY
                        Quality to pass to ffmpeg. (default: None)
  -t THREADS, --threads THREADS
                        Maximum number of threads used. (default: 4)
  -v, --verbose         Increase output. (default: False)
  ```
