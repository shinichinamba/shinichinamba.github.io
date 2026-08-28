"""Issue collection shared by every stage of the pipeline.

A cell-level type error and a cross-record rule violation end up in the same
list with the same locator format, so one run tells the whole story.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

Level = Literal["error", "warning"]


@dataclass(frozen=True)
class Loc:
    file: str
    sheet: str | None = None
    row: int | None = None
    col: str | None = None

    def __str__(self) -> str:
        s = self.file
        if self.sheet:
            s += f"[{self.sheet}]"
        if self.col and self.row:
            s += f"!{self.col}{self.row}"
        elif self.row:
            s += f":{self.row}"
        elif self.col:
            s += f"!{self.col}"
        return s


@dataclass(frozen=True)
class Issue:
    level: Level
    code: str
    loc: Loc
    message: str
    hint: str | None = None


class Report:
    def __init__(self) -> None:
        self._issues: list[Issue] = []

    def error(self, code: str, loc: Loc, message: str,
              hint: str | None = None) -> None:
        self._issues.append(Issue("error", code, loc, message, hint))

    def warn(self, code: str, loc: Loc, message: str,
             hint: str | None = None) -> None:
        self._issues.append(Issue("warning", code, loc, message, hint))

    @property
    def issues(self) -> list[Issue]:
        return list(self._issues)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self._issues if i.level == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self._issues if i.level == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def _sorted(self) -> list[Issue]:
        return sorted(
            self._issues,
            key=lambda i: (i.loc.file, i.loc.sheet or "", i.loc.row or 0,
                           i.loc.col or "", i.code),
        )

    def render_text(self, *, show_warnings: bool = True) -> str:
        lines: list[str] = []
        for i in self._sorted():
            if i.level == "warning" and not show_warnings:
                continue
            lines.append(f"{i.level.upper():7} {i.code:24} {str(i.loc):38} "
                         f"{i.message}")
            if i.hint:
                lines.append(f"{'':7} {'':24} {'':38} hint: {i.hint}")
        n_e, n_w = len(self.errors), len(self.warnings)
        lines.append(f"\n{n_e} error(s), {n_w} warning(s)")
        return "\n".join(lines)

    def render_json(self) -> str:
        return json.dumps({
            "issues": [{
                "level": i.level, "code": i.code, "file": i.loc.file,
                "sheet": i.loc.sheet, "row": i.loc.row, "col": i.loc.col,
                "message": i.message, "hint": i.hint,
            } for i in self._sorted()],
            "summary": {"errors": len(self.errors),
                        "warnings": len(self.warnings)},
        }, ensure_ascii=False, indent=2)

    def exit_code(self, strict: bool = False) -> int:
        if self.errors:
            return 1
        if strict and self.warnings:
            return 1
        return 0
