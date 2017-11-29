#!/usr/bin/python3

import os
import subprocess
import signal
import shutil
import tempfile


class MultiProcess:
    def __init__(self, cmds):
        self.cmds = cmds
        self.next()

    def next(self):
        self.process = subprocess.Popen(
            self.cmds.pop(0),
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE)

    def kill(self):
        self.process.send_signal(signal.SIGINT)
        self.process.wait()

    def poll(self):
        status = self.process.poll()
        if status == 0 and len(self.cmds) > 0:
            self.next()
            return None
        return status

    def log_error(self, logger):
        logger.info('Failed on cmd: ' + self.process.args)
        for l in self.process.stderr:
            logger.info(l)


class ConverterProcess(MultiProcess):

    def __init__(self, cmds, inf, outf):
        super().__init__(cmds)
        self.inf, self.outf = inf, outf

    def kill(self):
        super().kill()
        # Remove uncompleted file
        if os.path.exists(self.outf):
            print('Removing:', self.outf)
            os.remove(self.outf)


class TagUpdaterProcess(MultiProcess):

    def __init__(self, cmds, inf, outf, tmpf):
        super().__init__(cmds)
        self.inf, self.outf, self.tmpf = inf, outf, tmpf

    def poll(self):
        status = super().poll()
        if status == 0:
            shutil.copyfile(self.tmpf.name, self.outf)
        return status


class Converter:

    def __init__(self, options=[], threads=4):
        self.options = options
        self.threads = threads

        self.processes = []
        self.failed_processes = []
        self.completed = 0
        self.failed = 0
        self.size_conv = 0

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
                    self.size_conv += os.stat(proc.inf).st_size
                self.processes.remove(proc)
        return ret

    def add_convert_process(self, inpath, outpath,
                            print_actions=True, pretend=False):
        # Make new dir if needed
        if not os.path.exists(os.path.dirname(outpath)):
            if print_actions:
                print('Creating dir:', os.path.dirname(outpath))
            if not pretend:
                os.makedirs(os.path.dirname(outpath))

        # Add new process to processes, store filename for print
        if print_actions:
            print('Converting:', inpath)
        if pretend:
            self.completed += 1
        else:
            cmd = ['ffmpeg', '-i', inpath, '-vn']
            cmd.extend(self.options)
            cmd.append(outpath)
            self.processes.append(ConverterProcess([cmd], inpath, outpath))

    def add_update_process(self, inpath, outpath,
                           print_actions=True, pretend=False):
        # Add new process to processes
        if print_actions:
            print('Updating tags:', outpath)
        if pretend:
            self.completed += 1
        else:
            temp = tempfile.NamedTemporaryFile(
                    suffix=os.path.splitext(outpath)[1])
            cmds = [['ffmpeg', '-i', inpath, '-aframes', '1',
                     temp.name, '-y'],
                    ['ffmpeg', '-i', temp.name, '-i', outpath, '-map', '1',
                     '-c:a', 'copy', '-map_metadata:s:a', '0:s:a',
                     temp.name, '-y']]
            self.processes.append(TagUpdaterProcess(
                cmds, inpath, outpath, temp))

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
        return self.completed + self.failed
