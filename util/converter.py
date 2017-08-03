#!/usr/bin/python3

import os
import subprocess
import signal

from util import fileops


class ConverterProcess:

    def __init__(self, cmd, name):
        self.name = name
        self.process = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE)

    def kill(self):
        self.process.send_signal(signal.SIGINT)
        self.process.wait()

    def poll(self):
        return self.process.poll()

    def log_error(self, logger):
        for l in self.process.stderr:
            logger.info(l)


class Converter:

    def __init__(self, options=[], threads=4):
        self.options = options
        self.threads = threads

        self.processes = []
        self.completed = 0
        self.failed = 0
        self.skipped = 0

    def check_processes(self):
        ret = 0
        for proc in self.processes:
            status = proc.poll()
            if status is not None:
                if status > 0:
                    self.failed += 1
                    self.failed_processes.append(proc)
                    ret += 1
                else:
                    self.completed += 1
                self.processes.remove(proc)
        return ret

    def add_process(self, inpath, outpath, print_actions=True):
        if os.path.exists(outpath):
            if print_actions:
                print('Skipping:', outpath)
            self.skipped += 1
        else:
            # Make new dir if needed
            if fileops.create_dirs_if_not_exists(
                    os.path.dirname(outpath)):
                if print_actions:
                    print('Creating dir:', os.path.dirname(outpath))
            # Add new process to processes, store filename for print
            if print_actions:
                print('Converting:', inpath)
            cmd = ['ffmpeg', '-i', inpath]
            cmd.extend(self.options)
            cmd.append(outpath)
            self.processes.append(
                ConverterProcess(cmd, os.path.basename(inpath)))

    def log_errors(self, logger):
        for proc in self.failed_processes:
            proc.log_error(logger)
        self.failed_processes = []

    def kill_all(self):
        for proc in self.processes:
            proc.kill()
        self.processes = []

    def num_processess(self):
        return len(self.processes)

    def can_add_process(self):
        return self.num_processess() < self.threads

    def process_names(self):
        return [p.name for p in self.processes]

    def num_converted(self):
        return self.completed + self.failed + self.skipped