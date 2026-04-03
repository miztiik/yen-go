"""Analysis response model — received from KataGo engine."""

from pydantic import BaseModel, Field


class MoveAnalysis(BaseModel):
    """Analysis data for a single candidate move."""
    move: str = Field(description="GTP coordinate (e.g., 'D4') or 'pass'")
    visits: int = 0
    winrate: float = Field(default=0.5, ge=0.0, le=1.0)
    score_lead: float = 0.0
    policy_prior: float = Field(default=0.0, ge=0.0, le=1.0)
    play_selection_value: float = Field(
        default=0.0,
        description="KataGo playSelectionValue — blends visits + LCB for move selection.",
    )
    pv: list[str] = Field(default_factory=list, description="Principal variation in GTP coords")
    ownership: list[list[float]] | None = Field(
        default=None, description="19x19 ownership map, -1=W, +1=B"
    )

    @property
    def sgf_coord(self) -> str:
        """Convert GTP coordinate to SGF coordinate."""
        return gtp_to_sgf(self.move)

    @property
    def pv_sgf(self) -> list[str]:
        """Convert PV to SGF coordinates."""
        return [gtp_to_sgf(m) for m in self.pv]


class AnalysisResponse(BaseModel):
    """Full response from KataGo analysis engine."""
    request_id: str = ""
    move_infos: list[MoveAnalysis] = Field(default_factory=list)
    root_winrate: float = 0.5
    root_score: float = 0.0
    total_visits: int = 0
    ownership: list[float] | None = Field(
        default=None, description="Root-level ownership array (flat, board_size²)"
    )

    @property
    def top_move(self) -> MoveAnalysis | None:
        """Get the move with most visits (KataGo's best move)."""
        if not self.move_infos:
            return None
        return max(self.move_infos, key=lambda m: m.visits)

    def get_move(self, gtp_coord: str) -> MoveAnalysis | None:
        """Find analysis for a specific move."""
        for m in self.move_infos:
            if m.move.upper() == gtp_coord.upper():
                return m
        return None

    @classmethod
    def from_katago_json(cls, data: dict) -> "AnalysisResponse":
        """Parse KataGo analysis engine JSON response."""
        move_infos = []
        for mi in data.get("moveInfos", []):
            move_infos.append(MoveAnalysis(
                move=mi.get("move", "pass"),
                visits=mi.get("visits", 0),
                winrate=mi.get("winrate", 0.5),
                score_lead=mi.get("scoreLead", 0.0),
                policy_prior=mi.get("prior", 0.0),
                play_selection_value=mi.get("playSelectionValue", 0.0),
                pv=mi.get("pv", []),
                ownership=mi.get("ownership", None),
            ))

        root = data.get("rootInfo", {})
        return cls(
            request_id=data.get("id", ""),
            move_infos=move_infos,
            root_winrate=root.get("winrate", 0.5),
            root_score=root.get("scoreLead", 0.0),
            total_visits=root.get("visits", 0),
            ownership=data.get("ownership", None),
        )


def gtp_to_sgf(gtp_coord: str, board_size: int = 19) -> str:
    """Convert GTP coordinate (e.g., 'D16') to SGF coordinate (e.g., 'dc').

    Args:
        gtp_coord: GTP coordinate string (e.g., 'D16', 'pass').
        board_size: Board size (5-19). Defaults to 19.

    Returns:
        SGF coordinate string (e.g., 'dc'), or '' for pass/invalid.
    """
    if not gtp_coord or gtp_coord.lower() == "pass":
        return ""
    gtp_coord = gtp_coord.upper()
    if len(gtp_coord) < 2:
        return ""
    letters = "ABCDEFGHJKLMNOPQRST"  # GTP skips 'I'
    col_letter = gtp_coord[0]
    try:
        row_number = int(gtp_coord[1:])
    except ValueError:
        return ""

    col = letters.index(col_letter) if col_letter in letters else 0
    row = board_size - row_number  # SGF row 0 = top

    if row < 0 or row >= board_size or col < 0 or col >= board_size:
        return ""

    return chr(ord('a') + col) + chr(ord('a') + row)


def sgf_to_gtp(sgf_coord: str, board_size: int = 19) -> str:
    """Convert SGF coordinate (e.g., 'dc') to GTP coordinate (e.g., 'D16')."""
    if not sgf_coord or len(sgf_coord) < 2:
        return "pass"
    letters = "ABCDEFGHJKLMNOPQRST"
    col = ord(sgf_coord[0]) - ord('a')
    row = ord(sgf_coord[1]) - ord('a')
    col_letter = letters[col] if col < len(letters) else 'A'
    row_number = board_size - row
    return f"{col_letter}{row_number}"
