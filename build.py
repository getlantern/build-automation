#! /usr/bin/env python

import os
import string
import time
import yaml
from subprocess import Popen, PIPE


class Config:
    def __init__(self, fname):
        self.fname = fname
        if not os.access(fname, os.F_OK):
            self.store = {}
            return
        with open(fname) as f:
            self.store = yaml.load(f)

    def last_built(self, branch):
        v = self.store.get(branch)
        if v is None:
            return None
        return v.get('last-built')

    def set_last_built(self, branch, commit, s3links):
        v = self.store.get(branch)
        if v is None:
            v = {}
        v['last-built'] = commit
        v['last-s3links'] = s3links
        self.store[branch] = v

    def save(self):
        with open(self.fname, 'w') as f:
            f.write(yaml.dump(self.store))


def execute(command, print_output=True):
    print "> " + command
    popen = Popen(command, stdout=PIPE, stderr=PIPE, shell=True, cwd=execute.cwd)
    itout = iter(popen.stdout.readline, b"")
    iterr = iter(popen.stderr.readline, b"")
    stdout_lines = list(itout)
    if print_output:
        print ''.join(stdout_lines)
    stderr_lines = list(iterr)
    if stderr_lines:
        print ''.join(stderr_lines)
    popen.communicate()
    if popen.returncode is not None and popen.returncode != 0:
        raise RuntimeError
    return stdout_lines
execute.cwd = None


def build(branch, version):
    execute('git checkout ' + branch)
    execute('VERSION=' + version + ' make packages')


def upload(version):
    installers = map(lambda i: i.replace('VERSION', version), [
        'lantern-installer.dmg',
        'lantern-installer.exe',
        'lantern_VERSION_amd64.deb',
        'lantern_VERSION_i386.deb'
    ])
    prefix = time.strftime('%Y%m%d%H%M%S%Z') + '_' + version + '_'
    links = []
    for installer in installers:
        local = prefix + installer
        cp = 'cp ' + installer + ' ' + local
        put = 's3cmd put ' + local + " s3://lantern-continuous-build -P"
        rm = 'rm ' + local
        execute(cp)
        execute(put)
        execute(rm)
        links.append("s3://lantern-continuous-build/" + local)

    return links


def fetch():
    # execute('git fetch -p')
    output = execute('git branch -rl | grep -E "release-\d*.\d*.\d*$"')
    branches = map(lambda l: l.strip(), output)
    return map(lambda b: (b, execute('git show -s --format=%h ' + b)[0].strip()), branches)


def notify():
    pass


def main():
    config = Config("./result.yml")
    execute.cwd = "../lantern"
    for branch, commit in fetch():
        last = config.last_built(branch)
        if commit == last:
            print "skipping branch %s: head %s already uploaded" % (branch, commit)
        else:
            print "build branch %s: head %s, prev %s" % (branch, commit, last)
            version = string.split(branch, '-')[1] + '_' + commit
            build(branch, version)
            links = upload(version)
            if len(links) == 0:
                print "***Nothing uploaded"
            else:
                config.set_last_built(branch, commit, links)

    config.save()


if __name__ == '__main__':
    main()
