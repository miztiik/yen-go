"""KaTrain SGF parser — pure-Python SGF parser.

Stripped copy of KaTrain's sgf_parser.py (MIT License).
Source: https://github.com/sanderland/katrain

Stripped items:
- chardet import and parse_file() (file-based parsing)
- parse_gib() and parse_ngf() (multi-format support)

Kept: Move, SGFNode, SGF.parse_sgf(), _parse_branch(), place_handicap_stones()
"""

from __future__ import annotations

import copy
import re
from collections import defaultdict


class ParseError(Exception):
    """SGF parse error."""


class IllegalMoveError(Exception):
    """Illegal move."""


class Move:
    """Represents a Go move (or placement)."""

    GTP_COORD = "ABCDEFGHJKLMNOPQRSTUVWXYZ"

    def __init__(self, coords: tuple[int, int] | None = None, player: str = "B", *, is_pass: bool = False):
        self.coords = coords
        self.player = player
        self.is_pass = is_pass or coords is None

    def __repr__(self) -> str:
        return f"Move({self.player}, {self.gtp()})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Move):
            return NotImplemented
        return self.coords == other.coords and self.player == other.player

    def __hash__(self) -> int:
        return hash((self.coords, self.player))

    def sgf(self, board_size: tuple[int, int] = (19, 19)) -> str:
        """Return SGF coordinate string (e.g., 'cd')."""
        if self.is_pass or self.coords is None:
            return ""
        x, y = self.coords
        return chr(ord("a") + x) + chr(ord("a") + y)

    def gtp(self, board_size: tuple[int, int] = (19, 19)) -> str:
        """Return GTP coordinate string (e.g., 'D16')."""
        if self.is_pass or self.coords is None:
            return "pass"
        x, y = self.coords
        return self.GTP_COORD[x] + str(board_size[1] - y)

    @classmethod
    def from_sgf(cls, sgf_coords: str, player: str = "B", board_size: tuple[int, int] = (19, 19)) -> Move:
        """Create Move from SGF coordinate string."""
        if not sgf_coords or sgf_coords == "tt":
            return cls(player=player, is_pass=True)
        x = ord(sgf_coords[0]) - ord("a")
        y = ord(sgf_coords[1]) - ord("a")
        return cls(coords=(x, y), player=player)

    @classmethod
    def from_gtp(cls, gtp_coords: str, player: str = "B", board_size: tuple[int, int] = (19, 19)) -> Move:
        """Create Move from GTP coordinate string."""
        if not gtp_coords or gtp_coords.lower() == "pass":
            return cls(player=player, is_pass=True)
        col = gtp_coords[0].upper()
        x = cls.GTP_COORD.index(col)
        y = board_size[1] - int(gtp_coords[1:])
        return cls(coords=(x, y), player=player)


class SGFNode:
    """A node in an SGF game tree."""

    # Standard SGF properties with list-type values
    _LIST_PROPERTIES = {"AB", "AW", "AE", "AR", "CR", "DD", "LB", "LN", "MA", "SL", "SQ", "TR", "VW"}

    def __init__(self, parent: SGFNode | None = None, properties: dict | None = None, move: Move | None = None):
        self.parent = parent
        self.children: list[SGFNode] = []
        self.properties: defaultdict[str, list[str]] = defaultdict(list)
        self.move: Move | None = move
        if properties:
            for k, v in properties.items():
                if isinstance(v, list):
                    self.properties[k] = v
                else:
                    self.properties[k] = [v]
        if parent is not None:
            parent.children.append(self)

    def __repr__(self) -> str:
        return f"SGFNode(move={self.move}, props={dict(self.properties)}, children={len(self.children)})"

    @property
    def board_size(self) -> tuple[int, int]:
        """Board size from root SZ property, walking up to root."""
        node: SGFNode | None = self
        while node is not None:
            if "SZ" in node.properties:
                sz = node.properties["SZ"][0]
                if ":" in sz:
                    parts = sz.split(":")
                    return (int(parts[0]), int(parts[1]))
                size = int(sz)
                return (size, size)
            node = node.parent
        return (19, 19)

    @property
    def is_root(self) -> bool:
        return self.parent is None

    @property
    def root(self) -> SGFNode:
        """Walk up to root."""
        node = self
        while node.parent is not None:
            node = node.parent
        return node

    @property
    def depth(self) -> int:
        d = 0
        node = self
        while node.parent is not None:
            d += 1
            node = node.parent
        return d

    @property
    def placements(self) -> list[Move]:
        """Return AB/AW stone placements on this node."""
        moves: list[Move] = []
        bs = self.board_size
        for coord in self.properties.get("AB", []):
            moves.append(Move.from_sgf(coord, "B", bs))
        for coord in self.properties.get("AW", []):
            moves.append(Move.from_sgf(coord, "W", bs))
        return moves

    def get_property(self, key: str, default: str = "") -> str:
        """Get first value for a property key."""
        vals = self.properties.get(key, [])
        return vals[0] if vals else default

    def get(self, key: str, default: str = "") -> str:
        """Alias for get_property (backward compatibility)."""
        return self.get_property(key, default)

    def get_list_property(self, key: str) -> list[str]:
        """Get all values for a property key."""
        return self.properties.get(key, [])

    def get_all(self, key: str) -> list[str]:
        """Alias for get_list_property (backward compatibility)."""
        return self.get_list_property(key)

    def set_property(self, key: str, value: str) -> None:
        """Set a property to a single value."""
        self.properties[key] = [value]

    def add_list_property(self, prop: str, values: list[str]) -> None:
        """Add list-type property values."""
        # Normalize property name (strip lowercase)
        clean_prop = re.sub("[a-z]", "", prop)
        if clean_prop:
            prop = clean_prop
        self.properties[prop].extend(values)

    @property
    def comment(self) -> str:
        """Shorthand for C[] property."""
        return self.get_property("C", "")

    @comment.setter
    def comment(self, value: str) -> None:
        self.set_property("C", value)

    @property
    def initial_player(self) -> str:
        """Infer first player from PL property or first child move."""
        pl = self.get_property("PL", "")
        if pl:
            return pl
        for child in self.children:
            if child.move:
                return child.move.player
        return "B"

    def play(self, move: Move) -> SGFNode:
        """Create a child node with the given move."""
        child = SGFNode(parent=self, move=move)
        child.properties[move.player] = [move.sgf(self.board_size)]
        return child

    def sgf_properties(self) -> dict[str, list[str]]:
        """Return a copy of properties."""
        return copy.deepcopy(dict(self.properties))

    def sgf(self) -> str:
        """Serialize this node and its subtree to SGF string."""
        return "(" + self._sgf_recursive() + ")"

    def _sgf_recursive(self) -> str:
        """Recursive SGF serialization."""
        parts = [";"]
        for key, values in self.properties.items():
            if key in self._LIST_PROPERTIES:
                parts.append(key + "".join(f"[{_escape_sgf(v)}]" for v in values))
            else:
                for v in values:
                    parts.append(f"{key}[{_escape_sgf(v)}]")
        result = "".join(parts)

        if len(self.children) == 1:
            result += "\n" + self.children[0]._sgf_recursive()
        elif len(self.children) > 1:
            for child in self.children:
                result += "\n(" + child._sgf_recursive() + ")"

        return result


def _escape_sgf(value: str) -> str:
    """Escape special characters for SGF output."""
    return value.replace("\\", "\\\\").replace("]", "\\]")


def _unescape_sgf(value: str) -> str:
    """Unescape SGF property values."""
    return value.replace("\\]", "]").replace("\\\\", "\\")


class SGF:
    """SGF parser — parses SGF strings into SGFNode trees."""

    @classmethod
    def parse_sgf(cls, sgf_string: str) -> SGFNode:
        """Parse an SGF string and return the root SGFNode.

        Args:
            sgf_string: SGF content as string.

        Returns:
            Root SGFNode of the parsed game tree.

        Raises:
            ParseError: If the SGF is invalid.
        """
        sgf_string = sgf_string.strip()
        if not sgf_string:
            raise ParseError("Empty SGF string")

        # Find the start of the game tree
        ix = sgf_string.find("(")
        if ix < 0:
            raise ParseError("No game tree found in SGF")

        root, _ = cls._parse_branch(sgf_string, ix + 1)
        return root

    @classmethod
    def _parse_branch(cls, sgf_string: str, ix: int, parent: SGFNode | None = None) -> tuple[SGFNode, int]:
        """Parse a branch of the SGF tree starting at position ix.

        Returns:
            Tuple of (first node of this branch, position after branch).
        """
        first_node: SGFNode | None = None
        current_node: SGFNode | None = parent
        node_started = False

        while ix < len(sgf_string):
            c = sgf_string[ix]

            if c == ")":
                # End of this branch
                if first_node is None and not node_started:
                    raise ParseError("Empty branch in SGF")
                return first_node or current_node, ix + 1

            elif c == "(":
                # Start of a sub-branch (variation)
                if current_node is None:
                    raise ParseError("Variation before any node")
                _, ix = cls._parse_branch(sgf_string, ix + 1, parent=current_node)

            elif c == ";":
                # New node
                node = SGFNode(parent=current_node if node_started else parent)
                if not node_started and parent is not None:
                    # This is the first node of a sub-branch attached to parent
                    pass
                if first_node is None:
                    first_node = node
                current_node = node
                node_started = True
                ix += 1

            elif c.isupper():
                # Property name
                if current_node is None:
                    raise ParseError("Property before any node")
                prop_name, ix = cls._parse_property_name(sgf_string, ix)
                prop_values, ix = cls._parse_property_values(sgf_string, ix)

                # Handle move properties
                if prop_name in ("B", "W"):
                    sgf_coord = prop_values[0] if prop_values else ""
                    bs = current_node.board_size
                    current_node.move = Move.from_sgf(sgf_coord, prop_name, bs)

                # Store properties
                if prop_name in SGFNode._LIST_PROPERTIES:
                    current_node.properties[prop_name].extend(prop_values)
                else:
                    current_node.properties[prop_name] = prop_values

            else:
                ix += 1

        raise ParseError("Unexpected end of SGF (missing closing parenthesis)")

    @classmethod
    def _parse_property_name(cls, sgf_string: str, ix: int) -> tuple[str, int]:
        """Parse property name starting at ix."""
        start = ix
        while ix < len(sgf_string) and (sgf_string[ix].isupper() or sgf_string[ix].islower()):
            ix += 1
        name = sgf_string[start:ix]
        # Normalize: strip lowercase letters
        clean = re.sub("[a-z]", "", name)
        return clean or name, ix

    @classmethod
    def _parse_property_values(cls, sgf_string: str, ix: int) -> tuple[list[str], int]:
        """Parse property values (one or more [value] blocks)."""
        values: list[str] = []

        # Skip whitespace to find first [
        while ix < len(sgf_string) and sgf_string[ix] in " \t\n\r":
            ix += 1

        while ix < len(sgf_string) and sgf_string[ix] == "[":
            ix += 1  # Skip [
            value_chars: list[str] = []
            while ix < len(sgf_string):
                c = sgf_string[ix]
                if c == "\\":
                    # Escape sequence
                    ix += 1
                    if ix < len(sgf_string):
                        next_c = sgf_string[ix]
                        if next_c == "\n":
                            pass  # Soft line break — skip
                        elif next_c == "\r":
                            ix += 1
                            if ix < len(sgf_string) and sgf_string[ix] == "\n":
                                ix += 1
                            continue
                        else:
                            value_chars.append(next_c)
                    ix += 1
                elif c == "]":
                    ix += 1
                    break
                else:
                    value_chars.append(c)
                    ix += 1
            values.append("".join(value_chars))

            # Skip whitespace between values
            while ix < len(sgf_string) and sgf_string[ix] in " \t\n\r":
                ix += 1

        return values, ix


def place_handicap_stones(board_size: int, count: int) -> list[Move]:
    """Generate handicap stone placements for given board size and count."""
    if count < 2 or board_size < 5:
        return []

    near = 3 if board_size >= 13 else 2
    far = board_size - 1 - near
    mid = board_size // 2

    corners = [(near, near), (far, far), (near, far), (far, near)]
    sides = [(near, mid), (far, mid), (mid, near), (mid, far)]
    center = [(mid, mid)]

    if count <= 4:
        points = corners[:count]
    elif count == 5:
        points = corners + center
    elif count == 6:
        points = corners + sides[2:4]
    elif count == 7:
        points = corners + sides[2:4] + center
    elif count == 8:
        points = corners + sides
    else:  # 9
        points = corners + sides + center

    return [Move(coords=p, player="B") for p in points[:count]]
