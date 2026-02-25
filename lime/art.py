import curses

# Pixel grid traced from the lime sprite.
# B = brown (stem), G = green (body), W = white (highlight), . = empty
LIME_GRID = [
    "......BB..",
    ".....B....",
    "...GGGG...",
    "..GGGGGG..",
    ".GWGGGGGG.",
    ".GGGGGGGG.",
    ".GGGGGGGG.",
    "..GGGGGG..",
    "....GG....",
]

BLOCK = "\u2588\u2588"

ART_WIDTH = 20   # 10 columns * 2 chars
ART_HEIGHT = len(LIME_GRID)

_CELL_COLOR = {
    "G": 1,   # COLOR_GREEN
    "B": 2,   # COLOR_BROWN
    "W": 3,   # COLOR_WHITE
}

_CELL_BOLD = {"G", "W"}


def draw_lime(stdscr, start_y: int, start_x: int):
    for row_idx, row in enumerate(LIME_GRID):
        for col_idx, cell in enumerate(row):
            pair = _CELL_COLOR.get(cell)
            if pair is None:
                continue
            attr = curses.color_pair(pair)
            if cell in _CELL_BOLD:
                attr |= curses.A_BOLD
            try:
                stdscr.addstr(start_y + row_idx, start_x + col_idx * 2, BLOCK, attr)
            except curses.error:
                pass
