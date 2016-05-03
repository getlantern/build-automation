#! /usr/bin/env python

import argparse
import httplib
import json
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

    def last_build(self, branch):
        v = self.store.get(branch)
        if v is None:
            return None, None
        return v.get('commit'), v.get('s3links')

    def set_last_build(self, branch, commit, s3links):
        v = self.store.get(branch)
        if v is None:
            v = {}
        v['commit'] = commit
        v['s3links'] = s3links
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


def build(branch, version, dry_run):
    execute('git checkout ' + branch)
    if not dry_run:
        execute('VERSION=' + version + ' make packages')


def upload(version, bucket, dry_run):
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
        put = 's3cmd put ' + local + " -P s3://" + bucket
        rm = 'rm ' + local
        if not dry_run:
            execute(cp)
            execute(put)
            execute(rm)
        links.append("http://" + bucket + ".s3.amazonaws.com/" + local)

    return links


def fetch():
    execute('git fetch -p')
    output = execute('git branch -rl | grep -E "release-[0-9]*.[0-9]*.[0-9]*$"')
    branches = map(lambda l: l.strip(), output)
    branches.append('origin/master')
    branches.append('origin/devel')
    return map(lambda b: (b, execute('git show -s --format=%h ' + b)[0].strip()), branches)


def send_to_slack(title, fallback, text):
    host = "hooks.slack.com"
    payload = {"fallback": fallback,
               "title": title,
               "text": text}
    data = {'attachments': [payload]}
    conn = httplib.HTTPSConnection(host, 443)
    conn.connect()
    conn.request('POST', send_to_slack.path, headers={'content-type': 'application/json'}, body=json.dumps(data))
    response = conn.getresponse()
    if response.status != httplib.OK:
        raise RuntimeError("invalid response status %d" % response.status)
send_to_slack.path = None


def notify(processed):
    title_tmpl = string.Template('Latest installers of <https://github.com/getlantern/lantern/tree/$branch|$branch>:\r\n$links\r\n')
    text_tmpl = string.Template('Changes since $last_commit:\r\n$commits')

    branch = processed['branch'].split('/')[1]
    pretty_links = map(lambda l: '<' + l + '|' + l.split('_', 3)[3] + '>', processed['links'])
    title = title_tmpl.substitute({'branch': branch, 'links': '\r\n'.join(pretty_links)})
    fmt = '--format="%h: (%an) %s, %ar"'
    if processed['last_commit'] is None:
        commits = execute('git log -n 10 %s %s' % (fmt, processed['commit']))
    else:
        commits = execute('git log --no-pager %s %s..%s' % (fmt, processed['last_commit'], processed['commit']))

    pretty_commits = map(lambda line: "<https://github.com/getlantern/lantern/commit/%s|%s>:%s" % (line.split(':')[0], line.split(':')[0], line.split(':')[1]), commits)
    pretty_commits.append('<https://github.com/getlantern/lantern/commits/%s|more...>\r\n' % branch)
    text = text_tmpl.substitute({'last_commit': processed['last_commit'], 'commits': ''.join(pretty_commits)})
    send_to_slack(title, "commits for %s" % processed['commit'], text)


def process(branch, commit, dry_run):
    local_branch = string.split(branch, '/')[1]
    version = local_branch.rpartition('-')[2]
    # appdmg doesn't allow volumes name to exceed 27 chars. Simple math gives 11 here.
    if len(version) > 11:
        version = version[:11]
    version = version + '_' + commit
    build(branch, version, dry_run)
    links = upload(version, "lantern-continuous-build", dry_run)
    return links


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', dest='dry_run', action='store_true', help='not build/upload')
    args = parser.parse_args()
    send_to_slack.path = os.environ["SLACK_WEBHOOK_PATH"]

    config = Config("./result.yml")
    execute.cwd = "../lantern"
    processed = []
    for branch, commit in fetch():
        try:
            last_commit, last_links = config.last_build(branch)
            if commit == last_commit:
                print "skipping branch %s: head %s already uploaded" % (branch, commit)
            else:
                print "build branch %s: head %s is different from prev %s" % (branch, commit, last_commit)
                links = process(branch, commit, dry_run=args.dry_run)
                processed = {'branch': branch, 'commit': commit, 'links': links, 'last_commit': last_commit, 'last_links': last_links}
                notify(processed)
                if not args.dry_run:
                    config.set_last_build(processed['branch'], processed['commit'], processed['links'])
                    config.save()
        except Exception:
            pass


if __name__ == '__main__':
    main()
