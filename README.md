# Bash color

## Available colors

* BLACK
* RED
* GREEN
* BROWN
* BLUE
* PURPLE
* CYAN
* LIGHT_GRAY
* DEFAULT
* DARK_GRAY
* LIGHT_RED
* LIGHT_GREEN
* YELLOW
* LIGHT_BLUE
* LIGHT_PURPLE
* LIGHT_CYAN
* WHITE

## Available effect

* BOLD
* DIM  (not working on Konsole)
* UNDERLINE
* BLINK  (not working on Konsole and Gnome Terminal)
* INVERSE
* HIDDEN  (not working on Konsole)

## Example

```python
from bash import colorize, RED, UNDERLINE

print(colorize('Red color', RED))
print(colorize('Red background', background=RED))
print(colorize('Underline', effect=UNDERLINE))
```

## API

```python
def colorize(
    text,
    color=None,
    background=None,
    effects=[],
    color_256=None,
    background_256=None,
    with_end=True):
```
