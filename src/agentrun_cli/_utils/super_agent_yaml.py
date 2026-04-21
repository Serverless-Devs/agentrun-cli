"""YAML schema parsing for ``ar sa apply``.

Schema (k8s-style)::

    apiVersion: agentrun/v1
    kind: SuperAgent
    metadata:
      name: <str>
      description: <str>   # optional
    spec:
      prompt: <str>        # optional
      model:
        service: <str>     # optional
        name: <str>        # optional
      tools: [<str>, ...]       # optional
      skills: [<str>, ...]      # optional
      sandboxes: [<str>, ...]   # optional
      workspaces: [<str>, ...]  # optional
      subAgents: [<str>, ...]   # optional → maps to SDK 'agents' field
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import yaml

SUPPORTED_API_VERSION = "agentrun/v1"
SUPPORTED_KIND = "SuperAgent"


class YamlSchemaError(ValueError):
    """Raised when a document fails schema validation."""


@dataclass
class ParsedSuperAgent:
    name: str
    description: Optional[str] = None
    prompt: Optional[str] = None
    model_service_name: Optional[str] = None
    model_name: Optional[str] = None
    tools: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    sandboxes: List[str] = field(default_factory=list)
    workspaces: List[str] = field(default_factory=list)
    sub_agents: List[str] = field(default_factory=list)


def parse_yaml_text(text: str) -> List[ParsedSuperAgent]:
    """Parse multi-doc YAML and validate each document."""
    try:
        raw_docs = list(yaml.safe_load_all(text))
    except yaml.YAMLError as e:
        raise YamlSchemaError(f"Invalid YAML: {e}") from e

    raw_docs = [d for d in raw_docs if d is not None]
    if not raw_docs:
        raise YamlSchemaError("No documents found in YAML input.")

    results: List[ParsedSuperAgent] = []
    for idx, doc in enumerate(raw_docs):
        try:
            results.append(_validate_doc(doc))
        except YamlSchemaError as e:
            raise YamlSchemaError(f"Document #{idx + 1}: {e}") from e
    return results


def parse_yaml_file(path: str) -> List[ParsedSuperAgent]:
    with open(path, "r", encoding="utf-8") as f:
        return parse_yaml_text(f.read())


def _validate_doc(doc) -> ParsedSuperAgent:
    if not isinstance(doc, dict):
        raise YamlSchemaError("Top level must be a mapping.")

    api_version = doc.get("apiVersion")
    if api_version != SUPPORTED_API_VERSION:
        raise YamlSchemaError(
            f"Unsupported apiVersion {api_version!r}; "
            f"expected {SUPPORTED_API_VERSION!r}."
        )

    kind = doc.get("kind")
    if kind != SUPPORTED_KIND:
        raise YamlSchemaError(
            f"Unsupported kind {kind!r}; expected {SUPPORTED_KIND!r}."
        )

    metadata = doc.get("metadata") or {}
    if not isinstance(metadata, dict):
        raise YamlSchemaError("metadata must be a mapping.")
    name = metadata.get("name")
    if not name or not isinstance(name, str):
        raise YamlSchemaError(
            "metadata.name is required and must be a string."
        )
    description = metadata.get("description")

    spec = doc.get("spec") or {}
    if not isinstance(spec, dict):
        raise YamlSchemaError("spec must be a mapping.")

    prompt = spec.get("prompt")
    model_block = spec.get("model") or {}
    if not isinstance(model_block, dict):
        raise YamlSchemaError("spec.model must be a mapping.")

    def _as_list(v, field_name):
        if v is None:
            return []
        if not isinstance(v, list):
            raise YamlSchemaError(f"spec.{field_name} must be a list.")
        return [str(x) for x in v]

    return ParsedSuperAgent(
        name=name,
        description=description,
        prompt=prompt,
        model_service_name=model_block.get("service"),
        model_name=model_block.get("name"),
        tools=_as_list(spec.get("tools"), "tools"),
        skills=_as_list(spec.get("skills"), "skills"),
        sandboxes=_as_list(spec.get("sandboxes"), "sandboxes"),
        workspaces=_as_list(spec.get("workspaces"), "workspaces"),
        sub_agents=_as_list(spec.get("subAgents"), "subAgents"),
    )
