# -*- coding: utf-8 -*-

import sys
import os
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
rename/<new name>/<flag>
replace/<old>/<new>/<flag>
moveto/<path>/<flag>
movetorelatve/<path>/<flag>
setmeta/<name>/<value>/<flag>

flags can contains:
j => Jinja template.
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
        '--task', nargs='*', default=[],
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
                colorize(name, GREEN), cmd.get("name", "")
            ))
            exit()
    if args.list_tasks:
        for name, cmd in metatask.config.get("tasks", {}).items():
            print("{}: {}".format(
                colorize(name, GREEN), cmd.get("name", "")
            ))
            exit()

    for f, _ in files(
        args.directory, args.ignore_dir or
        metatask.config.get('ignore_dir', []), args.filename
    ):
        if os.path.isfile(f):
            try:
                metadata = None
                if args.metadata or args.view or len([
                    name for name, cmd in metatask.config.get("cmds", {}).items()
                    if cmd.get("metadata", False) is True and name in args.cmds
                ]) > 0:
                    metadata = read_metadata(f, not args.view)
                    if args.view:
                        print(json.dumps(metadata, indent=4))
                        exit()

                full_dest, extension, task = process.destination_filename(
                    args.cmds, f, metadata=metadata
                )

                if f != full_dest:
                    print_diff(f, full_dest)
                    if os.path.exists(full_dest):
                        sys.stderr.write(colorize(
                            "Destination already exists", RED
                        ))
                        continue
                    elif len([
                        i for i in job_files if i[1] == full_dest
                    ]) != 0:
                        sys.stderr.write(colorize(
                            "Destination will already exists", RED
                        ))
                        continue
                elif task is True:
                    print(colorize(f, BLUE))
                else:
                    continue
                job_files.append((f, metadata))
            except subprocess.CalledProcessError:
                sys.stderr.write("Error on getting metadata on '%s'.\n" % f)

    if len(job_files) != 0 and not args.dry_run and (args.apply or confirm()):
        progress = Progress(len(job_files), args.cmds, process)
        progress.run_all(job_files)


def init(config_file):
    global config
    if config_file is None:
        config_file = CONFIG_PATH
    with open(config_file) as f:
        config = yaml.load(f.read())


class Progress:
    def __init__(self, nb, cmds, process):
        self.nb = nb
        self.no = 0
        self.cmds = cmds
        self.process = process

    def run(self, filename, metadata):
        result = self.process.process(self.cmds, filename, metadata=metadata)
        self.no += 1
        print("%i/%i" % (self.no, self.nb))
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
