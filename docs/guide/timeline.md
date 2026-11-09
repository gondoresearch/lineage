# The timeline

The timeline is the main view: one horizontal **lane** per project, grouped by group (and domain), with time running left to right.

## Reading it

- **Symbols** are milestones; the shape and size come from the milestone's kind. **Planned** milestones are drawn faded; a planned milestone whose date has passed gets an *overdue* dot. A vertical line marks today.
- **Lane lines** between milestones show the state the project was in: their pattern, colour, thickness and opacity come from the state, and any single line can override them (see [Editing](editing.md#lane-lines)).
- **Forks** are drawn under their origin, starting from the milestone they forked from. **Merges** curve into the milestone that merges them. Their colour and thickness are set in **Settings → Fork and merge lines**.
- **References** are thin lines between milestones of different projects, styled by their reference type; directed types have an arrow.
- **Markers** are small badges on milestones (warning, question, chain, flag…).
- Lines and references can carry **text**, placed above, on or below the line.
- The **legend** lists the kinds, states and reference types in use.

## Moving around

- **Scroll** (or pinch) to zoom, **drag** to pan; **Reset zoom** goes back.
- **Time / Event order** switches the horizontal axis: *Time* places milestones at their dates; *Event order* spaces them evenly in date order, which helps when many happen close together.
- **Hover** a milestone or a project to highlight its ancestors and descendants across forks, merges and references.

## Filters

The filter bar above the views selects **groups** and **states**, and can **hide inactive** projects (those waiting on nobody, or closed). The same filters apply to the timeline, the status board and the dependencies view; **Clear filters** resets them.

## Reordering lanes

Drag a **lane label** up or down to reorder projects. Dropping it into another group moves the project there, together with its forks.

!!! note
    A project cannot be dragged into a group that has no projects yet; use the project's **Edit** form to choose that group.
