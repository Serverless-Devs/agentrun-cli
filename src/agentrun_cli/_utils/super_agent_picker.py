"""Interactive picker for ModelService / model selection.

Used by ``ar sa run`` when the user hasn't supplied both ``--model-service``
and ``--model`` and is on an interactive TTY.

When stdin is not a TTY (e.g. piped / CI), non-interactive resolution is
required; missing flags raise ``PickerInputError``.

The interactive UI uses ``questionary`` for arrow-key navigation with a
fixed page size of 10. On pages beyond the first, ``▼ Next page`` /
``▲ Previous page`` sentinels are appended; a ``🔍 Search all…`` sentinel
always appears when there are multiple pages, dropping the user into a
fuzzy autocomplete over the full list.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, List, Optional, Tuple

import click

PAGE_SIZE = 10

_SENTINEL_NEXT = object()
_SENTINEL_PREV = object()
_SENTINEL_SEARCH = object()


class PickerInputError(Exception):
    """Raised when model resolution is impossible (no TTY + missing flags)."""


def _default_services_loader(cfg):
    """Fetch ModelService list via SDK (sync)."""
    from agentrun.model import ModelService, ModelType

    return ModelService.list_all(model_type=ModelType.LLM, config=cfg)


def _default_selector(title: str, choices: List[Tuple[str, Any]]) -> Any:
    """Arrow-key selector with page-size 10 and fuzzy search.

    ``choices`` is a list of ``(label, value)`` tuples. Returns the chosen
    value, or raises ``PickerInputError`` if the user cancels (Esc / Ctrl-C).
    """
    import questionary

    if not choices:
        raise PickerInputError("No choices to select from.")

    total = len(choices)
    if total <= PAGE_SIZE:
        answer = questionary.select(
            title,
            choices=[
                questionary.Choice(label, value=value)
                for label, value in choices
            ],
        ).ask()
        if answer is None:
            raise PickerInputError("Selection cancelled.")
        return answer

    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    page = 0
    while True:
        start = page * PAGE_SIZE
        end = min(start + PAGE_SIZE, total)
        page_choices = [
            questionary.Choice(label, value=value)
            for label, value in choices[start:end]
        ]
        extras: list = []
        if page + 1 < total_pages:
            extras.append(questionary.Choice(
                f"▼ Next page ({page + 2}/{total_pages})",
                value=_SENTINEL_NEXT,
            ))
        if page > 0:
            extras.append(questionary.Choice(
                f"▲ Previous page ({page}/{total_pages})",
                value=_SENTINEL_PREV,
            ))
        extras.append(questionary.Choice(
            "🔍 Search all…", value=_SENTINEL_SEARCH,
        ))

        answer = questionary.select(
            f"{title}  [{page + 1}/{total_pages}]",
            choices=page_choices + extras,
        ).ask()
        if answer is None:
            raise PickerInputError("Selection cancelled.")
        if answer is _SENTINEL_NEXT:
            page += 1
            continue
        if answer is _SENTINEL_PREV:
            page -= 1
            continue
        if answer is _SENTINEL_SEARCH:
            picked = _fuzzy_pick_all(title, choices)
            if picked is _SENTINEL_PREV:
                continue
            return picked
        return answer


def _fuzzy_pick_all(title: str, choices: List[Tuple[str, Any]]) -> Any:
    """Fuzzy-autocomplete over the full list; Esc returns a sentinel."""
    import questionary

    labels = [label for label, _ in choices]
    label_to_value = {label: value for label, value in choices}
    typed = questionary.autocomplete(
        f"{title} (type to filter, Enter to select, Esc to cancel)",
        choices=labels,
        match_middle=True,
        ignore_case=True,
    ).ask()
    if typed is None or typed not in label_to_value:
        if typed and typed not in label_to_value:
            click.echo(f"No exact match for {typed!r}; showing list.", err=True)
        return _SENTINEL_PREV
    return label_to_value[typed]


def _get_svc_name(svc) -> str:
    return str(
        getattr(svc, "model_service_name", None) or getattr(svc, "name", "") or ""
    )


def _get_model_names(svc) -> list:
    ps = getattr(svc, "provider_settings", None)
    if ps is None:
        return []
    names = getattr(ps, "model_names", None)
    return list(names or [])


def _svc_choices(services: Iterable) -> List[Tuple[str, Any]]:
    out: List[Tuple[str, Any]] = []
    for svc in services:
        provider = getattr(svc, "provider", "")
        label = f"{_get_svc_name(svc)}  (provider: {provider})"
        out.append((label, svc))
    return out


def _model_choices(model_names: Iterable[str]) -> List[Tuple[str, Any]]:
    return [(name, name) for name in model_names]


def resolve_model(
    *,
    cli_service: Optional[str],
    cli_model: Optional[str],
    is_tty: bool,
    services_loader: Optional[Callable] = None,
    cfg=None,
    selector: Optional[Callable[[str, List[Tuple[str, Any]]], Any]] = None,
) -> Tuple[str, str]:
    """Resolve (model_service_name, model_name) from CLI flags + interactive prompt.

    Priority:
      1. Both flags given → use as-is, no lookup.
      2. Non-TTY & any missing → raise PickerInputError.
      3. TTY → fetch ModelService list, prompt user via ``selector``.
    """
    if cli_service and cli_model:
        return cli_service, cli_model

    if not is_tty:
        raise PickerInputError(
            "--model-service and --model are required when stdin is not a TTY."
        )

    loader = services_loader or _default_services_loader
    services = list(loader(cfg) or [])
    if not services:
        raise PickerInputError(
            "No model services found. Run `ar model create ...` first."
        )

    pick = selector or _default_selector

    # ── pick service ──
    if cli_service:
        matched = [s for s in services if _get_svc_name(s) == cli_service]
        if not matched:
            raise PickerInputError(
                f"Model service {cli_service!r} not found."
            )
        chosen_service = matched[0]
    elif len(services) == 1:
        chosen_service = services[0]
        click.echo(
            f"Using only available model service: "
            f"{_get_svc_name(chosen_service)}"
        )
    else:
        chosen_service = pick("Select model service", _svc_choices(services))

    # ── pick model ──
    model_names = _get_model_names(chosen_service)
    if not model_names:
        raise PickerInputError(
            f"Model service {_get_svc_name(chosen_service)!r} exposes no models."
        )

    if cli_model:
        if cli_model not in model_names:
            raise PickerInputError(
                f"Model {cli_model!r} not exposed by service "
                f"{_get_svc_name(chosen_service)!r}."
            )
        chosen_model = cli_model
    elif len(model_names) == 1:
        chosen_model = model_names[0]
        click.echo(f"Using only available model: {chosen_model}")
    else:
        chosen_model = pick(
            f"Select model from {_get_svc_name(chosen_service)}",
            _model_choices(model_names),
        )

    return _get_svc_name(chosen_service), chosen_model
