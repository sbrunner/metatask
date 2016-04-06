# Meta Task

Tools that support:
- Runs commands on a set of files
- Mupty process the for fast run
- Read metadata from the file with exiftool
- Use metadata in rename or command
- Set metadata on the file
- Rename or move the file

Config file `<Standard config path>/metatask.yaml`, `~/.config/metatask.yaml` on Linux

Syntax:
```yaml
nb_process: <number of concurent process>

chains:
    <name>:
        display: <text>
        source-mime: <mimie type>
        commands: [<list of commands>]

cmds:
    <name>:
        display: <text>
        metadata: True # => get some metadata with `exiftool` and can be used with python format syntax
        ...
    <name>:
        display: <text>
        cmd: <the command with {in} and {out} (if not inplace)>
        out_ext: <the output extension (optional)>
        inplace: <True|False default is False>
    <name>:
        display: <text>
        type: rename
        from: <regexp>
        to: <pattern with \1, ...>
    <name>:
        display: <text>
        type: rename
        do:
        - from: <regexp>
          to: <pattern with \1, ...>
    <name>:
        display: <text>
        type: rename
        from: <regexp>
        format: <lower|higher>
    <name>:
        display: <text>
        type: metadata
        name: <metadata name>
        value_get: <regexp used on filename>
        value_format: <pattern with \1, ...>
```
