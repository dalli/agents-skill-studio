# Agent Skill Studio — 설계 문서 공통 규약 (Design Doc Convention)

> 이 문서는 `docs/` 아래 모든 설계 문서의 **작성 규약**이다.
> 병렬 작성되는 문서 간에 용어·식별자·구조가 어긋나는 것을 방지하기 위한
> **단일 기준(single source of truth)** 이다. 어떤 문서를 작성하더라도 이 문서를 먼저 읽고 따른다.

---

## 0. 이 규약이 존재하는 이유

설계 문서 5개는 **병렬로** 작성된다. 병렬 작성은 속도 이득을 주지만, 서로 다른 작성자가
같은 개념을 다른 이름으로 부르면 문서 간 모순이 발생하고, 그 모순은 나중에 발견될수록
수정 비용이 기하급수적으로 오른다.

따라서 **용어와 식별자는 이 문서에서 한 번만 확정**하고, 모든 문서가 이를 그대로 사용한다.
어떤 문서도 이 규약에 없는 식별자를 새로 만들지 않는다. 새 식별자가 필요하면 이 문서를
먼저 갱신한다.

---

## 1. 언어 규칙

| 대상 | 언어 | 예시 |
|---|---|---|
| 설명 문장 | **한국어** | "`description` 필드는 스킬의 동작과 사용 시점을 기술한다." |
| 식별자 / 필드명 | 원문 유지 (영문) | `allowed-tools`, `SkillFrontmatter`, `iter-1` |
| 파일 경로 · 명령어 | 원문 유지 | `src-tauri/`, `pnpm tauri build` |
| 코드 블록 | 원문 유지 | `python`, `ts`, `bash` |
| 표 머리글 | 한국어 | `필드` `타입` `필수` `설명` |

**금지 사항**

- 한국어 문장 안에 영어 설명을 섞지 않는다. 영어 용어는 필요한 경우 괄호로 병기한다.
  - Good: `` `metadata` 필드는 문자열 키-값 쌍의 맵이다. (free-form key-value) ``
  - Bad: `` `metadata` 필드는 free-form key-value 맵이다. ``
- `TODO`, `TBD`, `FIXME`, `???`, `작성 예정`, `(placeholder)` 같은 표식을 남기지 않는다.
  정보가 없으면 "이 항목은 §7 리스크에 기재됨" 처럼 **정확한 상호참조**로 대체한다.
- lorem ipsum, 예시 없는 목록 항목("various", "several", "기타")을 쓰지 않는다.

---

## 2. 정규 컴포넌트 식별자

아래 **12개**가 PRD §4의 컴포넌트 목록과 대응한다 (PRD는 `spec-core`·`skill-io`·
`script-analyzer`·`sandbox-runner`·`eval-engine`·`RunAdapter`·`ipc-contract`·
`packager`·`installer`와 Tauri 셸·프론트 계층을 함께 기술하며, 이를
**규칙 소유자(`C2`)** 와 **규칙을 갖지 않는 껍데기(`C1`, `C12`)** 로 나눴다).
**이 이름을 바꾸지 않는다.**

> ⚠ **식별자 충돌 주의.** 이 표의 `C1`–`C12`는 **컴포넌트 ID**이고,
> PRD의 제약 `C1`–`C16`은 **제약 ID**다. 둘은 다른 namespace다.
> 설계 문서에서는 컴포넌트를 `` `C3` `` (백틱), 제약을 **제약 `C3`**
> (백틱 없이 "제약"을 붙여)로 쓴다. 모호하면 "제약"을 명시한다.

| ID | 컴포넌트 | 책임 |
|---|---|---|
| `C1` | **Tauri Shell** | 창 수명주기, 사이드카 감독, 네이티브 다이얼로그, 권한 ACL. 도메인 로직 금지 |
| `C2` | **Python Core** | FastAPI 사이드카. 비즈니스 로직의 단일 소유자 |
| `C3` | **`spec-core`** | 스키마 · 파서 · 검증 규칙 · 진단 생성 (L1) |
| `C4` | **`skill-io`** | 스킬 디렉터리 입출력, 임포트 어댑터, 경로 안전성 검사 |
| `C5` | **`script-analyzer`** | 정적 분석. 스킬 **전체**의 실행 표면 탐지 |
| `C6` | **`sandbox-runner`** | 격리된 스크립트 동적 실행 (opt-in) |
| `C7` | **`eval-engine`** | L3 평가 루프 오케스트레이션 |
| `C8` | **`RunAdapter`** | L3 제공자 어댑터 프로토콜 |
| `C9` | **`ipc-contract`** | Pydantic → JSON Schema → TS 타입 생성, 버전 관리 |
| `C10` | **`packager`** | 재현 가능한 아티팩트 · `manifest.json` |
| `C11` | **`installer`** | 대상 경로 · 우선순위 · 원자적 설치/제거 |
| `C12` | **UI Layer** | React 19 + Vite + CodeMirror 6 프론트엔드 |

> 표기 규칙: 설계 문서에서는 `C3` `spec-core` 처럼 **ID와 이름을 함께** 쓴다.
> PRD를 인용할 때는 `PRD §4.2` 형식으로 절 번호를 직접 cited한다.

---

## 3. 정규 데이터 식별자 (자료)

모든 Pydantic 모델 / 프로토콜의 정규 이름. `02-data-design.md`가 필드까지 정의한다.

### 3.1 스킬 도메인

| 모델 | 설명 |
|---|---|
| `SkillFrontmatter` | `SKILL.md` YAML 프런트매터 파싱 결과 |
| `SkillDocument` | 프런트매터 + 본문 + 경로 |
| `SkillProperties` | 검증 통과 스킬의 정규 속성(불변) |
| `Diagnostic` | 진단 1건 |
| `DiagnosticSeverity` | 열거형: `error` / `warn` / `info` |
| `DiagnosticCode` | 열거형: 진단 코드 (stable) |
| `ValidationProfile` | 열거형: `strict` / `lenient` |
| `Span` | 텍스트 위치 (line/column) |
| `QuickFix` | 빠른 수정제안 |

### 3.2 알려진 확장 레지스트리 (C3)

| 모델 | 설명 |
|---|---|
| `KnownExtension` | 클라이언트 확장 필드 1건 |
| `ExtensionRegistry` | 버전된 확장 필드 테이블 (데이터, 코드 아님) |
| `KeyClassification` | 열거형: `spec` / `client_extension` / `unknown` |

### 3.3 보안 / 분석 (C5)

| 모델 | 설명 |
|---|---|
| `CapabilityReport` | 정적 분석 결과 전체 |
| `CapabilityFinding` | 발견 1건 |
| `CapabilityKind` | 열거형: `body_shell_exec` / `session_persistent_hook` / `tool_preapproval` / `network_egress` / `credential_access` / `fs_escape` / `subprocess_spawn` / `dynamic_eval` / `declared_dependency` |
| `CapabilitySeverity` | 열거형: `info` / `suspicious` / `dangerous` |
| `Interpreter` | 열거형: `python` / `node` / `bash` / `ruby` / `deno` / `bun` / `go` / `unknown` |
| `SandboxProfile` | 격리 정책 (네트워크 · FS · UID · 자원 상한) |
| `SandboxRunResult` | 동적 실행 결과 |

### 3.4 평가 도메인 (C7/C8)

| 모델 | 설명 |
|---|---|
| `EvalSuite` | `evals/evals.json` 루트 |
| `EvalCase` | 테스트 케이스 1건 |
| `ArmName` | 열거형: `with_skill` / `without_skill` / `old_skill` |
| `ArmResult` | 한 arm 실행 결과 |
| `Timing` | `timing.json` (`total_tokens`, `duration_ms`) |
| `Grading` | `grading.json` |
| `AssertionResult` | 단일 assertion 채점 결과 |
| `AssertionVerdict` | 열거형: `pass` / `fail` / `unverifiable` |
| `Feedback` | `feedback.json` (사람 검토) |
| `Benchmark` | `benchmark.json` 집계 |
| `MetricStats` | `{mean, stddev, n}` |
| `BenchmarkDelta` | 두 arm 차이 |
| `AssertionAnalysis` | 4종 패턴 분석 결과 |
| `RunAdapter` | 프로토콜 |
| `AdapterCapabilities` | 어댑터가 보고할 수 있는 지표 (토큰·시간 등) |

### 3.5 패키징 / 설치 (C10/C11)

| 모델 | 설명 |
|---|---|
| `ArtifactManifest` | 아티팩트 매니페스트 (아카이브 **외부**) |
| `FileDigest` | 파일 1개의 해시 |
| `TreeDigest` | 트리 전체 해시 |
| `ResolvedInstallTarget` | 설치 대상 (내부 전용, 절대 경로 보유) |
| `InstallTargetView` | 설치 대상의 wire 안전 표현 (`display_path`) |
| `InstallScope` | 열거형: `project` / `user` |
| `ClientKind` | 열거형: `agents` / `claude` / `cursor` / `copilot` / `codex` / `windsurf` |
| `InstallPlan` | 설치 계획 (dry-run 결과) |
| `InstallOutcome` | 설치 결과 |
| `VisibilityReport` | 설치 후 실제 클라이언트 탐색 재현 결과 |

### 3.6 IPC 계약 (C9)

| 모델 | 설명 |
|---|---|
| `Handshake` | 연결 시 계약 버전 협상 |
| `Envelope[T]` | 요청/응답 봉투 (제네릭) |
| `RpcMethod` | 메서드 열거형 |

---

## 4. 정규 화면 식별자 (UI)

`03-ui-design.md`가 상세히 설계한다. 여기서는 ID와 이름만 확정한다.

| ID | 화면 | 라우트 |
|---|---|---|
| `S1` | 스킬 라이브러리 | `#/library` |
| `S2` | 스킬 편집기 | `#/skill/:name` |
| `S3` | 검증 리포트 | `#/skill/:name/validation` |
| `S4` | 테스트 러너 | `#/skill/:name/evals` |
| `S5` | 평가 리포트 | `#/skill/:name/evals/:iteration` |
| `S6` | 패키징 | `#/skill/:name/package` |
| `S7` | 설치 관리 | `#/installs` |
| `S8` | 임포트 | `#/import` |
| `S9` | 설정 | `#/settings` |

공통 오버레이: `O1` 임포트 다이얼로그, `O2` 패키지 다이얼로그, `O3` 신뢰 게이트,
`O4` 실행 확인 다이얼로그, `O5` Diff 뷰어.

### 4.2 스파이크 식별자

`[04. 개발 계획 §3](./04-development-plan.md#3-단계-0--스파이크)의 조사 과제다.

> ⚠ **`S1`–`S4`는 화면 ID다.** 스파이크에는 `SP-` 접두사를 쓴다.
> "S1이 실패했다"가 화면인지 스파이크인지 **오독되지 않게** 하기 위한 규칙이다.

| ID | 스파이크 | 검증 |
|---|---|---|
| `SP-1` | 샌드박스 실행 가능성 | 격리 탈출 3종 |
| `SP-2` | Tauri 사이드카 + 전송 계층 | 왕복 <10ms, 고아 프로세스 0 |
| `SP-3` | 어댑터 현실 확인 | 격리 + 두 지표 보고 |
| `SP-4` | 에디터 통합 | 한글 위치 정확성 |

---

## 5. 문서 간 상호 참조 규칙

- 각 문서 첫머리에 **문서 지표(문서 목적 · 독자 · 선행/후행 문서)** 를 둔다.
- 상호 참조는 `§` 절 번호로 한다. 예: `자02-data-design.md §3.4`.
- **내용 중복 금지.** 어떤 정의가 두 문서에 있으면 한쪽이 다른 쪽을 링크한다.
  - 허용: 아키텍처 문서가 데이터 모델의 *존재*를 언급하고 링크.
  - 금지: 아키텍처 문서가 `EvalCase` 의 필드 목록을 다시 적는 것.
- **추적성은 `04-development-plan.md`가 단독으로 소유한다.**
  PRD AC ID → 설계 문서 절 → 개발 단계 매트릭스는 그 문서에만 존재한다.
  다른 문서는 "이 AC의 구현 단계는 04 문서를 참조"로 처리한다.

---

## 6. 문서 구조 규약

각 설계 문서는 다음 순서를 따른다.

1. `#` 제목
2. 인용 형식의 목적 · 독자 · 상태 요약 블록
3. `## 1. 개요` (범위와 비범위)
4. 본문 절들
5. `## 검증` — 이 문서가 주장하는 것의 확인 방법
6. `## 열린 이슈` — 미해결 질문 (PRD §9 리스크로 링크)

절 번호는 문서 내에서 연속한다. 하위 절은 `### 3.4` 형식으로 3단계까지만 쓴다.

---

## 7. 문서 간 링크 규칙

상호 링크는 **상대 경로 + 앵커**로 쓴다.

```markdown
자세한 필드 정의는 [데이터 설계 §3.4](./02-data-design.md#7-평가-도메인-모델-c7-eval-engine--c8-runadapter)를 참조한다.
```

앵커는 GitHub 슬러그 규칙을 따른다: 소문자, 공백→하이픈, 특수문자 제거, 한글 유지.

---

## 8. 분량 기준

| 문서 | 최소 분량 | 근거 |
|---|---|---|
| `01-architecture.md` | 700줄 | 12개 컴포넌트 · 프로세스 경계 · IPC · 기술 선정 근거 |
| `02-data-design.md` | 600줄 | 필드 단위 정의가 본문 majority |
| `03-ui-design.md` | 600줄 | 9개 화면 · 토큰 · 컴포넌트 트리 · 상태 모델 |
| `04-development-plan.md` | 400줄 | 단계 · 태스크 · 의존성 · 검증 명령 |

분량은 상한이 아니다. **단, 빈 서술로 줄수를 늘리지 않는다.** 각 줄이 정보여야 한다.
