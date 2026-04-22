# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

AgentRun CLI (`ar` / `agentrun`) — a Click-based command-line tool for managing AI agent infrastructure on the AgentRun platform. It wraps the `agentrun` Python SDK (installed as `agentrun-inner-test[core]`) to provide CRUD operations for model services and proxies.

## Commands

```bash
# Setup
make dev                  # Create venv + install editable with dev deps
make install              # Install without dev deps

# Development
make lint                 # Run ruff linter
make test                 # Run all tests
.venv/bin/pytest tests/test_cli_basic.py -v              # Run a single test file
.venv/bin/pytest tests/test_cli_basic.py::TestConfigCommands::test_set_and_get -v  # Single test

# Build standalone binary
make build                # Nuitka --onefile binary → dist/agentrun (warm-start cache: ~/.agentrun/cache/)
make build-all            # macOS + Linux (via Docker)
```

## Architecture

**Source layout:** `src/agentrun_cli/` with setuptools `find` packages.

**Entry point:** `main.py` defines the root `cli` Click group. Global options (`--profile`, `--region`, `--output`, `--debug`) are captured in `ctx.obj` and flow to all subcommands.

**Command pattern:** Each command module (e.g. `commands/model_cmd.py`) does the following:
1. Lazily imports SDK classes inside the command function (not at module top) to keep `ar --help` fast and avoid import errors when the SDK isn't configured.
2. Calls `build_sdk_config()` to construct an SDK `Config` from CLI flags → env vars → `~/.agentrun/config.json` profile (in priority order).
3. Calls the SDK, serializes the result with a `_serialize_*` helper, then passes it to `format_output()`.

**Config system** (`_utils/config.py`): Multi-profile JSON config at `~/.agentrun/config.json`. Credentials resolve as: CLI flags (`--region`) > profile values > env vars (`AGENTRUN_*` > `ALIBABA_CLOUD_*` / `FC_*`).

**Output** (`_utils/output.py`): Four modes — `json` (default), `table` (requires `rich`), `yaml`, `quiet` (prints only the primary identifier). All commands use `format_output(ctx, data)`.

**Error handling** (`_utils/error.py`): The `@handle_errors` decorator catches SDK exceptions by class name pattern (no hard import) and maps them to deterministic exit codes (0=success, 1=not found, 2=bad input, 3=auth, 4=server). Errors go to stderr as JSON.

## Testing

Tests use `click.testing.CliRunner` and `unittest.mock.patch` to swap `CONFIG_FILE`/`CONFIG_DIR` with `tmp_path` fixtures, so no real `~/.agentrun/` is touched. Model commands that hit the SDK are not tested in the basic suite — they require credentials.

### Coverage Requirement

Every code change must maintain **incremental test coverage >= 95%**. A Claude Code hook (`.claude/settings.json`) automatically runs `pytest --cov=agentrun_cli --cov-fail-under=95` after edits to `src/` files. If coverage drops below the threshold, the hook will report failure — add or update tests before proceeding.

## Adding a New Command Group

1. Create `src/agentrun_cli/commands/<resource>_cmd.py` with a `@click.group` and CRUD subcommands.
2. Use lazy SDK imports inside each command function.
3. Apply `@handle_errors` to each command.
4. Use `format_output(ctx, data, quiet_field="<name_field>")` for output.
5. Register the group in `main.py` via `cli.add_command(...)`.
6. **Add integration tests** — see below.

## Integration Test Requirement

Every time a CLI command is added or modified, you **must** add or update integration tests in `tests/integration/` that cover **all** changed or new CLI subcommands. Integration tests validate the full invocation path from the top-level `cli` entry point (`ar <group> <command> ...`) through to the mocked SDK layer.

Rules:
- Use `CliRunner` with the top-level `cli` (from `agentrun_cli.main`) — not the subgroup directly.
- Mock SDK clients/models via `unittest.mock.patch`; never make real API calls.
- Cover every subcommand that was added or modified, including both success and error paths.
- Follow the existing pattern in `tests/integration/test_sandbox_cmd.py` for helper setup and assertions.
- Integration tests are part of the 95% coverage requirement — `make test` runs both unit and integration suites.

## Documentation Requirement

User-facing documentation lives in two places. Every command change must keep both in sync.

**Layout:**

```
README.md            # English, root (GitHub default view)
README_zh.md         # 简体中文, root
docs/
├── en/
│   ├── index.md     # install / auth / global options / output / exit codes / group nav
│   ├── config.md    # one file per command group
│   ├── model.md
│   ├── sandbox.md
│   ├── skill.md
│   ├── super-agent.md
│   └── tool.md
└── zh/              # mirror of docs/en/ — same structure, same section order
    └── (同上)
```

**Rules:**

- **Code-change ⇒ docs change.** Whenever you add, remove, rename, or modify an option, argument, default value, or subcommand in `src/agentrun_cli/commands/`, update the matching section in `docs/en/<group>.md` **and** `docs/zh/<group>.md` in the same commit. Option tables are the source of truth for users — they must match `@click.option(...)` definitions exactly.
- **Bilingual parity.** Chinese and English docs mirror each other 1:1 at the section and table level. Any edit to a Chinese page must be reflected in the matching English page, and vice versa. Only the natural-language prose differs; headings, command signatures, option tables, and example commands stay identical.
- **README parity.** Edits to `README.md` that affect Quickstart, Features, or the Command-Groups table must be mirrored in `README_zh.md`. Language switch links at the top (`English | 简体中文`) must resolve to an existing file on both sides.
- **Cross-link integrity.** When adding a new page or renaming an anchor, update the references in `docs/{en,zh}/index.md`, the two READMEs, and any sibling pages. Anchors use GitHub-slug form (`## Sub-group` → `#sub-group`; Chinese headings preserve the Unicode characters, e.g. `## file 子命令组` → `#file-子命令组`).
- **Source of truth = the code.** Never document options that do not exist in the Click definitions. When the design doc (`docs_inner/cli-design-*.md`) and the code disagree, the code wins — update the user-facing docs to match the code, and flag the divergence in your PR description.
- **No partial updates.** A PR that modifies a command without updating both language versions of the user-facing docs is incomplete; reviewers should block it.
