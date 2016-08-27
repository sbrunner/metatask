# -*- coding: utf-8 -*-


import os
import re
import shutil
import threading
import metatask
import jinja2
import subprocess
import bashcolor
from tempfile import NamedTemporaryFile
from PyQt5.QtCore import QObject, pyqtSignal


def format_num_on_demon(fract):
    if fract is None:
        return ''
    if fract == '':
        return ''
    if type(fract) == int:
        return "%02d" % fract
    if type(fract) == dict:
        print(fract)
    s = fract.split("/")
    if len(s) == 1:
        return "%02d" % int(s[0])
    elif len(s) == 2:
        n, d = s
        return ("%0" + str(len(d)) + "d") % int(n)
    else:
        return fract


class Process(QObject):
    progress = pyqtSignal(int, str, str, dict)
    cancel = False
    lock = threading.Lock()

    def process(
            self, names, filenames=None, destination_filename=None,
            in_extention=None, get_content=False, metadata=None, keep=False):
        is_merged = False
        out_ext = in_extention
        cmds_config = metatask.config.get("cmds", {})
        cmds = []
        for cmd in names:
            if isinstance(cmd, str):
                c = cmds_config.get(cmd)
                if c is None:
                    raise Exception("Missing command '%s' in `cmds`" % cmd)
                c["name"] = cmd
                cmds.append(c)
            else:
                cmds.append(cmd)

        filename = filenames[0] if isinstance(filenames, list) else filenames
        if destination_filename is None:
            destination_filename = filename

        if filename is not None:
            dst, extension, types, messages = self.destination_filename(names, filename, metadata=metadata)
            if types == set():
                return
            if types == set(["rename"]):
                if filename != dst:
                    directory = os.path.dirname(dst)
                    with self.lock:
                        if directory != '' and not os.path.exists(directory):
                            os.makedirs(directory)
                        if not os.path.exists(dst):
                            shutil.move(filename, dst)
                return

        original_filename = filename
        if cmds[0].get("inplace") is True or cmds[0].get("type" == "metadata"):
            if in_extention is None:
                out_name = NamedTemporaryFile(mode='w+b').name
            else:
                out_name = NamedTemporaryFile(
                    mode='w+b',
                    suffix='.' + in_extention
                ).name
            shutil.copyfile(filename, out_name)
            filename = out_name

        for no, cmd in enumerate(cmds):
            if isinstance(cmd, str):
                cmd = dict(cmd=cmd)

            if cmd.get('type') == 'rename':
                destination_filename = self._rename(cmd, destination_filename, metadata)
            if cmd.get("type" == "metadata"):
                value = cmd.get('value_format')
                value = self._format(
                    filename,
                    "^.*{}.*$".format(cmd.get("value_get")),
                    cmd.get("value_format"),
                )
                subprocess.check_output(['exiftool', '-%s=%s' % (cmd.get('name'), value), filename])
            else:
                if 'out_ext' in cmd:
                    out_ext = cmd['out_ext']

                inplace = cmd.get('inplace', False)
                cmd_cmd = cmd.get('cmd')

                if inplace:
                    out_name = filename
                else:
                    if out_ext is None:
                        out_name = NamedTemporaryFile(mode='w+b').name
                    else:
                        out_name = NamedTemporaryFile(
                            mode='w+b',
                            suffix='.' + out_ext
                        ).name

                params = {}
                if metadata is not None:
                    params.update(metadata)

                # it's a merge
                if not is_merged and isinstance(filenames, list):
                    params["in"] = " ".join([
                        "'%s'" % f.replace("'", "'\"'\"'") for f in filenames
                    ])
                    # do the merge only one time
                    is_merged = True
                elif filename is not None:
                    params["in"] = "'%s'" % filename.replace("'", "'\"'\"'")

                if not inplace:
                    params["out"] = "'%s'" % out_name.replace("'", "'\"'\"'")

                try:
                    cmd_cmd = cmd_cmd.format(**params)
                except:
                    print("Error in {name}: {cmd}, with {params}".format(
                        name=cmd["name"], cmd=cmd_cmd, params=params))
                    raise

                if self.cancel is True:
                    return None, None
                print("{name}: {cmd}".format(
                    name=bashcolor.colorize(cmd["name"], bashcolor.BLUE), cmd=cmd_cmd
                ))
                self.progress.emit(no, cmd["name"], cmd_cmd, cmd)
                subprocess.check_call(cmd_cmd, shell=True)

                if filename != original_filename and not inplace:
                    os.unlink(filename)
                filename = out_name

        if get_content:
            content = None
            if os.path.exists(filename):
                with open(filename) as f:
                    content = f.read()
                if original_filename is None or original_filename != filename:
                    os.unlink(filename)
            return content, out_ext
        else:
            if out_ext is not None:
                destination_filename = "%s.%s" % (re.sub(
                    r"\.[a-z0-9A-Z]{2,5}$", "",
                    destination_filename
                ), out_ext)
            if filename != destination_filename:
                directory = os.path.dirname(destination_filename)
                with self.lock:
                    if not os.path.exists(directory):
                        os.makedirs(directory)
                    if filename != destination_filename and (
                            # apply on new file
                            filenames is None or
                            # apply a transformation on the file
                            len(filenames) == 1 and filenames[0] == destination_filename or
                            not os.path.exists(destination_filename)
                    ):
                        print("{name}: {file}".format(
                            name=bashcolor.colorize('copy', bashcolor.BLUE),
                            file=bashcolor.colorize(destination_filename, bashcolor.YELLOW),
                        ))
                        shutil.move(filename, destination_filename)
                        if not keep:
                            if isinstance(filenames, list):
                                for f in filenames:
                                    if f != filename:
                                        os.unlink(f)
                            elif original_filename is not None and original_filename != filename:
                                os.unlink(original_filename)

            return destination_filename, out_ext

    def _rename(self, cmd, destination_filename, metadata):
        from_re = cmd.get('from', '.*')
        to_re = cmd.get('to')
        format_ = cmd.get('format')
        if format_ in ['upper', 'lower']:
            def format_term(term):
                if format_ == 'upper':
                    return term.upper()
                else:
                    return term.lower()
            return re.sub(
                from_re,
                lambda m: format_term(m.group(0)),
                destination_filename
            )
        else:
            return self._format(
                destination_filename, from_re, to_re,
                cmd.get('metadata', False), metadata,
                cmd.get('template')
            )

    def _format(self, destination_filename, from_re, to_re, do_metadata=False, metadata=None, template=None):
            if do_metadata is True:
                if template == 'jinja':
                    template = jinja2.Template(to_re)
                    to_re = template.render(
                        len=len, str=str,
                        format_num_on_demon=format_num_on_demon,
                        m=metadata, **metadata
                    )
                else:
                    to_re = to_re.format(**metadata)

            return re.sub(from_re, to_re, destination_filename)

    def destination_filename(self, names, filename, extension=None, metadata=None):
        cmds_config = metatask.config.get("cmds", {})
        cmds = []
        for cmd in names:
            if isinstance(cmd, str):
                c = cmds_config.get(cmd)
                if c is None:
                    raise Exception("Missing command '%s' in `cmds`" % cmd)
                cmds.append(c)
            else:
                cmds.append(cmd)

        types = set()
        messages = []

        for cmd in cmds:
            types.add(cmd.get('type', 'cmd'))

            if cmd.get('type') == 'rename':
                if "do" in cmd:
                    for do in cmd["do"]:
                        filename = self._rename(do, filename, metadata)
                else:
                    filename = self._rename(cmd, filename, metadata)
            if cmd.get("type" == "metadata"):
                value = cmd.get('value_format')
                value = self._format(
                    filename,
                    "^.*{}.*$".format(cmd.get("value_get")),
                    cmd.get("value_format"),
                )
                messages.append("Set the metadata '%s' to '%s'." % (
                    bashcolor.colorize(cmd.get('name'), bashcolor.BLUE),
                    bashcolor.colorize(value, bashcolor.GREEN)
                ))
            else:
                if 'out_ext' in cmd:
                    extension = cmd['out_ext']

        if extension is not None:
            filename = "%s.%s" % (re.sub(
                r"\.[a-z0-9A-Z]{2,5}$", "",
                filename
            ), extension)
        return filename, extension, types, messages
