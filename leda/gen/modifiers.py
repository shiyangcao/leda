from __future__ import annotations

import dataclasses
import logging
import pathlib
from typing import ClassVar, List, MutableMapping, Optional

import nbformat

import leda.gen.base

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

TOC_LEVELS = ["I", "A", "1", "a", "i"]


def insert_toc(cells: List[nbformat.NotebookNode]):
    """Inserts table of contents in-place."""
    toc_cell = None
    for cell in cells:
        if cell["cell_type"] == "code" and cell["source"].strip().startswith(
            "%toc"
        ):
            toc_cell = cell
            break

    if toc_cell:
        items = []
        for cell in cells:
            if cell["cell_type"] == "markdown" and cell[
                "source"
            ].strip().startswith("#"):
                items.append(
                    (
                        cell["source"].count("#"),
                        cell["source"].replace("#", "").strip(),
                    )
                )

        html_lines = [
            "%%HTML",
            "<!-- Auto-generated by leda -->",
            "<h2>Table of Contents</h2>",
        ]
        ols = []
        prev_level_num = None
        for level_num, item in items:
            spaces = " " * level_num * 2
            prev_spaces = None
            if prev_level_num is not None:
                prev_spaces = " " * prev_level_num * 2

            if prev_level_num is not None and level_num < prev_level_num:
                html_lines.append(f"{prev_spaces}</ol>")
                ols.pop()
            elif prev_level_num is None or level_num > prev_level_num:
                html_lines.append(
                    f"{spaces}<ol type='{TOC_LEVELS[level_num - 1]}'>"
                )
                ols.append(level_num)

            href = "#" + item.replace(" ", "-")
            html_lines.append(
                f"{spaces}<li type='{TOC_LEVELS[level_num - 1]}'>"
                f"<a href='{href}'>{item}</a></li>"
            )

            prev_level_num = level_num

        while ols:
            level_num = ols.pop()
            spaces = " " * level_num * 2
            html_lines.append(f"{spaces}</ol>")

        toc_cell["source"] = "\n".join(html_lines)


@dataclasses.dataclass()
class StaticReportModifier(leda.gen.base.ReportModifier):
    static_interact_mode_cls_name: ClassVar[str]

    inject_code: Optional[str] = None

    def _get_new_cells_top(self) -> List[nbformat.NotebookNode]:
        new_cells = [
            nbformat.v4.new_code_cell(
                f"""
# Auto-generated by leda
import leda


leda.set_interact_mode(leda.{self.static_interact_mode_cls_name}())"""
            ),
        ]

        if self.inject_code:
            new_cells.append(
                nbformat.v4.new_code_cell(
                    f"""
# Injected by user
{self.inject_code}"""
                )
            )

        return new_cells

    def _get_new_cells_bottom(self) -> List[nbformat.NotebookNode]:
        return [
            nbformat.v4.new_markdown_cell("---"),
            nbformat.v4.new_code_cell(
                """
# Auto-generated by leda
import leda


leda.show_input_toggle()"""
            ),
            nbformat.v4.new_code_cell(
                """
# Auto-generated by leda
import leda


leda.show_std_output_toggle()"""
            ),
        ]

    def modify(self, nb_contents: MutableMapping):
        logger.info("Modifying notebook")

        new_cells_top = self._get_new_cells_top()
        new_cells_bottom = self._get_new_cells_bottom()
        nb_contents["cells"] = (
            new_cells_top + nb_contents["cells"] + new_cells_bottom
        )

        insert_toc(nb_contents["cells"])


@dataclasses.dataclass()
class StaticPanelReportModifier(StaticReportModifier):
    static_interact_mode_cls_name: ClassVar[str] = "StaticPanelInteractMode"

    inject_code: Optional[str] = None


@dataclasses.dataclass()
class _StaticIpywidgetsReportModifier:
    local_dir_path: pathlib.Path


@dataclasses.dataclass()
class StaticIpywidgetsReportModifier(
    StaticReportModifier, _StaticIpywidgetsReportModifier
):
    static_interact_mode_cls_name: ClassVar[
        str
    ] = "StaticIpywidgetsInteractMode"

    def __post_init__(self):
        local_img_dir_path = self.local_dir_path / "images"
        local_img_dir_path.mkdir(parents=True, exist_ok=True)

    def _get_new_cells_top(self) -> List[nbformat.NotebookNode]:
        new_cells = super()._get_new_cells_top()

        new_cells.append(
            nbformat.v4.new_code_cell(
                f"""
# Auto-generated by leda
import os

from leda.vendor.static_ipywidgets.static_ipywidgets \
    import interact as static_interact

static_interact.IMAGE_MANAGER = static_interact.FileImageManager(
    path=os.path.join({str(self.local_dir_path)!r}, "images"),
)
"""
            ),
        )

        return new_cells
