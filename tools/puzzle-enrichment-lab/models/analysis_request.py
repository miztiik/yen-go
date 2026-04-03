"""Analysis request model — sent to KataGo engine."""

from pydantic import BaseModel, Field

from .position import Position


class AnalysisRequest(BaseModel):
    """Request payload for KataGo analysis."""
    request_id: str = Field(default="req_001")
    position: Position
    max_visits: int = Field(default=200, ge=1, le=100000)
    include_ownership: bool = True
    include_pv: bool = True
    include_policy: bool = False
    # Additional moves played on top of position (for analyzing after a move)
    moves: list[list[str]] = Field(
        default_factory=list,
        description='Moves in GTP format [["B","D4"],["W","C5"]]'
    )
    # Restrict analysis to moves near existing stones (puzzle region focus)
    # If set, KataGo will only consider moves within this region
    allowed_moves: list[str] | None = Field(
        default=None,
        description='List of GTP coordinates to restrict analysis to (e.g., ["C3","D4"])'
    )
    # Ko-aware rules override (Phase S.4, ADR D31).
    # Default "chinese" uses superko; "tromp-taylor" uses simple ko
    # (only immediate recapture banned), letting KataGo explore ko sequences.
    rules: str = Field(
        default="chinese",
        description='KataGo rules string: "chinese" (superko) or "tromp-taylor" (simple ko)',
    )
    # Per-request PV length override for ko puzzles.
    # When set, overrides the cfg-level analysisPVLen. Ko fights produce
    # longer PV sequences that need 30+ moves to capture the full fight.
    analysis_pv_len: int | None = Field(
        default=None,
        ge=1, le=100,
        description="Per-request analysisPVLen override (None = use cfg default)",
    )
    # Correct move GTP coordinate for dual-engine F2 tiebreaker (G2 fix).
    # Set by the enrichment pipeline so _compare_results can use per-move
    # winrate instead of root_winrate when Quick/Referee disagree on top move.
    correct_move_gtp: str = Field(
        default="",
        description="Correct move GTP coord for dual-engine tiebreaker (optional)",
    )
    # Report winrates from Black's perspective for consistent interpretation.
    report_analysis_winrates_as: str = Field(
        default="BLACK",
        description="Perspective for winrate reporting: BLACK or WHITE",
    )
    # A8: Per-request KataGo config overrides via overrideSettings.
    # Used to pass rootNumSymmetriesToSample from enrichment config
    # instead of relying on the .cfg file default.
    override_settings: dict[str, int | float | str | bool] | None = Field(
        default=None,
        description="Per-request KataGo config overrides (e.g. rootNumSymmetriesToSample)",
    )
    # Q8: max_time for KataGo query (0 = no limit)
    max_time: float = Field(
        default=0,
        ge=0,
        description="Max seconds per query (0 = unlimited, passed as maxTime to KataGo)",
    )
    # Phase 3: HumanSL profile (feature-gated, absent by default)
    human_sl_profile: str | None = Field(
        default=None,
        description="HumanSL profile name (feature-gated, absent by default)",
    )

    def to_katago_json(self) -> dict:
        """Convert to KataGo analysis engine JSON format.

        Note: reportAnalysisWinratesAs is a cfg-level setting, not a per-query
        field.  It is set in tsumego_analysis.cfg (SIDETOMOVE) and must NOT be
        sent as a JSON field — KataGo will emit a warning and ignore it.
        """
        payload: dict = {
            "id": self.request_id,
            "initialStones": self.position.to_katago_initial_stones(),
            "moves": self.moves,
            "rules": self.rules,
            "komi": self.position.komi,
            "boardXSize": self.position.board_size,
            "boardYSize": self.position.board_size,
            "analyzeTurns": [len(self.moves)],
            "maxVisits": self.max_visits,
        }
        # Q8: Wire max_time to KataGo maxTime field
        if self.max_time > 0:
            payload["maxTime"] = self.max_time
        if self.analysis_pv_len is not None:
            payload["analysisPVLen"] = self.analysis_pv_len
        if self.override_settings:
            payload["overrideSettings"] = dict(self.override_settings)
        if self.include_ownership:
            payload["includeOwnership"] = True
        if self.include_pv:
            payload["includePVVisits"] = True
        if self.include_policy:
            payload["includePolicy"] = True
        if self.human_sl_profile:
            payload["humanSLProfile"] = self.human_sl_profile
        # Tell KataGo who plays next
        if not self.moves:
            payload["initialPlayer"] = self.position.player_to_move.value
        # Restrict moves to puzzle region if specified.
        # KataGo allowMoves accepts a list of dicts:
        #   [{"player": "B", "moves": ["C3","D4"], "untilDepth": N}]
        # untilDepth=1 restricts only the first move (the puzzle answer);
        # subsequent response/refutation moves are unrestricted so KataGo
        # can explore the full tree.
        if self.allowed_moves:
            player = self.position.player_to_move.value
            if self.moves:
                # After N moves, the player alternates from initial player
                is_initial_player_turn = (len(self.moves) % 2 == 0)
                if is_initial_player_turn:
                    player = self.position.player_to_move.value
                else:
                    player = "W" if self.position.player_to_move.value == "B" else "B"
            payload["allowMoves"] = [
                {"player": player, "moves": list(self.allowed_moves), "untilDepth": 1}
            ]
        return payload

    @classmethod
    def with_puzzle_region(
        cls,
        position: "Position",
        max_visits: int = 200,
        margin: int = 2,
        **kwargs,
    ) -> "AnalysisRequest":
        """Create a request with allowedMoves restricted to the puzzle region.

        Computes the bounding box of all stones + margin, and only allows
        moves within that region. This prevents KataGo from suggesting moves
        on the far side of an empty 19x19 board.

        Args:
            position: Board position with stones
            max_visits: MCTS visits
            margin: Extra rows/cols around the stone bounding box (default 2)
        """
        region_moves = position.get_puzzle_region_moves(margin=margin)
        return cls(
            position=position,
            max_visits=max_visits,
            allowed_moves=region_moves if region_moves else None,
            **kwargs,
        )
