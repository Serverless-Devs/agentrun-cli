"""Unit tests for super_agent YAML schema."""

import pytest

from agentrun_cli._utils.super_agent_yaml import (
    ParsedSuperAgent,
    YamlSchemaError,
    parse_yaml_file,
    parse_yaml_text,
)

VALID_MINIMAL = """
apiVersion: agentrun/v1
kind: SuperAgent
metadata:
  name: my-helper
spec:
  prompt: You are helpful
"""

VALID_FULL = """
apiVersion: agentrun/v1
kind: SuperAgent
metadata:
  name: researcher
  description: research helper
spec:
  prompt: deep researcher
  model:
    service: svc-tongyi
    name: qwen-max
  tools:
    - web-search
    - calc
  skills:
    - data-analyzer
  sandboxes: []
  workspaces: []
  subAgents:
    - helper-a
"""

MULTI_DOC = """
apiVersion: agentrun/v1
kind: SuperAgent
metadata:
  name: a
spec:
  prompt: p1
---
apiVersion: agentrun/v1
kind: SuperAgent
metadata:
  name: b
spec:
  prompt: p2
"""

INVALID_KIND = """
apiVersion: agentrun/v1
kind: OtherKind
metadata:
  name: x
spec:
  prompt: y
"""

INVALID_VERSION = """
apiVersion: agentrun/v99
kind: SuperAgent
metadata:
  name: x
spec:
  prompt: y
"""

MISSING_NAME = """
apiVersion: agentrun/v1
kind: SuperAgent
spec:
  prompt: y
"""

METADATA_NOT_MAPPING = """
apiVersion: agentrun/v1
kind: SuperAgent
metadata: "not a mapping"
spec:
  prompt: y
"""

SPEC_NOT_MAPPING = """
apiVersion: agentrun/v1
kind: SuperAgent
metadata:
  name: x
spec: "not a mapping"
"""

TOOLS_NOT_LIST = """
apiVersion: agentrun/v1
kind: SuperAgent
metadata:
  name: x
spec:
  tools: not-a-list
"""

MODEL_NOT_MAPPING = """
apiVersion: agentrun/v1
kind: SuperAgent
metadata:
  name: x
spec:
  model: not-a-mapping
"""


class TestParseMinimal:
    def test_minimal(self):
        docs = parse_yaml_text(VALID_MINIMAL)
        assert len(docs) == 1
        p = docs[0]
        assert isinstance(p, ParsedSuperAgent)
        assert p.name == "my-helper"
        assert p.prompt == "You are helpful"
        assert p.model_service_name is None
        assert p.model_name is None
        assert p.tools == []
        assert p.description is None

    def test_full(self):
        docs = parse_yaml_text(VALID_FULL)
        p = docs[0]
        assert p.name == "researcher"
        assert p.description == "research helper"
        assert p.model_service_name == "svc-tongyi"
        assert p.model_name == "qwen-max"
        assert p.tools == ["web-search", "calc"]
        assert p.skills == ["data-analyzer"]
        assert p.sub_agents == ["helper-a"]


class TestParseMultiDoc:
    def test_two_docs(self):
        docs = parse_yaml_text(MULTI_DOC)
        assert len(docs) == 2
        assert [d.name for d in docs] == ["a", "b"]


class TestInvalid:
    def test_invalid_kind(self):
        with pytest.raises(YamlSchemaError) as e:
            parse_yaml_text(INVALID_KIND)
        assert "kind" in str(e.value).lower()

    def test_invalid_api_version(self):
        with pytest.raises(YamlSchemaError) as e:
            parse_yaml_text(INVALID_VERSION)
        assert "apiversion" in str(e.value).lower() or "v1" in str(e.value)

    def test_missing_name(self):
        with pytest.raises(YamlSchemaError) as e:
            parse_yaml_text(MISSING_NAME)
        assert "name" in str(e.value).lower()

    def test_empty_doc(self):
        with pytest.raises(YamlSchemaError):
            parse_yaml_text("\n\n")

    def test_metadata_not_mapping(self):
        with pytest.raises(YamlSchemaError):
            parse_yaml_text(METADATA_NOT_MAPPING)

    def test_spec_not_mapping(self):
        with pytest.raises(YamlSchemaError):
            parse_yaml_text(SPEC_NOT_MAPPING)

    def test_tools_not_list(self):
        with pytest.raises(YamlSchemaError):
            parse_yaml_text(TOOLS_NOT_LIST)

    def test_model_not_mapping(self):
        with pytest.raises(YamlSchemaError):
            parse_yaml_text(MODEL_NOT_MAPPING)

    def test_bad_yaml(self):
        with pytest.raises(YamlSchemaError):
            parse_yaml_text("foo: [\n  unclosed")

    def test_non_mapping_top_level(self):
        with pytest.raises(YamlSchemaError):
            parse_yaml_text("- just\n- a\n- list\n")


class TestParseFile:
    def test_parse_file(self, tmp_path):
        f = tmp_path / "a.yaml"
        f.write_text(VALID_MINIMAL)
        docs = parse_yaml_file(str(f))
        assert len(docs) == 1
        assert docs[0].name == "my-helper"
