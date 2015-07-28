#!/usr/bin/env python
# -*- coding: utf-8 -*-

__version__ = '0.1.3'

import re
from prettytable import PrettyTable
from pipes import quote
from subprocess import Popen, PIPE
from datetime import date, timedelta

def shell(cmd):
    p = Popen(cmd, shell=True, stdout=PIPE)
    p.wait()
    return p.stdout.read()[:-1]

def get_number_of_lines(range='', paths=None, options=None):
    if options is None:
        options = {}

    shell_args = []

    for k, v in options.items():
        if k == 'oneline': continue
        if isinstance(v, bool) and v:
            shell_args.append('--%s' % k.replace('_', '-'))
        elif v:
            shell_args.append('--%s=%s' % (k.replace('_', '-'), quote(v)))

    if paths:
        shell_args.append('-- %s' % paths)
    commit_id = shell('git log --reverse -1 --format=format:"%%H" %s %s' % (range, ' '.join(shell_args))).split("\n")[0].strip()
    return int(shell( 'git ls-tree -r --name-only %s | xargs -I%% git --no-pager show %s:%%  | wc -l ' % (commit_id, commit_id)))

def get_number_of_files(range='', paths=None, options=None):
    if options is None:
        options = {}

    shell_args = []

    for k, v in options.items():
        if k == 'oneline': continue
        if isinstance(v, bool) and v:
            shell_args.append('--%s' % k.replace('_', '-'))
        elif v:
            shell_args.append('--%s=%s' % (k.replace('_', '-'), quote(v)))

    if paths:
        shell_args.append('-- %s' % paths)
    commit_id = shell('git log --reverse -1 --format=format:"%%H" %s %s' % (range, ' '.join(shell_args))).split("\n")[0].strip()
    return int(shell( 'git ls-tree -r --name-only "%s" | wc -l' % commit_id))

def get_stat_summary_counts(line):
    numbers = re.findall('\d+', line)
    if len(numbers) == 1:
        numbers.append(0)
        numbers.append(0)
    elif len(numbers) == 2 and line.find('(+)') != -1:
        numbers.append(0)
    elif len(numbers) == 2 and line.find('(-)') != -1:
        numbers.insert(1, 0)
    return [int(x) for x in numbers]

def count_git_changed_files(range='', paths=None, options=None):
    if options is None:
        options = {}

    shell_args = []

    for k, v in options.items():
        if isinstance(v, bool) and v:
            shell_args.append('--%s' % k.replace('_', '-'))
        elif v:
            shell_args.append('--%s=%s' % (k.replace('_', '-'), quote(v)))

    if paths:
        shell_args.append('-- %s' % paths)

    files_count = 0
    lines_count = 0

    changes = shell('git log --format=format:"%%H" --shortstat %s %s | grep "^ "' % (range, ' '.join(shell_args)))
    for change in changes.split("\n"):
        numbers = get_stat_summary_counts(change)
        if len(numbers) == 3:
            files_count += numbers[0]
            lines_count += numbers[1] + numbers[2]
    return [files_count, lines_count]

def count_git_log(range='', paths=None, options=None):
    if options is None:
        options = {}

    options['oneline'] = True

    shell_args = []

    for k, v in options.items():
        if isinstance(v, bool) and v:
            shell_args.append('--%s' % k.replace('_', '-'))
        elif v:
            shell_args.append('--%s=%s' % (k.replace('_', '-'), quote(v)))

    if paths:
        shell_args.append('-- %s' % paths)

    return int(shell('git log %s %s | wc -l' % (range, ' '.join(shell_args))))

DAY = timedelta(days=1)
WEEK = timedelta(weeks=1)
DATE_FORMAT  = '%Y-%m-%d 00:00:00'

def count(author=None, period='weekly', first='monday', number=None, range='', paths=None, no_all=False, merges=True, **options):

    assert period[0] in 'dwmy', "option 'period' should be daily (d), weekly (w), monthly (m) or yearly (y)"
    assert first[:3] in ('mon', 'sun', 'sat'), "option 'first' should be monday (mon), sunday (sun), saturday (sat)"

    today = date.today()

    if period.startswith('d'):
        until = today+DAY
        if not number: number = 14
    elif period.startswith('w'):
        until = today - today.weekday()*DAY + WEEK
        if first[:3] == 'sun':
            until -= DAY
        elif first[:3] == 'sat':
            until -= 2*DAY
        if not number: number = 8
    elif period.startswith('m'):
        until = date(
            today.year+(today.month+1 > 12),
            (today.month+1) % 12,
            1
        )
        if not number: number = 12
    elif period.startswith('y'):
        until = date(today.year+1, 1, 1)
        if not number: number = 5


    options['author']    = author
    options['all']       = not no_all
    options['no_merges'] = not merges

    table = PrettyTable(["Since", "Until", "# commits", "# files in repo", "# files changed", "% files changed", "# lines in repo", "# lines changed", "% lines changed"])
    table.align = 'l'
    while number > 0:

        if period.startswith('d'):
            since = until - DAY
        elif period.startswith('w'):
            since = until - WEEK
        elif period.startswith('m'):
            since = date(
                until.year-(until.month-1 <= 0),
                1 + ((12+(until.month-1)-1) % 12),
                1
            )
        elif period.startswith('y'):
            since = date(until.year-1, 1, 1)

        options['since'] = since.strftime(DATE_FORMAT)
        options['until'] = until.strftime(DATE_FORMAT)

        number_of_files = get_number_of_files(range, paths, options)
        number_of_lines = get_number_of_lines(range, paths, options)
        (files_count, changes_count) = count_git_changed_files(range, paths, options)
        table.add_row([since, until, count_git_log(range, paths, options), number_of_files, files_count, 
                   "{:0.2f}%".format(float(files_count) / number_of_files * 100),
                   number_of_lines,
                   changes_count,
                   "{:0.2f}%".format(float(changes_count) / number_of_lines * 100),])

        until = since

        number -= 1

    print table

def main():
    count(period='w',  number=3)

if __name__ == '__main__':
    main()
