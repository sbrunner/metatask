# -*- coding: utf-8 -*-

import sys
import os
import re
import json
import yaml
import subprocess
import argparse
import locale
import metatask
from metatask.process import Process
from metatask.utils import files, read_metadata, print_diff, confirm
from bashcolor import colorize, RED, BLUE, GREEN
from concurrent.futures import ThreadPoolExecutor, as_completed


CONFIG_FILENAME = "metatask.yaml"

if 'APPDATA' in os.environ:
    CONFIG_PATH = os.path.join(os.environ['APPDATA'], CONFIG_FILENAME)
elif 'XDG_CONFIG_HOME' in os.environ:
    CONFIG_PATH = os.path.join(os.environ['XDG_CONFIG_HOME'], CONFIG_FILENAME)
else:
    CONFIG_PATH = os.path.join(os.environ['HOME'], '.config', CONFIG_FILENAME)

config = {}


def main():
    locale.setlocale(locale.LC_ALL, locale.getdefaultlocale())

    parser = argparse.ArgumentParser(
        description='Rename the file using metadata.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Task to do:
name: Predefined command in the config file.
TODO:
rename/<old>/<new>/<flag>

flags can contains:
i => Perform case-insensitive matching.
l => Make \w, \W, \b, \B, \s and \S dependent on the current locale.
m => Multiline.
s => Make the '.' special character match any character at all.
u => Make \w, \W, \b, \B, \d, \D, \s and \S '''
        '''dependent on the Unicode character properties database.
x => Verbose
See also: https://docs.python.org/2/library/re.html#module-contents''')
    parser.add_argument(
        'directory', nargs='*', default=['.'],
        help='root foldrers'
    )
    parser.add_argument(
        '--ignore-dir', nargs='*', default=None,
        help='ignore the following dirrectories',
    )
    parser.add_argument(
        '--filename', nargs='*', default=['.*'],
        help='The filename regexp',
    )
    parser.add_argument(
        '--metadata', action='store_true',
        help='view the available tags'
    )
    parser.add_argument(
        '--view', action='store_true',
        help='view the available tags'
    )
    parser.add_argument(
        '--view-meta',
        help='view the available tags'
    )
    parser.add_argument(
        '--apply', action='store_true',
        help='apply the change'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='just see the diff'
    )
    parser.add_argument(
        '--cmds', nargs='*', default=[],
        help='cmds we want to do',
    )
    parser.add_argument(
        '--list-cmds', action='store_true',
        help='List the available cmds and exit'
    )
    parser.add_argument(
        '--task',
        help='task we want to do',
    )
    parser.add_argument(
        '--list-tasks', action='store_true',
        help='List the available cmds and exit'
    )
    parser.add_argument(
        '--config-file', default=None,
        help='The configuration file',
    )

    args = parser.parse_args()

    metatask.init(args.config_file)
    job_files = []
    process = Process()

    if args.list_cmds:
        for name, cmd in metatask.config.get("cmds", {}).items():
            print("{}: {}".format(
                colorize(name, GREEN), cmd.get("display", "")
            ))
        exit()
    if args.list_tasks:
        for name, cmd in metatask.config.get("tasks", {}).items():
            print("{}: {}".format(
                colorize(name, GREEN), cmd.get("display", "")
            ))
        exit()

    merge = False
    keep = False
    cmds = []
    cmds_config = metatask.config.get("cmds", {})
    if args.task is not None:
        task = metatask.config.get("tasks", {}).get(args.task, {})
        merge = task.get(merge, False) is True
        keep = task.get(keep, False) is True
        for cmd in task.get("cmds", []):
            if isinstance(cmd, str):
                c = cmds_config.get(cmd)
                c["name"] = cmd
                if c is None:
                    raise Exception("Missing command '%s' in `cmds`" % cmd)
                cmds.append(c)
            else:
                cmds.append(cmd)
    elif args.cmds:
        for cmd in args.cmds:
            rename = re.match("rename/(.+)/(.*)/(.*)", cmd)
            if rename is not None:
                cmds.append({
                    "display": "",
                    "name": cmd,
                    "type": "rename",
                    "from": rename.group(1),
                    "to": rename.group(2),
                    "flag": rename.group(3)
                })
            else:
                c = cmds_config.get(cmd)
                if c is None:
                    raise Exception("Missing command '%s' in `cmds`" % cmd)
                c["name"] = cmd
                cmds.append(c)

    file_list = files(
        args.directory, args.ignore_dir or
        metatask.config.get('ignore_dir', []), args.filename
    )
    if merge:
        f = file_list[0]
        if os.path.isfile(f):
            full_dest, types, messages = _process_file(f, args, process, cmds)

            if 'cmd' not in types:
                sys.stderr.write(colorize("A merge process should have a cmd", RED))
                exit()

            if f != full_dest:
                print_diff(file_list, full_dest)
                if os.path.exists(full_dest):
                    sys.stderr.write(colorize(
                        "Destination already exists\n", RED
                    ))
                    exit()
            if keep:
                sys.stderr.write(colorize("The source an the destination are the same in keep mode", RED))
                exit()

            job_files.append((file_list, None))
    else:
        dest_files = []
        for f, _ in file_list:
            if os.path.isfile(f):
                full_dest, types, messages, metadata = _process_file(f, args, process, cmds)

                if types == set():
                    continue

                if f != full_dest:
                    print_diff(f, full_dest)
                    if os.path.exists(full_dest):
                        sys.stderr.write(colorize(
                            "Destination already exists\n", RED
                        ))
                        continue
                    elif len([
                        i for i in dest_files if i == full_dest
                    ]) != 0:
                        sys.stderr.write(colorize(
                            "Destination will already exists\n", RED
                        ))
                        continue
                elif keep:
                    sys.stderr.write(colorize("The source an the destination are the same in keep mode", RED))
                    exit()
                elif types != set(["rename"]):
                    print(colorize(f, BLUE))
                    for message in messages:
                        print(message)
                else:
                    continue
                job_files.append((f, metadata))
                dest_files.append(full_dest)

    if len(job_files) != 0 and not args.dry_run and (args.apply or confirm()):
        progress = Progress(len(job_files), cmds, process, keep)
        progress.run_all(job_files)


def _process_file(f, args, process, cmds):
    try:
        metadata = None
        if args.metadata or args.view or len([
            cmd for cmd in cmds
            if cmd.get("metadata", False) is True
        ]) > 0:
            metadata = read_metadata(f, not args.view)
            if args.view:
                print(json.dumps(metadata, indent=4))
                exit()

        full_dest, extension, types, messages = process.destination_filename(
            cmds, f, metadata=metadata
        )

        return full_dest, types, messages, metadata

    except subprocess.CalledProcessError:
        sys.stderr.write("Error on getting metadata on '%s'.\n" % f)


def init(config_file):
    global config
    if config_file is None:
        config_file = CONFIG_PATH
    with open(config_file) as f:
        config = yaml.load(f.read())


class Progress:
    def __init__(self, nb, cmds, process, keep):
        self.nb = nb
        self.no = 0
        self.cmds = cmds
        self.process = process
        self.keep = keep

    def run(self, filename, metadata):
        print(colorize(filename, GREEN))
        result = self.process.process(self.cmds, filename, metadata=metadata, keep=self.keep)
        self.no += 1
        print(colorize("{}/{}".format(self.no, self.nb), GREEN))
        return result

    def run_all(self, job_files):
        with ThreadPoolExecutor(
            max_workers=metatask.config.get('nb_process', 8)
        ) as executor:
            future_results = {
                executor.submit(self.run, f, metadata):
                f for f, metadata in job_files
            }
            for feature in as_completed(future_results):
                feature.result()
                pass

if __name__ == "__main__":
    main()
