"""Unit tests for interactive model picker."""

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agentrun_cli._utils import super_agent_picker as picker_mod
from agentrun_cli._utils.super_agent_picker import (
    PAGE_SIZE,
    PickerInputError,
    _default_selector,
    _default_services_loader,
    _fuzzy_pick_all,
    _get_model_names,
    _get_svc_name,
    _model_choices,
    _svc_choices,
    resolve_model,
)


def _svc(name, model_names, provider="tongyi"):
    return SimpleNamespace(
        model_service_name=name,
        provider=provider,
        provider_settings=SimpleNamespace(model_names=model_names),
    )


class TestResolveModelNonInteractive:

    def test_both_flags_given(self):
        service, model = resolve_model(
            cli_service="svc-a", cli_model="m-a",
            is_tty=False, services_loader=None, cfg=None,
        )
        assert service == "svc-a"
        assert model == "m-a"

    def test_non_tty_missing_flags_raises(self):
        with pytest.raises(PickerInputError):
            resolve_model(
                cli_service=None, cli_model=None,
                is_tty=False, services_loader=None, cfg=None,
            )

    def test_non_tty_missing_model_raises(self):
        with pytest.raises(PickerInputError):
            resolve_model(
                cli_service="svc-a", cli_model=None,
                is_tty=False, services_loader=None, cfg=None,
            )


class TestResolveModelInteractive:

    def test_single_service_single_model_auto_pick(self):
        loader = MagicMock(return_value=[_svc("only-svc", ["only-model"])])
        service, model = resolve_model(
            cli_service=None, cli_model=None,
            is_tty=True, services_loader=loader, cfg=None,
            selector=MagicMock(),
        )
        assert service == "only-svc"
        assert model == "only-model"

    def test_multiple_services_prompt(self):
        svc_a = _svc("svc-a", ["m-a1", "m-a2"])
        svc_b = _svc("svc-b", ["m-b1"])
        loader = MagicMock(return_value=[svc_a, svc_b])

        # First call: pick svc-b. Second call: not invoked (svc-b has 1 model).
        selector = MagicMock(side_effect=[svc_b])
        service, model = resolve_model(
            cli_service=None, cli_model=None,
            is_tty=True, services_loader=loader, cfg=None,
            selector=selector,
        )
        assert service == "svc-b"
        assert model == "m-b1"

    def test_multiple_models_prompt(self):
        svc_a = _svc("svc-a", ["m-a1", "m-a2", "m-a3"])
        loader = MagicMock(return_value=[svc_a])
        selector = MagicMock(return_value="m-a2")
        service, model = resolve_model(
            cli_service=None, cli_model=None,
            is_tty=True, services_loader=loader, cfg=None,
            selector=selector,
        )
        assert service == "svc-a"
        assert model == "m-a2"
        # Only model picker invoked (1 service auto-picks).
        assert selector.call_count == 1
        title, choices = selector.call_args.args
        assert "svc-a" in title
        assert [label for label, _ in choices] == ["m-a1", "m-a2", "m-a3"]

    def test_service_selector_receives_service_choices(self):
        svc_a = _svc("svc-a", ["m-a1", "m-a2"])
        svc_b = _svc("svc-b", ["m-b1", "m-b2"])
        loader = MagicMock(return_value=[svc_a, svc_b])
        selector = MagicMock(side_effect=[svc_a, "m-a1"])
        resolve_model(
            cli_service=None, cli_model=None,
            is_tty=True, services_loader=loader, cfg=None,
            selector=selector,
        )
        first_title, first_choices = selector.call_args_list[0].args
        assert "service" in first_title.lower()
        assert any("provider: tongyi" in label for label, _ in first_choices)

    def test_empty_list_raises(self):
        loader = MagicMock(return_value=[])
        with pytest.raises(PickerInputError) as exc:
            resolve_model(
                cli_service=None, cli_model=None,
                is_tty=True, services_loader=loader, cfg=None,
                selector=MagicMock(),
            )
        assert "ar model" in str(exc.value)

    def test_service_given_but_not_found(self):
        loader = MagicMock(return_value=[_svc("svc-a", ["m-a"])])
        with pytest.raises(PickerInputError) as exc:
            resolve_model(
                cli_service="svc-other", cli_model=None,
                is_tty=True, services_loader=loader, cfg=None,
                selector=MagicMock(),
            )
        assert "not found" in str(exc.value)

    def test_service_has_no_models(self):
        loader = MagicMock(return_value=[_svc("svc-a", [])])
        with pytest.raises(PickerInputError) as exc:
            resolve_model(
                cli_service=None, cli_model=None,
                is_tty=True, services_loader=loader, cfg=None,
                selector=MagicMock(),
            )
        assert "no models" in str(exc.value).lower()

    def test_partial_service_only_prompts_for_model(self):
        """cli_service given, cli_model missing → look up svc, then prompt."""
        loader = MagicMock(return_value=[_svc("svc-a", ["m-a1", "m-a2"])])
        selector = MagicMock(return_value="m-a2")
        service, model = resolve_model(
            cli_service="svc-a", cli_model=None,
            is_tty=True, services_loader=loader, cfg=None,
            selector=selector,
        )
        assert service == "svc-a"
        assert model == "m-a2"

    def test_cli_model_in_service_no_prompt(self):
        """If cli_model is valid for looked-up service, use directly."""
        loader = MagicMock(return_value=[_svc("svc-a", ["m-a1", "m-a2"])])
        selector = MagicMock()
        service, model = resolve_model(
            cli_service=None, cli_model="m-a2",
            is_tty=True, services_loader=loader,
            cfg=None, selector=selector,
        )
        assert service == "svc-a"
        assert model == "m-a2"
        # Single service auto-picked; cli_model validated directly.
        selector.assert_not_called()

    def test_cli_model_not_in_service_raises(self):
        loader = MagicMock(return_value=[_svc("svc-a", ["m-a1"])])
        with pytest.raises(PickerInputError) as exc:
            resolve_model(
                cli_service=None, cli_model="nope",
                is_tty=True, services_loader=loader,
                cfg=None, selector=MagicMock(),
            )
        assert "nope" in str(exc.value)


class TestInternalHelpers:

    def test_get_svc_name_from_model_service_name(self):
        svc = SimpleNamespace(model_service_name="svc-a")
        assert _get_svc_name(svc) == "svc-a"

    def test_get_svc_name_from_name(self):
        svc = SimpleNamespace(name="svc-b")
        assert _get_svc_name(svc) == "svc-b"

    def test_get_model_names_no_provider_settings(self):
        svc = SimpleNamespace()
        assert _get_model_names(svc) == []

    def test_get_model_names_none_list(self):
        svc = SimpleNamespace(
            provider_settings=SimpleNamespace(model_names=None),
        )
        assert _get_model_names(svc) == []

    def test_get_model_names_returns_list(self):
        svc = SimpleNamespace(
            provider_settings=SimpleNamespace(model_names=["a", "b"]),
        )
        assert _get_model_names(svc) == ["a", "b"]

    def test_svc_choices_label_contains_provider(self):
        svc_a = _svc("svc-a", ["m1"], provider="dashscope")
        out = _svc_choices([svc_a])
        assert len(out) == 1
        label, value = out[0]
        assert "svc-a" in label
        assert "dashscope" in label
        assert value is svc_a

    def test_model_choices(self):
        assert _model_choices(["m1", "m2"]) == [("m1", "m1"), ("m2", "m2")]


class TestDefaultLoader:

    def test_default_loader_calls_sdk(self):
        """_default_services_loader proxies to ModelService.list_all."""
        fake_svc = [MagicMock()]
        fake_model_service = MagicMock()
        fake_model_service.list_all.return_value = fake_svc
        fake_model_type = MagicMock()
        fake_model_type.LLM = "llm-enum"
        with patch.dict(sys.modules, {
            "agentrun.model": SimpleNamespace(
                ModelService=fake_model_service,
                ModelType=fake_model_type,
            ),
        }):
            result = _default_services_loader(cfg="cfg-obj")
        assert result == fake_svc
        fake_model_service.list_all.assert_called_once_with(
            model_type="llm-enum", config="cfg-obj",
        )


class TestDefaultSelector:
    """questionary-backed default selector."""

    def _patch_questionary(self, select_returns=None, autocomplete_returns=None):
        """Return a MagicMock questionary module; queued .ask() results."""
        mod = MagicMock()

        def make_question(return_values):
            q = MagicMock()
            q.ask = MagicMock(side_effect=list(return_values))
            return q

        def select(title, choices):
            return make_question([select_returns.pop(0)])

        def autocomplete(title, choices, **kwargs):
            return make_question([autocomplete_returns.pop(0)])

        if select_returns is not None:
            mod.select = MagicMock(side_effect=select)
        if autocomplete_returns is not None:
            mod.autocomplete = MagicMock(side_effect=autocomplete)
        mod.Choice = lambda label, value: SimpleNamespace(
            label=label, value=value,
        )
        return mod

    def test_empty_choices_raises(self):
        with pytest.raises(PickerInputError):
            _default_selector("t", [])

    def test_single_page_returns_selected_value(self):
        choices = [(f"label-{i}", f"v-{i}") for i in range(5)]
        mod = self._patch_questionary(select_returns=["v-3"])
        with patch.dict(sys.modules, {"questionary": mod}):
            assert _default_selector("Title", choices) == "v-3"
        mod.select.assert_called_once()

    def test_single_page_cancel_raises(self):
        choices = [("a", 1), ("b", 2)]
        mod = self._patch_questionary(select_returns=[None])
        with patch.dict(sys.modules, {"questionary": mod}):
            with pytest.raises(PickerInputError):
                _default_selector("Title", choices)

    def test_paginated_next_then_select(self):
        total = PAGE_SIZE * 2 + 3  # 23 items → 3 pages
        choices = [(f"label-{i}", f"v-{i}") for i in range(total)]
        # first call: pick next sentinel; second: pick v-15
        mod = self._patch_questionary(
            select_returns=[picker_mod._SENTINEL_NEXT, "v-15"],
        )
        with patch.dict(sys.modules, {"questionary": mod}):
            assert _default_selector("T", choices) == "v-15"
        assert mod.select.call_count == 2
        # First call title mentions [1/3]
        first_title = mod.select.call_args_list[0].args[0]
        assert "[1/3]" in first_title

    def test_paginated_prev_navigation(self):
        total = PAGE_SIZE * 2 + 1  # 21 items → 3 pages
        choices = [(f"l-{i}", f"v-{i}") for i in range(total)]
        mod = self._patch_questionary(
            select_returns=[
                picker_mod._SENTINEL_NEXT,   # page 1 → 2
                picker_mod._SENTINEL_PREV,   # page 2 → 1
                "v-0",                        # page 1 pick
            ],
        )
        with patch.dict(sys.modules, {"questionary": mod}):
            assert _default_selector("T", choices) == "v-0"
        assert mod.select.call_count == 3

    def test_paginated_cancel_raises(self):
        total = PAGE_SIZE + 5  # 15 items → 2 pages
        choices = [(f"l-{i}", i) for i in range(total)]
        mod = self._patch_questionary(select_returns=[None])
        with patch.dict(sys.modules, {"questionary": mod}):
            with pytest.raises(PickerInputError):
                _default_selector("T", choices)

    def test_paginated_search_hit_returns_value(self):
        total = PAGE_SIZE + 2  # 12 items → 2 pages
        choices = [(f"l-{i}", f"v-{i}") for i in range(total)]
        mod = self._patch_questionary(
            select_returns=[picker_mod._SENTINEL_SEARCH],
            autocomplete_returns=["l-7"],
        )
        with patch.dict(sys.modules, {"questionary": mod}):
            assert _default_selector("T", choices) == "v-7"

    def test_paginated_search_miss_returns_to_list(self):
        total = PAGE_SIZE + 2
        choices = [(f"l-{i}", f"v-{i}") for i in range(total)]
        mod = self._patch_questionary(
            select_returns=[picker_mod._SENTINEL_SEARCH, "v-0"],
            autocomplete_returns=["not-in-list"],
        )
        with patch.dict(sys.modules, {"questionary": mod}):
            assert _default_selector("T", choices) == "v-0"

    def test_paginated_search_cancel_returns_to_list(self):
        total = PAGE_SIZE + 2
        choices = [(f"l-{i}", f"v-{i}") for i in range(total)]
        mod = self._patch_questionary(
            select_returns=[picker_mod._SENTINEL_SEARCH, "v-1"],
            autocomplete_returns=[None],
        )
        with patch.dict(sys.modules, {"questionary": mod}):
            assert _default_selector("T", choices) == "v-1"


class TestFuzzyPickAll:

    def test_fuzzy_hit(self):
        mod = MagicMock()
        q = MagicMock()
        q.ask = MagicMock(return_value="label-2")
        mod.autocomplete = MagicMock(return_value=q)
        with patch.dict(sys.modules, {"questionary": mod}):
            out = _fuzzy_pick_all(
                "T", [("label-1", 1), ("label-2", 2), ("label-3", 3)],
            )
        assert out == 2

    def test_fuzzy_cancel(self):
        mod = MagicMock()
        q = MagicMock()
        q.ask = MagicMock(return_value=None)
        mod.autocomplete = MagicMock(return_value=q)
        with patch.dict(sys.modules, {"questionary": mod}):
            out = _fuzzy_pick_all("T", [("l", 1)])
        assert out is picker_mod._SENTINEL_PREV
