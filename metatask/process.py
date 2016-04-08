# -*- coding: utf-8 -*-


import os
import re
import shutil
import threading
import metatask
from tempfile import NamedTemporaryFile
from subprocess import check_call
from PyQt5.QtCore import QObject, pyqtSignal


class Process(QObject):
    progress = pyqtSignal(int, str, str, dict)
    cancel = False
    lock = threading.Lock()

    def process(
            self, names, filename=None, destination_filename=None,
            in_extention=None, get_content=False, metadata=None):
        out_ext = in_extention
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

        if filename is not None:
            dst, extension, types = self.destination_filename(names, filename, metadata=metadata)
            if types == set():
                return
            if types == set(["rename"]):
                if filename != dst:
                    directory = os.path.dirname(dst)
                    with self.lock:
                        if not os.path.exists(directory):
                            os.makedirs(directory)
                        if not os.path.exists(dst):
                            shutil.move(filename, dst)
                return

        original_filename = filename
        if cmds[0].get("inplace") is True:
            if in_extention is None:
                out_name = NamedTemporaryFile(mode='w+b').name
            else:
                out_name = NamedTemporaryFile(
                    mode='w+b',
                    suffix='.' + in_extention
                ).name
            shutil.copyfile(filename, out_name)
            filename = out_name

        if destination_filename is None:
            destination_filename = filename
        for no, name in enumerate(cmds):
            cmd = cmds_config.get(name)
            if cmd is None:
                raise "Missing command '%s' in `cmds`" % name

            if isinstance(cmd, str):
                cmd = dict(cmd=cmd)

            if cmd.get('type') == 'rename':
                destination_filename = self._rename(cmd, destination_filename, metadata)
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

                if filename is not None:
                    params["in"] = "'%s'" % filename.replace("'", "'\"'\"'")

                if not inplace:
                    params["out"] = "'%s'" % out_name.replace("'", "'\"'\"'")

                try:
                    cmd_cmd = cmd_cmd.format(**params)
                except:
                    print("Error in {name}: {cmd}, with {params}".format(
                        name=name, cmd=cmd_cmd, params=params))
                    raise

                if self.cancel is True:
                    return None, None
                print("{name}: {cmd}".format(name=name, cmd=cmd_cmd))
                self.progress.emit(no, name, cmd_cmd, cmd)
                check_call(cmd_cmd, shell=True)

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
                    if not os.path.exists(destination_filename) and filename != destination_filename:
                        shutil.move(filename, destination_filename)
                        if original_filename is not None and original_filename != filename:
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
            do_metadata = cmd.get('metadata', False) is True and metadata is not None
            return re.sub(
                from_re,
                to_re.format(**metadata) if do_metadata is not None else to_re,
                destination_filename
            )

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

        for cmd in cmds:
            types.add(cmd.get('type'))

            if cmd.get('type') == 'rename':
                if "do" in cmd:
                    for do in cmd["do"]:
                        filename = self._rename(do, filename, metadata)
                else:
                    filename = self._rename(cmd, filename, metadata)
            else:
                if 'out_ext' in cmd:
                    extension = cmd['out_ext']

        if extension is not None:
            filename = "%s.%s" % (re.sub(
                r"\.[a-z0-9A-Z]{2,5}$", "",
                filename
            ), extension)
        return filename, extension, types
