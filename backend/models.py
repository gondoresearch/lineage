"""Pydantic models for storage, requests and responses."""

import datetime as dt
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(
        extra="forbid", populate_by_name=True, serialize_by_alias=True
    )


Shape = Literal[
    "open-circle",
    "filled-circle",
    "diamond",
    "filled-diamond",
    "square",
    "filled-square",
    "triangle",
    "filled-triangle",
    "star",
    "filled-star",
    "cross",
]
# Line patterns shared by states (lane segments) and reference types.
Line = Literal["solid", "dashed", "dotted", "long-dash", "dash-dot", "dash-dot-dot"]
MarkerIcon = Literal["warning", "question", "chain", "flag", "pin", "clock", "lock", "check", "info"]
# Symbol size of a kind, relative to the default.
Size = Annotated[float, Field(ge=0.5, le=2.0)]
# Line thickness in pixels.
Width = Annotated[float, Field(ge=0.5, le=8.0)]
# Where optional line text goes: along the line, and relative to it.
TextAlign = Literal["left", "center", "right"]
TextPosition = Literal["above", "middle", "below"]
# Font size of line text, in pixels.
TextSize = Annotated[float, Field(ge=7, le=24)]
# Reference text: always level, or rotated to follow the line.
TextOrientation = Literal["horizontal", "along"]
# Line opacity, from barely visible to fully opaque.
Opacity = Annotated[float, Field(ge=0.1, le=1.0)]
WaitingOn = Literal["me", "others", "nobody"]


class Link(Model):
    label: str
    url: str


# ---------------------------------------------------------------- stored entities
# Colours are plain strings here; graph.validate checks the #RRGGBB format and
# that every group has one, so hand edits get readable messages.


class Group(Model):
    id: str
    name: str
    color: str | None = None
    description: str = ""


class Project(Model):
    id: str
    title: str
    group: str
    from_: str | None = Field(default=None, alias="from")
    links: list[Link] = []
    color: str | None = None
    description: str = ""


class Milestone(Model):
    id: str
    project: str
    title: str
    date: dt.date
    kind: str
    state: str | None = None
    planned: bool = False
    labels: list[str] = []
    merges: list[str] = []
    markers: list[str] = []
    line_text: str = Field(default="", description="Text on the lane line after this milestone (overrides the state's default text).")
    line_text_align: TextAlign = "center"
    line_text_position: TextPosition = "above"
    line_text_size: TextSize = 10
    links: list[Link] = []
    color: str | None = None
    description: str = ""


class Reference(Model):
    id: str
    type: str
    from_: str = Field(alias="from")
    to: str
    color: str | None = None
    text: str = Field(default="", description="Optional text drawn with the line; shown only if set.")
    text_align: TextAlign = "center"
    text_position: TextPosition = "above"
    text_size: TextSize = 10
    text_orientation: TextOrientation = "horizontal"
    description: str = ""


class Kind(Model):
    id: str
    name: str
    shape: Shape
    size: Size = 1.0
    default_state: str | None = None
    color: str | None = None
    description: str = ""


class State(Model):
    id: str
    name: str
    line: Line
    opacity: Opacity = 1.0
    line_width: Width = 2.5
    text: str = Field(default="", description="Default text on every lane line in this state; a milestone's line_text overrides it.")
    text_align: TextAlign = "center"
    text_position: TextPosition = "above"
    text_size: TextSize = 10
    waiting_on: WaitingOn
    color: str | None = None
    description: str = ""


class RefType(Model):
    id: str
    name: str
    directed: bool
    line: Line
    opacity: Opacity = 1.0
    line_width: Width = 1.4
    color: str | None = None
    description: str = ""


class Marker(Model):
    id: str
    name: str
    icon: MarkerIcon
    color: str | None = None
    description: str = ""


class Settings(Model):
    fork_color: str | None = None
    merge_color: str | None = None
    fork_width: Width = 1.8
    merge_width: Width = 1.8


class Workspace(Model):
    settings: Settings = Settings()
    groups: list[Group] = []
    projects: list[Project] = []
    milestones: list[Milestone] = []
    references: list[Reference] = []
    kinds: list[Kind] = []
    states: list[State] = []
    reftypes: list[RefType] = []
    markers: list[Marker] = []


# ---------------------------------------------------------------- create requests


class GroupCreate(Model):
    name: str
    color: str
    description: str = ""


class MilestoneInit(Model):
    """Milestone fields without `project` (used for a project's first milestone)."""

    title: str
    date: dt.date
    kind: str
    state: str | None = None
    planned: bool = False
    labels: list[str] = []
    merges: list[str] = []
    markers: list[str] = []
    line_text: str = Field(default="", description="Text on the lane line after this milestone (overrides the state's default text).")
    line_text_align: TextAlign = "center"
    line_text_position: TextPosition = "above"
    line_text_size: TextSize = 10
    links: list[Link] = []
    color: str | None = None
    description: str = ""


class MilestoneCreate(MilestoneInit):
    project: str


class ProjectCreate(Model):
    title: str
    group: str
    from_: str | None = Field(default=None, alias="from")
    links: list[Link] = []
    color: str | None = None
    description: str = ""
    first_milestone: MilestoneInit


class ReferenceCreate(Model):
    type: str
    from_: str = Field(alias="from")
    to: str
    color: str | None = None
    text: str = Field(default="", description="Optional text drawn with the line; shown only if set.")
    text_align: TextAlign = "center"
    text_position: TextPosition = "above"
    text_size: TextSize = 10
    text_orientation: TextOrientation = "horizontal"
    description: str = ""


class KindCreate(Model):
    name: str
    shape: Shape
    size: Size = 1.0
    default_state: str | None = None
    color: str | None = None
    description: str = ""


class StateCreate(Model):
    name: str
    line: Line
    opacity: Opacity = 1.0
    line_width: Width = 2.5
    text: str = Field(default="", description="Optional text drawn with the line; shown only if set.")
    text_align: TextAlign = "center"
    text_position: TextPosition = "above"
    text_size: TextSize = 10
    waiting_on: WaitingOn
    color: str | None = None
    description: str = ""


class RefTypeCreate(Model):
    name: str
    directed: bool
    line: Line
    opacity: Opacity = 1.0
    line_width: Width = 1.4
    color: str | None = None
    description: str = ""


class MarkerCreate(Model):
    name: str
    icon: MarkerIcon
    color: str | None = None
    description: str = ""


# ---------------------------------------------------------------- patch requests
# Only the fields that are sent are changed; null sets a field to null.


class GroupPatch(Model):
    name: str | None = None
    color: str | None = None
    description: str | None = None
    position: int | None = Field(
        default=None, description="Move the group to this index in the group order."
    )


class ProjectPatch(Model):
    title: str | None = None
    group: str | None = None
    from_: str | None = Field(default=None, alias="from")
    links: list[Link] | None = None
    color: str | None = None
    description: str | None = None
    position: int | None = Field(
        default=None,
        description="Move the project to this index in the project list (the manual lane order).",
    )


class MilestonePatch(Model):
    title: str | None = None
    date: dt.date | None = None
    kind: str | None = None
    state: str | None = None
    planned: bool | None = None
    labels: list[str] | None = None
    merges: list[str] | None = None
    markers: list[str] | None = None
    line_text: str | None = None
    line_text_align: TextAlign | None = None
    line_text_position: TextPosition | None = None
    line_text_size: TextSize | None = None
    links: list[Link] | None = None
    color: str | None = None
    description: str | None = None


class ReferencePatch(Model):
    type: str | None = None
    from_: str | None = Field(default=None, alias="from")
    to: str | None = None
    color: str | None = None
    text: str | None = None
    text_align: TextAlign | None = None
    text_position: TextPosition | None = None
    text_size: TextSize | None = None
    text_orientation: TextOrientation | None = None
    description: str | None = None


class KindPatch(Model):
    name: str | None = None
    shape: Shape | None = None
    size: Size | None = None
    default_state: str | None = None
    color: str | None = None
    description: str | None = None


class StatePatch(Model):
    name: str | None = None
    line: Line | None = None
    opacity: Opacity | None = None
    line_width: Width | None = None
    text: str | None = None
    text_align: TextAlign | None = None
    text_position: TextPosition | None = None
    text_size: TextSize | None = None
    waiting_on: WaitingOn | None = None
    color: str | None = None
    description: str | None = None


class RefTypePatch(Model):
    name: str | None = None
    directed: bool | None = None
    line: Line | None = None
    opacity: Opacity | None = None
    line_width: Width | None = None
    color: str | None = None
    description: str | None = None


class MarkerPatch(Model):
    name: str | None = None
    icon: MarkerIcon | None = None
    color: str | None = None
    description: str | None = None


class SettingsPatch(Model):
    fork_color: str | None = None
    merge_color: str | None = None
    fork_width: Width | None = None
    merge_width: Width | None = None


# ---------------------------------------------------------------- responses


class ProjectDerived(Model):
    milestones: list[str] = Field(description="Milestone ids in project order.")
    head: str | None = Field(description="Latest non-planned milestone.")
    current_state: str | None
    merged: bool


class Derived(Model):
    projects: dict[str, ProjectDerived]
    parents: dict[str, list[str]] = Field(
        description="Parents of each milestone: previous in project (or fork origin), then merge sources."
    )


class WorkspaceOut(Workspace):
    derived: Derived


class ErrorOut(Model):
    errors: list[str]


class EntityRef(Model):
    type: str
    id: str


class Blocker(Model):
    type: str
    id: str
    reason: str


class BlockedOut(Model):
    blockers: list[Blocker]


class DryRunOut(Model):
    removes: list[EntityRef]
    blockers: list[Blocker]
