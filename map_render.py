"""Render an ASCII map of discovered rooms.

Rooms sit on an integer (x, y) grid. Discovered rooms are drawn as ``[Lbl]``
boxes; the current room is drawn as ``*Lbl*``; a room you have seen an exit to
but not yet visited is drawn as ``[ ? ]``. Boxes are joined by ``-`` and ``|``
connectors that follow the real exits.

The map is a *camera*, not the whole world: it draws a fixed VIEW_COLS x
VIEW_ROWS window centered on the room you are standing in, so the display stays
the same size no matter how far the cave sprawls. Corridors leading past the
edge are drawn as stubs, and a hint line names the directions where the map
continues off-screen.
"""

from models import Room

COL_STEP = 6  # horizontal distance between adjacent room cells
ROW_STEP = 2  # vertical distance between adjacent room cells
LABEL_WIDTH = 3  # every label is padded to this so the grid stays aligned
BOX_WIDTH = LABEL_WIDTH + 2  # width of "[Lbl]" / "*Lbl*"

VIEW_COLS = 7  # room cells shown across (odd, so the player sits centered)
VIEW_ROWS = 5  # room cells shown down
PAD = 1  # margin so connectors leaving the window still have a cell to draw in

# The drawn grid is always exactly this tall, whatever the world looks like.
GRID_HEIGHT = (VIEW_ROWS - 1) * ROW_STEP + 1 + 2 * PAD


def _box(label: str, marker: tuple[str, str]) -> str:
    """Draw one room box, padding short labels so every box is BOX_WIDTH wide."""
    left, right = marker
    return f"{left}{label[:LABEL_WIDTH].center(LABEL_WIDTH)}{right}"


def _visible_keys(world: dict[str, Room], discovered: set[str]) -> set[str]:
    """Discovered rooms plus any room reachable from one in a single step."""
    keys = set(discovered)
    for key in discovered:
        for target in world[key].exits.values():
            keys.add(target)
    return keys


def build_map(
    world: dict[str, Room],
    discovered: set[str],
    current: str,
    view_cols: int = VIEW_COLS,
    view_rows: int = VIEW_ROWS,
) -> list[str]:
    """Return the map as a list of text lines, centered on ``current``."""
    if not discovered:
        return ["(no map yet)"]

    visible = _visible_keys(world, discovered)
    focus = world[current]

    # The window follows the player: it is always the same size, centered here.
    min_x = focus.x - view_cols // 2
    max_x = min_x + view_cols - 1
    min_y = focus.y - view_rows // 2
    max_y = min_y + view_rows - 1

    width = (view_cols - 1) * COL_STEP + BOX_WIDTH + 2 * PAD
    height = (view_rows - 1) * ROW_STEP + 1 + 2 * PAD  # == GRID_HEIGHT by default
    canvas = [[" "] * width for _ in range(height)]

    def cell(room: Room) -> tuple[int, int]:
        col = (room.x - min_x) * COL_STEP + PAD
        row = (max_y - room.y) * ROW_STEP + PAD
        return row, col

    def stamp(row: int, col: int, text: str) -> None:
        """Draw text at a position, silently clipping anything off-canvas."""
        for offset, char in enumerate(text):
            c = col + offset
            if 0 <= row < height and 0 <= c < width:
                canvas[row][c] = char

    def in_window(room: Room) -> bool:
        return min_x <= room.x <= max_x and min_y <= room.y <= max_y

    # Boxes first, for rooms inside the window.
    for key in visible:
        room = world[key]
        if not in_window(room):
            continue
        row, col = cell(room)
        if key not in discovered:
            stamp(row, col, _box("?", ("[", "]")))
        elif key == current:
            stamp(row, col, _box(room.label, ("*", "*")))
        else:
            stamp(row, col, _box(room.label, ("[", "]")))

    # Connectors follow real exits. Rooms just outside the window are included
    # so their corridors show as stubs entering from the edge; stamp() clips.
    for key in discovered:
        room = world[key]
        if not (min_x - 1 <= room.x <= max_x + 1 and min_y - 1 <= room.y <= max_y + 1):
            continue
        row, col = cell(room)
        for target in room.exits.values():
            if target not in visible:
                continue
            other = world[target]
            if other.x == room.x + 1 and other.y == room.y:
                stamp(row, col + BOX_WIDTH, "-")
            elif other.x == room.x - 1 and other.y == room.y:
                stamp(row, col - 1, "-")
            elif other.y == room.y + 1 and other.x == room.x:
                stamp(row - 1, col + 2, "|")
            elif other.y == room.y - 1 and other.x == room.x:
                stamp(row + 1, col + 2, "|")

    lines = ["".join(line).rstrip() for line in canvas]
    lines.append("")
    lines.append(f"YOU ARE HERE: *{focus.label}* {focus.name}")

    # Always emit this row -- blank when nothing lies beyond the window -- so
    # the map block is a constant height and the panel below never jitters.
    beyond = _offscreen_directions(world, visible, min_x, max_x, min_y, max_y)
    lines.append(f"(map continues: {', '.join(beyond)})" if beyond else "")

    # Kept under ui.WIDTH (62) so the legend never wraps in the framed layout.
    lines.append("legend: [Abc] seen  *Abc* you  [ ? ] unknown  ! deadly")
    return lines


def _offscreen_directions(
    world: dict[str, Room],
    visible: set[str],
    min_x: int,
    max_x: int,
    min_y: int,
    max_y: int,
) -> list[str]:
    """Name the compass directions where known rooms lie outside the window."""
    found = []
    for key in visible:
        room = world[key]
        if room.y > max_y:
            found.append("north")
        if room.y < min_y:
            found.append("south")
        if room.x > max_x:
            found.append("east")
        if room.x < min_x:
            found.append("west")
    # Preserve a stable compass order rather than set order.
    return [name for name in ("north", "south", "east", "west") if name in found]
