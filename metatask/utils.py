# -*- coding: utf-8 -*-

import os
import re
import json
import datetime
import subprocess
from bashcolor import colorize, RED, GREEN, INVERSE


def common_start(str1, str2):
    strs = []
    strs += str1
    strs.append(str2)

    strs.sort(key=lambda e: len(e))
    str1 = strs[0]
    strs = strs[1:]

    start = ""

    for index, str1_ in enumerate(str1):
        continue_ = True
        for s in strs:
            if str1_ != s[index]:
                continue_ = False
                break
        if not continue_:
            break
        start += str1_

    return start


def different(str_, start, end):
    if end == "":
        return str_[len(start):]
    else:
        return str_[len(start):-len(end)]


def print_diff(str1, str2):
    if not isinstance(str1, list):
        str1 = [str1]
    start = common_start(str1, str2)
    end = common_start([s[:len(start) - 1:-1] for s in str1], str2[:len(start) - 1:-1])[::-1]

    for s in str1:
        print("- {0!s}".format(colorize("{0!s}{1!s}{2!s}".format(
            start,
            colorize(different(s, start, end), effects=[INVERSE]),
            end
        ), RED)))
    print("+ {0!s}".format(colorize("{0!s}{1!s}{2!s}".format(
        start,
        colorize(different(str2, start, end), effects=[INVERSE]),
        end
    ), GREEN)))


def split(path):
    result = []
    path, folder = os.path.split(path)
    result.append(folder)
    while path != '':
        path, folder = os.path.split(path)
        result.append(folder)
    return result


def files(directories, ignore_dir, filenames=None):
    if filenames is None:
        filenames = ['.*']
    ignore_dir = set(ignore_dir)
    ignore_dir = [re.compile(i) for i in ignore_dir]
    for directory in directories:
        if os.path.isdir(directory):
            # for f in glob.iglob(args.directory, recursive=True):
            stop = False
            for path, _, files in os.walk(directory):
                for p in set(split(path)):
                    for i in ignore_dir:
                        stop = i.match(p) is not None
                        if stop:
                            break
                    if stop:
                        break
                if stop:
                    continue
                for f_ in files:
                    for filename in filenames:
                        if re.match(filename, f_):
                            full_path = re.sub(
                                "^\./", "", os.path.join(path, f_)
                            )
                            yield full_path, f_
                            break
        elif os.path.isfile(directory):
            yield directory, os.path.split(directory)[-1]


def confirm(prompt=None, resp=False):
    """
    Prompts for yes or no response from the user. Returns True for yes and
    False for no.

    'resp' should be set to the default value assumed by the caller when
    user simply types ENTER.

    >>> confirm(prompt='Create Directory?', resp=True)
    Create Directory? [y]|n:
    True
    >>> confirm(prompt='Create Directory?', resp=False)
    Create Directory? [n]|y:
    False
    >>> confirm(prompt='Create Directory?', resp=False)
    Create Directory? [n]|y: y
    True
    """

    if prompt is None:
        prompt = "Confirm"

    if resp:
        prompt = "{0!s} [{1!s}]|{2!s}: ".format(prompt, "y", "n")
    else:
        prompt = "{0!s} [{1!s}]|{2!s}: ".format(prompt, "n", "y")

    while True:
        ans = input(prompt)
        if not ans:
            return resp
        if ans not in ["y", "Y", "n", "N"]:
            print("please enter y or n.")
            continue
        if ans in ["y", "Y"]:
            return True
        if ans in ["n", "N"]:
            return False


def read_metadata(filename, read_types=True):
    metadata = json.loads(str(subprocess.check_output([
        "/usr/bin/exiftool", "-json", filename
    ]), encoding='utf-8', errors='strict'))[0]
    if read_types is True:
        for k in metadata.keys():
            if isinstance(metadata[k], str):
                try:
                    metadata[k] = datetime.datetime.strptime(
                        metadata[k], "%Y:%m:%d %H:%M:%S"
                    )
                except ValueError:
                    try:
                        metadata[k] = datetime.datetime.strptime(
                            metadata[k], "%Y:%m:%d %H:%M:%S%z"
                        )
                    except ValueError:
                        try:
                            metadata[k] = datetime.datetime.strptime(
                                metadata[k], "%d/%m/%Y %H:%M:%S"
                            )
                        except ValueError:
                            pass
    return metadata
