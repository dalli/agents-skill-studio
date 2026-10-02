# 02. 데이터 설계

> **목적** — 모든 데이터 모델의 필드 단위 정의를 유일한 진실 공급원으로 제공한다.
> 다른 문서는 모델의 *존재*를 언급하고 링크할 뿐, 필드를 다시 쓰지 않는다.
>
> **독자** — Python 코어(`C2`) 구현자, TypeScript 프론트(`C12`) 구현자, `C9` 계약 관리자.
>
> **선행 문서** — [00. 문서 공통 규약](./00-convention.md), [PRD](./PRD.md)
> **후행 문서** — [01. 아키텍처](./01-architecture.md), [03. UI 디자인](./03-ui-design.md), [04. 개발 계획](./04-development-plan.md)
>
> **상태** — 확정. 이 문서의 제약 번호(`D-n`)는 본 문서 소유다.

---

## 1. 개요

### 1.1 범위

필드 단위 모델 정의, 파서 계약, 레지스트리, 디스크 저장 형식, IPC 계약을 정의한다.
컴포넌트의 배치와 프로세스 경계는 [01. 아키텍처 §3](./01-architecture.md#3-프로세스-아키텍처-c1--c2)가 소유한다.
화면 배치는 [03. UI 디자인](./03-ui-design.md)이 소유한다.

### 1.2 데이터 설계 원칙

| 번호 | 원칙 | 근거 |
|---|---|---|
| **D-1** | **단일 진실 공급원** — 모든 계약 타입은 Pydantic 모델로 정의한다. JSON Schema와 TypeScript 타입은 여기서 **생성되는 파생물**이며 손으로 편집하지 않는다. | `C9`가 세 언어 간 불일치의 근원을 하나로 접는다 |
| **D-2** | **추론 금지** — 모델은 사실을 보관한다. `pass_rate`나 `is_installed` 같은 파생값을 저장하지 않는다. 계산은 소비자가 한다. | 저장된 파생값은 언제든 원본과 어긋난다 |
| **D-3** | **상대 경로 원칙** — 디스크 경로를 모델에 절대 경로로 저장하지 않는다. 스킬 루트 기준 상대 경로만 저장하고, 절대 경로는 해석 시점에 조립한다. | 스킬 디렉터리는 사용자가 이동시킨다. 절대 경로가 저장되면 링크가 깨진다 |
| **D-4** | **경계 검증** — 내부 모델은 wire를 넘어가기 전에 반드시 검증된다. 검증 없는 경로는 존재하지 않는다. | [아키텍처 §5](./01-architecture.md#5-데이터-흐름)에서 정의한 경계를 통과하는 값만 신뢰한다 |
| **D-5** | **폐쇄 집합** — 열거형은 `unknown` 또는 `unverifiable` 같은 탈출구를 가진다. 새 값을 만나도 파싱이 깨지지 않는다. | 클라이언트는 스펙보다 빠르게 진화한다 (제약 `C14`) |
| **D-6** | **안정 식별자** — `DiagnosticCode` 같은 문자열 코드에 UI와 CI가 의존한다. 값 리네임은 schemas 변경이다. | 문자열 리네임은 조용한 break |

### 1.3 저장 계층 전략 — 스튜디오는 자체 데이터베이스를 갖지 않는다

**결정: 디스크가 유일한 영속 계층이다.**

스킬은 본질적으로 디렉터리이고, 스펙은 스킬의 위치 규약을 강제하지 않는다
(PRD §4.4). 사용자 관점에서 스킬의 진실은 그 파일들이다. 스튜디오가 별도 저장소를
두면 다음 문제가 생긴다.

| 문제 | 설명 |
|---|---|
| 진실의 분열 | 스킬을 파일 편집기로 바꿨을 때 스튜디오 DB와 어긋난다. 어느 쪽이 진실인가? |
| 백업·이관 파괴 | 사용자가 스킬을 git으로 관리하는 관행과 충돌한다 |
| 클라이언트 불일치 | 스튜디오만 아는 스킬이 있고, 실제 클라이언트는 못 찾는 상태가 재현 가능 |
| 동기화 부담 | 파일 변경 감지, 충돌 해결, 인덱스 재구축의 모든 복잡도가 발생 |

**대신**: 파생 인덱스는 **캐시**로만 보유하며 언제든 폐기·재구축할 수 있어야 한다.
캐시는 성능을 위한 것이지 정답이 아니다. 캐시 파일에는 버전 스탬프를 넣고,
스탬프가 불일치하면 폐기한다. [01. 아키텍처 §9.2](./01-architecture.md#92-캐시)에서
캐시 위치를 정의한다.

**예외 — 유일하게 저장해야 하는 파생 데이터 없음.** 평가 결과(`grading.json` 등)는
공식 문서 계약상 디스크에 있으므로 예외가 아니다. 그것은 이미 스킬 소유자의
워크스페이스에 존재하는 파일이며, 스튜디오는 그 형식을 그대로 따를 뿐 새로 만들지 않는다.

### 1.4 모델 계열 개요

[규약 §3](./00-convention.md#3-정규-데이터-식별자-자료)이 정한 6개 계열이다.

| 계열 | 소유 컴포넌트 | 절 |
|---|---|---|
| 스킬 도메인 | `C3` `spec-core` | [§3](#3-스킬-도메인-모델-c3-spec-core) |
| 알려진 확장 레지스트리 | `C3` `spec-core` | [§4](#4-알려진-확장-레지스트리-c3-spec-core) |
| 파서 계약 | `C3` `spec-core` | [§5](#5-파서-계약-c3-spec-core) |
| 정적 분석 | `C5` `script-analyzer` | [§6](#6-정적-분석-모델-c5-script-analyzer) |
| 평가 도메인 | `C7` `eval-engine` / `C8` `RunAdapter` | [§7](#7-평가-도메인-모델-c7-eval-engine--c8-runadapter) |
| 패키징·설치 | `C10` `packager` / `C11` `installer` | [§8](#8-패키징--설치-모델-c10-packager--c11-installer) |
| IPC 계약 | `C9` `ipc-contract` | [§9](#9-ipc-계약-c9-ipc-contract) |
| 경로 안전성 | `C4` `skill-io` | [§10](#10-경로-안전성-데이터-c4-skill-io) |

---

### 1.5 임포트 소스 모델 (`C4`)

임포트는 네 종류 소스를 받는다. **어느 소스든 같은 6단계 파이프라인을 지난다**
([§10.1](#101-임포트-파이프라인)) — 소스별 예외가 없어야 우회가 불가능하다.

```python
class ImportSourceKind(StrEnum):
    LOCAL_DIR = "local_dir"
    ARCHIVE = "archive"
    GIT = "git"
    REGISTRY = "registry"


class ImportSource(BaseModel):
    kind: ImportSourceKind
    # kind에 따라 정확히 하나만 채워진다 (판별 유니온).
    local_path: str | None = None          # LOCAL_DIR
    archive_path: str | None = None        # ARCHIVE
    git_url: str | None = None             # GIT
    git_ref: str | None = None
    git_subpath: str | None = None
    registry_slug: str | None = None       # REGISTRY: "owner/slug"
```

**판별 유니온 대신 `kind` + 선택적 필드를 쓴 이유.** 네 소스 모델을
`Field(discriminator="kind")`로 합치면 wire 스키마가 정확해지지만,
`C9`의 TS 생성과 `C12`의 폼 처리가 복잡해진다. v1은 **단일 모델 + 런타임 검증**으로
가 simplicity를 취한다. 네 번째 소스가 추가되면 그때 판별 유니온으로 승격한다.

**네 어댑터의 계약 — 무엇을 내놓는가.**

| 어댑터 | 입력 | 스테이징에 내놓는 것 | 고유 실패 모드 |
|---|---|---|---|
| `LocalDirSource` | 디렉터리 경로 | 디렉터리 복사 | 경로 없음, 권한 없음 |
| `ArchiveSource` | `.tar.gz`/`.zip` | 압축 해제 결과 | **포맷 미지원, 경로 안전성 위반(§10.2)** |
| `GitSource` | URL + ref + subpath | 얕은 복제 결과 | 인증 실패, ref 없음, 빈 저장소 |
| `RegistrySource` | `owner/slug` | API 응답의 파일들 | 404, 스키마 불일치, API 변경 |

**네 어댑터 모두의 공통 출력 — `StagedSkill`.**

```python
class StagedSkill(BaseModel):
    """임포트 파이프라인의 유일한 출력. 이후 단계는 이 형태만 본다."""

    staging_root: str          # 임시 디렉터리 (절대 경로, 내부 전용)
    skill_relpath: str         # SKILL.md가 있는 스테이징 내 상대 경로
    file_count: int
    total_bytes: int
    source: ImportSource
    provenance: list[str]      # 사람이 읽을 출처 표기 (UI 표시용)
```

**`StagedSkill`이 하나뿐인 이유.** 이후 단계(경로 안전성 → 검증 → 분석 →
게이트 → 설치)가 **어느 소스인지 알 필요가 없어야 한다.** 소스별 분기가
여기서 들어오면 "git 경로만 경로 검사를 건너뛴다" 같은 결함이 생긴다.
`source`는 **표시용**으로만 남는다.

**레지스트리 응답 스키마 (참고 — `agentskill.sh` 실측).**

```python
class RegistryInstallResponse(BaseModel):
    """GET /api/agent/skills/{owner%2Fslug}/install 의 응답."""

    skill_md: str
    skill_files: list[RegistryFile] = Field(default_factory=list)
    install_path: str | None = None    # 표기용. 실제로는 쓰지 않는다


class RegistryFile(BaseModel):
    path: str
    content: str
```

**`install_path`를 **사용하지 않는** 이유.** 이 필드는 원격 서버가 제안하는
경로이며, 그 서버의 클라이언트 규약을 따른 것이다. 이를 그대로 따르면
**원격 서버가 클라이언트의 파일 배치를 지배**하게 되어 §9.4의 경로 경계를
무너뜨린다. 표시에만 쓰고 실제 배치는 `C11`이 `ClientKind`로 결정한다.

**레지스트리 스키마가 불일치하면 어떻게 되는가.** `skill_files`의 `path`가
`..`를 포함하거나 절대 경로이면 **검증 없이 즉시 거부**한다(§10.2).
스키마 불일치를 "부분 성공"으로 처리하지 않는다.

## 2. 명명 규칙

### 2.1 두 개의 이름 체계

| 대상 | 규칙 | 예시 |
|---|---|---|
| 파이썬 속성·변수 | `snake_case` | `allowed_tools` |
| YAML·JSON 직렬화 키 | `kebab-case` | `allowed-tools` |

`allowed-tools`(스펙의 실제 키)와 `allowed_tools`(파이썬 관용)는 같은 값이다.
PRD §5는 이를 "실제 버그 원인"으로 지목한다. 이 불일치를 **단일 지점**에서 해결한다.

### 2.2 하이픈↔언더스코어 별칭 규칙

```python
from enum import StrEnum        # stdlib — pydantic에서 오지 않는다
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SkillFrontmatter(BaseModel):
    """SKILL.md YAML 프런트매터의 파싱 결과."""

    model_config = ConfigDict(
        populate_by_name=True,   # 양쪽 이름 모두 허용
        extra="forbid",          # 폐쇄 집합: 알 수 없는 키 거부
    )

    name: str = Field(alias="name")
    description: str = Field(alias="description")
    license: str | None = Field(default=None, alias="license")
    compatibility: str | None = Field(default=None, alias="compatibility")
    metadata: dict[str, str] = Field(default_factory=dict, alias="metadata")
    allowed_tools: str | None = Field(
        default=None,
        alias="allowed-tools",                 # 와이어 키
        serialization_alias="allowed-tools",   # 직렬화 키
    )

    @field_validator("metadata", mode="before")
    @classmethod
    def _coerce_metadata(cls, v: Any) -> dict[str, str]:
        """참조 구현과 동일한 값 강제 변환. §3.3 참조."""
        if not isinstance(v, dict):
            raise ValueError("metadata는 맵이어야 합니다")
        return {str(k): str(x) for k, x in v.items()}
```

> **`StrEnum`은 `pydantic`가 아니라 `enum`에서 온다.** `from pydantic import StrEnum`은
> `ImportError`다. Python 3.11+ 표준 라이브러리다.

> **`mode="before"` 검증기가 필수인 이유 (실측 확인).** `metadata: dict[str, str]`만
> 선언하면 Pydantic v2는 `metadata: {v: 1}`을 **`ValidationError`로 거부**한다.
> 그러나 참조 구현 `skills-ref`는 `{str(k): str(v)}`로 **강제 변환해 통과시킨다**
> (PRD §4.2, 소스 확인). 강제 변환 없이는 **클라이언트가 로드하는 스킬을 우리가
> 거부**하게 되어, 검증기가 잘못된 판단을 내는 최악의 버그가 된다.
> `mode="before"`로 원본 값을 먼저 변환해 넣으면 두 구현이 일치한다.

- `populate_by_name=True` — 파싱 시 `allowed_tools`로도, `allowed-tools`로도 받는다.
- `serialization_alias` — 직렬화 시 항상 `allowed-tools`로 되돌린다.

**임의의 kebab→snake 자동 변환기를 쓰지 않는 이유.** 전역 변환기는 다음을 유발한다.

| 위험 | 예시 |
|---|---|
| 키 충돌 | YAML에 `allowed_tools`와 `allowed-tools`가 **동시에** 있으면 변환 후 하나로 붕괴하고 정보가 사라진다 |
| 모호성 | `some-key`와 `some_key`가 같은 필드로 수렴하여 어느 것이 원본인지 역추적 불가 |
| 오류 은폐 | 사용자의 실제 오타(`allowed-tool`)가 조용히 다른 필드로 매핑될 수 있다 |

대신 **명시적 alias만** 사용하고, **반올림 테스트로 보강**한다
([§3.8](#38-불변식과-검증-규칙), `D-TEST-3`).

### 2.3 `id` 사용 금지

`id`는 도메인마다 의미가 다르다. 전역 규칙 대신 도메인별 명명을 쓴다.

| 도메인 | 식별자 | 이유 |
|---|---|---|
| 평가 케이스 | `EvalCase.id: int` | 공식 문서 계약이 정수 인덱스를 정의한다 (PRD §4.6) |
| IPC 요청 | `Envelope.id: str` | UUID. 클라이언트가 만들어 서버가 되돌려보내야 하므로 분산 생성 |
| 파일 | `FileDigest.path: str` | 경로 자체가 식별자 |
| 진단 | `Diagnostic.code` + `span` | 메시지가 아니라 규칙이 식별자 |

### 2.4 금지 필드

- `object` 타입 금지. 모든 필드는 정밀한 타입을 갖는다.
- 파이썬 `Optional[X]` 대신 `X | None` (PEP 604).
- `dict` bare 사용 금지. `dict[str, str]` 처럼 두 매개변수를 명시한다.

**`Any`의 예외 — 정확히 3군처에서만 허용한다.**

| 허용 위치 | 이유 | 경계 강제 |
|---|---|---|
| 1단계 `RawFrontmatter.fields` | 원본 YAML 값을 **손실 없이** 보존해야 키 분류가 가능 (§3.1) | `classify_keys()`가 소비 후 파기 |
| `ClassifiedFrontmatter.client_extensions` / `.unknown_fields` | 원본 값을 보존해야 "이 값을 옮기면 **어느 클라이언트가** 무시합니다"라는 정확한 안내가 가능 | **규칙 판단에 쓰지 않고 경고 문자열 생성에만** 사용. 값의 구조는 규칙에 들어가지 않는다 |
| `Envelope.params` / `StreamEvent.payload` | 메서드별 구체 타입으로 **검증 후** 하위에 내려보내야 함 (§9.4) | `parse_params()`가 메서드별 모델로 검증. **검증 없이 하위로 내려가는 경로가 없다** (§12.3) |

**`Any`가 넓게 쓰이면 안 되는 이유.** `Any`는 검증을 통과시키지 못한다.
이 규칙의 정확한 형태는 "`Any`는 **경계 직전**에만 존재하고, 경계를 넘은
값은 반드시 구체 타입"이다. 위 표의 "경계 강제" 열이 각 예외의
**유일한 출구**를 명시한다. 경계가 없는 `Any`는 결함이다.

**`RpcError.detail`은 `Any`를 쓰지 않는다.** `dict[str, str]`으로 제한한다 —
오류 상세는 사람이 읽는 문자열 쌍이면 충분하고, 임의 구조를 넣으면
클라이언트가 오류를 검증할 방법이 없어진다.

---

## 3. 스킬 도메인 모델 (`C3` `spec-core`)

### 3.1 `SkillFrontmatter`

> ⚠ **2단계 파싱이 구조적으로 필요하다 (설계 결함, 수정 완료).**
> `extra="forbid"`인 모델에 `context: fork`를 넣으면 Pydantic이 분류
> **이전에** `ValidationError`를 던진다. 그러면 §4.2의
> `CLIENT_EXTENSION` 분류가 **절대 실행되지 않아** AC-1.3a가 구현 불가하다.
> 따라서 파싱은 반드시 **2단계**여야 한다.

```python
class RawFrontmatter(BaseModel):
    """1단계: 스키마 제약 없이 YAML 맵을 그대로 받는다.

    `extra="allow"` **가 아니라** Pydantic 모델로 만들지 않는다. 어떤 설정을
    쓰든 Pydantic은 원본 키를 잃거나 거부한다:

    - `extra="allow"` → 알 수 없는 필드가 통과하긴 하지만, **원본 키 이름이
      보존된다**는 보장이 없고 중첩 구조가 정규화된다.
    - `extra="forbid"` → 즉시 `ValidationError`.
    - `dict[str, Any]` 를 필드로 선언 → 가장 단순하고 손실이 없다.

    아래 구현이 `dict[str, Any]` 경로를 쓴다.
    """

    fields: dict[str, Any]          # 원본 키 → 원본 값 (손실 없음)

    @classmethod
    def from_yaml(cls, raw: str) -> RawFrontmatter: ...


class ClassifiedFrontmatter(BaseModel):
    """2단계 결과를 담은 분류 모델. 스펙 6개 + 나머지.

    `client_extensions`와 `unknown_fields`도 `Any`를 쓴다. 이유는 §2.4의
    예외 ①과 같다: **원본 값을 손실 없이 보존**해야 사용자에게 정확한
    안내("이 값을 `metadata` 아래로 옮기면 Claude Code가 무시합니다")를
    할 수 있다. 이 두 맵은 **규칙 판단에 쓰지 않고 경고 생성에만** 쓴다.
    """

    spec_fields: SkillFrontmatter          # 스펙 필드만 검증된 것
    client_extensions: dict[str, Any]      # 알려진 클라이언트 확장
    unknown_fields: dict[str, Any]         # 진짜 미지의 키
    classifications: dict[str, KeyClassification]
```

**흐름.**

```
YAML 바이트
  └─ 1단계 RawFrontmatter.from_yaml()      ← 스키마 제약 없음. 예외 없음.
       └─ classify_keys(raw, registry)    ← KeyClassification 3분류
            ├─ spec              → 2단계: SkillFrontmatter로 검증 (extra="forbid")
            ├─ client_extension  → spec_fields에 넣지 않고 client_extensions에 보존
            └─ unknown           → unknown_fields에 보존
                 └─→ ClassifiedFrontmatter
```

**`SkillFrontmatter`는 2단계에서만 쓰이며, 그 시점에는 이미 스펙 6개만
남아 있다.** 그래서 `extra="forbid"`가 폐쇄 집합을 지킬 수 있다.

```python
class SkillFrontmatter(BaseModel):
    """SKILL.md YAML 프런트매터의 **스펙 6개 필드만**.

    주의: 이 모델에 클라이언트 확장 필드를 직접 넣지 않는다.
    `ClassifiedFrontmatter`가 1단계에서 분리해 온다(§3.1 두 단계 참조).
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    name: str | None = Field(default=None, alias="name")
    description: str | None = Field(default=None, alias="description")
    license: str | None = Field(default=None, alias="license")
    compatibility: str | None = Field(default=None, alias="compatibility")
    metadata: dict[str, str] = Field(default_factory=dict, alias="metadata")
    allowed_tools: str | None = Field(default=None, alias="allowed-tools")

    @field_validator("metadata", mode="before")
    @classmethod
    def _coerce_metadata(cls, v: Any) -> dict[str, str]:
        """참조 구현과 동일한 값 강제 변환. §3.3 참조."""
        if not isinstance(v, dict):
            raise ValueError("metadata는 맵이어야 합니다")
        return {str(k): str(x) for k, x in v.items()}
```

**왜 이 구조인가.** 1단계에 Pydantic 모델을 쓰면 (`extra="allow"`든
무엇이든) 원본 키가 **잃히거나 거부된다.** 분류는 원본 키를 봐야 한다.
따라서 1단계는 `dict[str, Any]`로 받고, 2단계에서만 스펙 필드를 검증한다.
이러면 "스펙 위반"과 "이식성 문제"와 "오타"가 **모두** 구별 가능해진다.

**`name`과 `description`이 `| None`인 이유.** 두 필드는 스펙상 필수지만,
파서 단계에서 "없음"과 "있으나 타입이 틀림"을 구분해야 한다. 파서가 곧바로
검증하지 않고 구조만 표현한다. 필수성 판정은 [§3.8](#38-불변식과-검증-규칙)의
`validate()`가 담당한다. 이렇게 분리하면 파서 테스트와 검증 테스트의 책임이
분리되어, 파서를 다시 써도 검증 로직은 건드리지 않아진다.

| 필드 | 타입 | 필수(스펙) | 제약 | 설명 |
|---|---|---|---|---|
| `name` | `str \| None` | ✅ | 1–64자, 유니코드 소문자 알파벳·숫자·`-`, 선행/후행 `-` 금지, 연속 `--` 금지, **부모 디렉터리명과 일치** | §3.2 상세 기술 |
| `description` | `str \| None` | ✅ | 1–1024자, 공백 아님 | 스킬이 무엇을 하고 언제 쓰이는지 |
| `license` | `str \| None` | — | 문자열 | 라이선스 이름 또는 번들 파일 참조 |
| `compatibility` | `str \| None` | — | **문자열**, 1–500자 | 환경 요구사항. 숫자·불리언이면 오류 |
| `metadata` | `dict[str, str]` | — | **평면 맵**, 모든 값 `str` | 클라이언트별 부가 데이터. §3.3 |
| `allowed_tools` | `str \| None` | — | 공백 구분 문자열 | 스펙상 **실험적(experimental)** |

### 3.2 `name` 검증 규칙 — 유니코드와 NFKC

이 규칙은 **스펙 산문과 참조 구현이 어긋나는 지점**이므로 정밀하게 기술한다.

```python
import unicodedata

MAX_SKILL_NAME_LENGTH = 64


def normalize_name(raw: str) -> str:
    """이름 비교 전 정규화. NFKC를 사용한다."""
    return unicodedata.normalize("NFKC", raw.strip())


def validate_name(name: str, dir_name: str | None) -> list[Diagnostic]:
    """이름 규칙 검증. 정규화는 호출 전에 수행되어야 한다."""
    norm = normalize_name(name)
    problems: list[Diagnostic] = []

    if not norm:
        problems.append(Diagnostic(code=DiagnosticCode.MISSING_NAME, severity="error"))
        return problems

    if len(norm) > MAX_SKILL_NAME_LENGTH:
        problems.append(Diagnostic(
            code=DiagnosticCode.NAME_TOO_LONG,
            severity="error",
            message=f"스킬 이름이 {MAX_SKILL_NAME_LENGTH}자를 초과합니다 ({len(norm)}자).",
        ))

    if norm != norm.lower():
        problems.append(Diagnostic(code=DiagnosticCode.NAME_CHARSET, severity="error",
                                    message="스킬 이름은 소문자여야 합니다."))

    if norm.startswith("-") or norm.endswith("-"):
        problems.append(Diagnostic(code=DiagnosticCode.NAME_HYPHEN_EDGE, severity="error",
                                    message="하이픈으로 시작하거나 끝날 수 없습니다."))

    if "--" in norm:
        problems.append(Diagnostic(code=DiagnosticCode.NAME_DOUBLE_HYPHEN, severity="error",
                                    message="연속된 하이픈(--)을 포함할 수 없습니다."))

    # isalnum()은 유니코드를 인식한다. 한글 스킬 이름이 유효하다는 뜻이다.
    invalid = [ch for ch in norm if not (ch.isalnum() or ch == "-")]
    if invalid:
        problems.append(Diagnostic(code=DiagnosticCode.NAME_CHARSET, severity="error",
                                    message=f"허용되지 않는 문자: {''.join(sorted(set(invalid)))}"))

    if dir_name is not None and normalize_name(dir_name) != norm:
        problems.append(Diagnostic(code=DiagnosticCode.NAME_DIR_MISMATCH, severity="error",
                                    message=f"디렉터리 이름 '{dir_name}'이(가) 스킬 이름 '{norm}'과(와) 일치해야 합니다."))
    return problems
```

**두 가지 사실이 이 설계의 근거다.**

1. **`isalnum()`은 유니코드를 인식한다.** 즉 `데이터-분석`, `일본어 스킬`,
   `café-naïve`가 **유효하다**. `[a-z0-9-]`를 하드코딩한 검증기는 **틀렸으며**
   한국어 스킬을 거부한다. 스펙 산문은 "lowercase letters, numbers, and hyphens"로
   더 좁게 서술하지만, 참조 구현의 docstring은 *"Skill names support i18n characters
   (Unicode letters) plus hyphens."*라고 명시한다 (PRD §4.2).
2. **비교는 NFKC 정규화 후 수행한다.** 참조 구현이 `unicodedata.normalize("NFKC", ...)`
   를 양쪽에 적용한다 (PRD §4.2 검증 사실). 전각/반각 문자 차이로 인한 오탐을 막는다.

**`spec_ambiguity` 진단.** 이 불일치를 숨기지 않는다. 검증 결과 요약에
`spec_ambiguity` 항목이 포함되고, 메시지는 "스펙 산문은 ASCII만 허용하나 참조
구현과 실제 클라이언트는 유니코드 소문자를 허용합니다. 현재는 참조 구현을 따릅니다."
를 명시한다. 조용히 선택하지 않는 것이 [규약 §1](./00-convention.md#1-언어-규칙)의
금지 사항에 해당한다.

### 3.3 `metadata` — 평면 맵 강제

`metadata`는 `str → str` **평면(flat) 맵**이다. 참조 구현이 `{str(k): str(v) for ...}`
로 값을 강제 문자열 변환한다 (PRD §4.2).

```python
def coerce_metadata(raw: dict[str, object]) -> dict[str, str]:
    """참조 구현과 동일한 강제 변환. 중첩 구조는 문자열로 직렬화된다."""
    return {str(k): str(v) for k, v in raw.items()}
```

| 결정 | 이유 |
|---|---|
| 값 강제 변환을 **재현**한다 | 클라이언트는 `version: 1.0`을 문자열로 읽는다. 우리만 오류를 내면 스킬이 로드되지 않는다 |
| **중첩 맵을 허용하지 않는다** | 스펙이 "map from string keys to string values"라고 명시. 중첩을 허용하면 "portable"가 거짓말이 된다 |
| `metadata` 안에 스펙 필드명을 키로 쓰지 않는다 | Claude Code 문서가 `metadata`에 `paths` 같은 프런트매터 필드명을 키로 재사용하지 말라고 경고한다 (PRD §4.2). 중첩 맵 검사로 일부 감지 가능 |
| 최상위 키는 `extra="forbid"`로 차단 | `version:`을 최상위에 쓰면 `unknown_field`. `metadata.version`이 정답 |

### 3.4 `SkillDocument`

```python
class SkillDocument(BaseModel):
    """파싱된 스킬 파일 1개."""

    frontmatter: SkillFrontmatter
    body: str
    skill_md_relpath: str      # D-3: 스킬 루트 기준 상대 경로
    dir_name: str              # 부모 디렉터리명 (name 검증에 사용)
    raw_text: str = Field(exclude=True)  # 진단 표시용 원문, 직렬화 금지
```

| 필드 | 설명 |
|---|---|
| `raw_text` | 진단 메시지가 원본 문맥을 인용할 때 쓴다. `exclude=True`로 wire에 싣지 않는다 (크기) |
| `skill_md_relpath` | `SKILL.md` 또는 `skill.md`. 어느 것이었는지 기록해 재파싱 불필요 |

### 3.5 `SkillProperties` — 검증 통과 후의 불변 형태

```python
class SkillProperties(BaseModel):
    """strict 검증을 통과한 스킬의 정규 속성. 이후에는 불변."""

    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    license: str | None = None
    compatibility: str | None = None
    allowed_tools: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    description_length: int
    has_client_extensions: bool = False
```

`frozen=True`의 이유: 검증 통과 후에는 아무도 이를 고치지 않아야 한다.
`C4` `skill-io`와 `C11` `installer`가 이 객체를 받아 배치를 결정하며,
중간에 변경되면 검증 결과와 실제 설치물이 어긋난다.

### 3.6 `Span`, `QuickFix`, `Diagnostic`

```python
class LineColumn(BaseModel):
    """진단 위치의 한 좌표. **Pydantic BaseModel** (NamedTuple 아님).

    NamedTuple을 쓰면 JSON Schema에서 필드 이름이 보존되지 않아
    `C9`의 TS 타입 생성이 깨진다. 계약 타입은 반드시 BaseModel이다.
    """

    line: int      # 0-based
    column: int    # 0-based, **UTF-16 코드유닛** 기준 (§3.6.1)
    offset: int    # 절대 UTF-16 오프셋 (JS 문자열 인덱스와 동일)


class Span(BaseModel):
    """진단 위치. 프런트 CM6이 소비한다.

    `None`은 "위치를 모른다"를 뜻한다. 임의로 (0,0)을 넣지 않는다 —
    틀린 위치 표시가 진단보다 해롭다.
    """

    start: LineColumn
    end: LineColumn
```

### 3.6.1 좌표계 규약 — wire에서 UTF-16, 내부에서 코드포인트

**이 규약은 세 곳에서 일관되어야 하며, 이전 판본에서 서로 어긋나 있었다.
최종 규약은 하나다.**

| 층 | 좌표계 | 근거 |
|---|---|---|
| **`C2` 내부 파서·정규식** | **코드포인트** (파이썬 `str` 인덱스) | 파이썬 문자열이 코드포인트다 |
| **wire (`C2` → `C9` → `C12`)** | **UTF-16 코드유닛** | JS 문자열 인덱스와 동일해야 프런트가 그대로 쓸 수 있다 |
| **`C12` CodeMirror 6** | **UTF-16 코드유닛** | CM6 `pos`/`ch`가 JS 문자열 인덱스다 |

**변환은 오직 `C9`의 어댑터가 수행한다.** `C2`의 응답 직렬화 시점에
내부 좌표를 UTF-16으로 바꾼다. `C12`는 **어떤 변환도 하지 않고**
`LineColumn`을 CM6에 그대로 넘긴다.

```
[내부] 코드포인트 offset 42
   │  C9 어댑터: len(text[:42].encode('utf-16-le')) // 2
   ▼
[wire] UTF-16 offset 60      ← C12가 그대로 사용
   │  CM6 dispatch({ pos: 60 })
   ▼
[화면] 정확한 문자 위치
```

**이 규약이 없으면 무엇이 깨지는가.** 한글 한 줄이 코드포인트 기준 30칸이고
UTF-16 기준 60칸이므로, 변환이 빠지면 **해당 줄 이후의 모든 진단이 한 칸씩
밀린다.** 마커 개수 테스트는 통과하므로 **자동 테스트로 잡히지 않는다**
([03. UI 디자인 §13.2 M1](./03-ui-design.md#132-수동-검증-playwright로-어려움)).
스파이크 `SP-4`가 이 규약을 실측 확인하고 `T5-22`가 수동으로 재확인한다.

**`Span`이 `None`인 진단의 처리.** 파싱 실패처럼 위치를 모르면
`(0,0)`을 채우지 **않고** `span=None`을 보낸다. `C12`는 gutter 마커를
그리지 않고 "위치 없음" 그룹에 모은다.
좌표계 규약은 위 §3.6.1에 정의했다. **프런트는 변환하지 않는다.**
[03. UI 디자인 §5.2.2](./03-ui-design.md#522-진단--cm6-decoration-매핑)가 소비 방법이다.

```python
class QuickFix(BaseModel):
    """빠른 수정 제안. 적용 가능 여부를 명시한다."""

    title: str                       # 사용자에게 보여줄 문구 (한국어)
    kind: Literal["replace_span", "insert_field", "move_to_metadata", "none"]
    payload: dict[str, str] = Field(default_factory=dict)
    preserves_cursor: bool = True    # 커서 위치를 보존하는지
```

| `kind` | 의미 | 적용 후 |
|---|---|---|
| `replace_span` | `payload["replacement"]`로 span 교체 | 프런트에서 undo 가능한 편집 |
| `insert_field` | `payload["key"]`, `payload["value"]` 삽입 | 프런트 편집 |
| `move_to_metadata` | 최상위 키를 `metadata` 아래로 이동 | **구조적 편집이므로 별도 확인 필요** |
| `none` | 자동 수정 불가. 우클릭 메뉴에서 수동 안내만 | — |

`move_to_metadata`를 별도 종류로 둔 이유: 이 수정은 스킬의 의미(클라이언트가
키를 해석하는지 여부)를 바꾼다. `context: fork`를 `metadata`로 옮기면 Claude Code의
fork 동작이 사라진다. 따라서 "스펙 준수로 바꾼다"와 "기능을 잃는다"가 동시에
일어나며, 사용자가 인지해야 한다. `QuickFix.title`에 이 상충을 명시한다.

```python
class DiagnosticSeverity(StrEnum):
    ERROR = "error"
    WARN = "warn"
    INFO = "info"


class DiagnosticCode(StrEnum):
    # 파스 실패 4종
    PARSE_NO_OPENING_DELIMITER = "parse_no_opening_delimiter"
    PARSE_UNTERMINATED = "parse_unterminated"
    PARSE_YAML_ERROR = "parse_yaml_error"
    PARSE_NOT_MAPPING = "parse_not_mapping"

    # 필수 및 제약
    MISSING_NAME = "missing_name"
    MISSING_DESCRIPTION = "missing_description"
    DESCRIPTION_EMPTY = "description_empty"
    DESCRIPTION_TOO_LONG = "description_too_long"
    NAME_EMPTY = "name_empty"
    NAME_TOO_LONG = "name_too_long"
    NAME_HYPHEN_EDGE = "name_hyphen_edge"
    NAME_DOUBLE_HYPHEN = "name_double_hyphen"
    NAME_CHARSET = "name_charset"
    NAME_DIR_MISMATCH = "name_dir_mismatch"
    NAME_NOT_LOWERCASE = "name_not_lowercase"
    COMPATIBILITY_TOO_LONG = "compatibility_too_long"
    COMPATIBILITY_NOT_STRING = "compatibility_not_string"

    # 필드 분류
    UNKNOWN_FIELD = "unknown_field"
    CLIENT_EXTENSION_FIELD = "client_extension_field"
    SPEC_AMBIGUITY = "spec_ambiguity"
    TRUNCATION_RISK = "truncation_risk"
    RESERVED_NAME = "reserved_name"

    # 본문 권고 (스펙 밖 — §3.6.2 규칙표 참조)
    BODY_TOO_LONG = "body_too_long"
    BROKEN_RELATIVE_LINK = "broken_relative_link"
    ORPHAN_SCRIPT_REFERENCE = "orphan_script_reference"
    WEAK_DESCRIPTION = "weak_description"
    MISSING_SKILL_MD = "missing_skill_md"
    BODY_EMPTY = "body_empty"

    def severity(self, profile: "ValidationProfile") -> DiagnosticSeverity:
        """프로필별 심각도. C5(단일 엔진 + 맵)의 규칙 구현부."""
        return _SEVERITY_MAP[(self, profile)]
```

#### 3.6.2 본문 권고 규칙 — 스펙 밖 lint (AC-1.8의 규칙 정의)

`T1-10`이 **구현할 정확한 규칙**이다. 스펙 밖이지만 공식 best-practices
가이드가 지적한 실패 모드를 린트로 승격했다. **모두 `strict`/`lenient`에서
같은 심각도**다(프로필 무관).

| `DiagnosticCode` | 발동 조건 | 심각도 | 근거 |
|---|---|---|---|
| `body_too_long` | 본문 > **500줄** | `warn` | 스펙이 "500줄 미만"을 권장 |
| `broken_relative_link` | 본문의 상대 링크가 **디스크에 없음** | `warn` | 스펙: "참조는 한 단계 깊이" |
| `orphan_script_reference` | 본문이 실행 파일처럼 참조하나 `scripts/`에 없음 | `warn` | 경로 오타 또는 의도 누락 |
| `weak_description` | `description`에 트리거 키워드가 없음 | `info` | 공식 *Optimizing descriptions* |
| `body_empty` | 본문이 비어 있음 | `info` | 지시 없이 `SKILL.md`만 존재 |

**`broken_relative_link`가 가장 값이 높은 규칙이다.** 정적으로 100%
판정 가능하고, **실제로 스킬이 깨지는 원인**이며, 사용자가 스킬을 쓰다
처음 겪는 문제다. 판정 규칙을 명시한다.

| 항목 | 규칙 |
|---|---|
| 링크 형태 | 마크다운 링크 형태(대괄호 + 괄호 경로)와 `path/to/file` 두 가지를 **모두** 검사 |
| 기준 경로 | **스킬 루트 기준.** `SKILL.md`가 있는 디렉터리 |
| 깊이 | 1단계만 검사. 중첩 링크는 경고하지 않고 무시 |
| 앵커·URL | `#fragment` , `http://`, `https://`, `mailto:` 는 **검사하지 않는다** |
| 코드펜스 안 | 코드펜스(삼중 역따옴표) 안의 경로는 **검사하지 않는다** (예시일 수 있다) |
| 판정 | 경로가 스킬 루트 밖에 있으면 `broken_relative_link` (`fs_escape` 아님) |

**코드펜스를 검사하지 않는 이유.** 본문의 코드 예시는 흔히 존재하지 않는
경로를 쓴다(`scripts/process.py` 같은 예시). 이들을 누락으로 보고하면
오탐이 폭증하고 사용자는 린터를 끈다.

```python
class Diagnostic(BaseModel):
    """진단 1건. bool이 아니라 이것을 반환한다."""

    code: DiagnosticCode
    severity: DiagnosticSeverity
    message: str                     # 한국어, 사용자에게 보여줄 문구
    relpath: str | None = None       # 진단 대상 파일 (상대 경로)
    span: Span | None = None         # 위치 미상일 때 None
    quick_fix: QuickFix | None = None
    docs_ref: str | None = None      # 스펙 절 인용
```

**`severity`를 필드로 갖되 `code.severity(profile)`를 통해 계산하는 이유.**
코드는 `DiagnosticCode`에 있고 심각도 결정은 **심각도 맵**에 있다(§3.7).
`Diagnostic.severity`는 그 결과를 담는 필드일 뿐이다. 계산 로직이 두 곳에
있으면 프로필 추가 시 drift한다.

### 3.7 프로필 — 하나의 규칙 엔진, 하나의 심각도 맵

```python
class ValidationProfile(StrEnum):
    STRICT = "strict"    # 스펙 원문대로
    LENIENT = "lenient"  # 실제 클라이언트가 로드하는 기준


# 코드는 그대로 두고 심각도만 바꾼다. 규칙 엔진은 하나다.
_SEVERITY_MAP: dict[tuple[DiagnosticCode, ValidationProfile], DiagnosticSeverity] = {
    (DiagnosticCode.NAME_DIR_MISMATCH, ValidationProfile.STRICT):  DiagnosticSeverity.ERROR,
    (DiagnosticCode.NAME_DIR_MISMATCH, ValidationProfile.LENIENT): DiagnosticSeverity.WARN,
    (DiagnosticCode.NAME_TOO_LONG,     ValidationProfile.STRICT):  DiagnosticSeverity.ERROR,
    (DiagnosticCode.NAME_TOO_LONG,     ValidationProfile.LENIENT): DiagnosticSeverity.WARN,
    # lenient에서 description 누락·YAML 파싱 실패는 스킵 대상이므로 ERROR 유지(§3.8)
}
```

| 프로필 | `name`≠디렉터리 | `name`>64 | `description` 누락 | YAML 파싱 실패 |
|---|---|---|---|---|
| `strict` | `error` | `error` | `error` | `error` |
| `lenient` | `warn` | `warn` | `error` (스킵) | `error` (스킵) |

`lenient`에서 `description` 누락과 파싱 실패가 계속 `error`인 이유: 공식
client-implementation 가이드는 이 두 경우에만 **스킵**한다고 명시하고
나머지는 경고 후 로드한다고 한다 (PRD §4.2). 즉 이 둘은 "나관이 무른"
경우가 아니라 **스킬이 존재하지 않는** 경우다. 임계의 차이가 아니다.

**두 개의 독립 구현은 반드시 drift한다.** 이 프로젝트에서 이를 피할 수 있는
유일한 구조가 단일 규칙 엔진 + 심각도 맵이다.

### 3.8 불변식과 검증 규칙

`validate()`가 강제하는 불변식:

| ID | 불변식 | 대응 AC |
|---|---|---|
| `D-TEST-1` | `name`은 NFKC 정규화 후 부모 디렉터리명(NFKC)과 일치 | AC-1.2 |
| `D-TEST-2` | 유니코드 소문자 이름이 `name_charset`를 발생시키지 않는다 | AC-1.4 |
| `D-TEST-3` | `SkillFrontmatter`의 반올림이 항등이다: `parse(dump(m)) == m` | AC-1.3 |
| `D-TEST-4` | 6개 스펙 제약 각각이 **서로 다른** `DiagnosticCode`를 낸다 | AC-1.2 |
| `D-TEST-5` | 파스 실패 4종은 1:1로 매핑된다 | AC-1.6 |
| `D-TEST-6` | `strict`와 `lenient`가 **같은 코드 집합**을 쓰고 심각도만 다르다 | AC-1.5 |
| `D-TEST-7` | 스펙 `description` 1024자 **와** 클라이언트 1536자 예산이 각각 점검된다 | AC-1.3b |
| `D-TEST-8` | 5000개 스캔이 2초 미만이며 **바디를 메모리에 올리지 않는다** | AC-1.10 |

`D-TEST-2`가 중요한 이유: 이 테스트가 없으면 "ASCII만" 구현으로 퇴화하고,
한국어 스킬이 조용히 거부된다. PRD는 사용자가 한국어로 문서를 요청했다.
여러 지점에서 다룬 하드코딩 위험이 실제로 발현되는 지점이다.

### 3.9 카탈로그 스캔 계약 (AC-1.10)

```python
class SkillCatalogEntry(BaseModel):
    """티어 1 노출에 필요한 최소 정보. 바디를 읽지 않는다."""

    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    relpath: str            # SKILL.md의 상대 경로
    description_length: int
```

스캔 함수는 **프런트매터만** 읽고 종료한다. 본문 전체를 읽지 않는 이유는
프로gressive disclosure의 정의와 같다 — 티어 1 카탈로그 비용은 스킬당
~50–100 토큰이다 (PRD §4.2). 5000개 스킬의 본문을 읽으면 입력이 수백 MB가 되고
진단 하나를 내는 데 2초 규칙을 어긴다.

---

## 4. 알려진 확장 레지스트리 (`C3` `spec-core`)

### 4.1 문제 — "미지의 키"는 하나의 종류가 아니다

스펙은 폐쇄 집합 6개를 정의한다. `skills-ref`는 그 외 모든 키를
`Unexpected fields in frontmatter`로 보고한다 (PRD §4.2). 그러나 실제로
**Claude Code는 스펙에 없는 14개 필드를 문서화하고 존중한다** (PRD §4.2 표).

따라서 스킬에 `context: fork`가 있으면:

| 판정 | 결과 |
|---|---|
| `skills-ref` 방식 | "예상치 못한 필드" → 사용자가 **정상 동작하는 스킬의 필드를 삭제**함 |
| 올바른 판정 | 스펙 위반이지만 이식성 문제이며, 어느 클라이언트가 존중하는지 알려야 함 |

**이 구분이 제품의 신뢰를 좌우한다.** 잘못된 필드를 지우라고 안내하는 검증기는
사용자가 검증기를 무시하게 만든다.

### 4.2 `KeyClassification` 3분류

```python
class KeyClassification(StrEnum):
    SPEC = "spec"                        # 스펙 필드 → 유효
    CLIENT_EXTENSION = "client_extension"  # 알려진 클라이언트 확장 → 이식성 문제
    UNKNOWN = "unknown"                  # 진짜 미지의 키 → 오타 가능성
```

| 분류 | `strict` 심각도 | `lenient` 심각도 | 메시지 |
|---|---|---|---|
| `SPEC` | — (진단 없음) | — | — |
| `CLIENT_EXTENSION` | `error` | `warn` | "`context`는 스펙에 없는 필드입니다. Claude Code가 존중하지만 다른 클라이언트는 **무시합니다**. 이식성이 필요하면 `metadata` 하위로 옮기세요." |
| `UNKNOWN` | `error` | `warn` | "`version`은 스펙에도 없고 알려진 클라이언트 확장도 아닙니다. 오타이거나, `metadata.version`으로 옮겨야 합니다." |

`lenient`에서 둘 다 `warn`인 이유: lenient는 "실제 클라이언트가 로드하는 기준"이므로,
무시될 수 있는 필드는 로드를 막지 않는다. 다만 `unknown`은 오타 가능성이 있어
`client_extension`보다 **메시지가 더 직접적**이어야 한다.

### 4.3 레지스트리는 코드가 아니라 데이터

제약 `C14`: *"레지스트리는 데이터다. 새 클라이언트는 규칙 엔진 수정을 요구해서는 안 된다.
클라이언트는 스펙보다 빠르게 필드를 추가한다."*

```python
class KnownExtension(BaseModel):
    """클라이언트 확장 필드 1건."""

    model_config = ConfigDict(frozen=True)

    key: str                                  # kebab-case, 예: disable-model-invocation
    clients: frozenset[str]                   # 존중하는 클라이언트 ID
    effect: str                               # 한국어 1문장 설명
    value_type: Literal["bool", "string", "string_list", "enum", "map", "any"]
    default: str | None = None
    is_conditional: bool = False              # 버전·플래그에 따라 동작 여부 다름
    notes: str | None = None
```

**규칙 엔진은 레지스트리를 "조회"만 한다.** 새 클라이언트 추가는 JSON 파일에
항목 하나를 추가하는 일이다. 새 필드마다 `if` 분기를 추가하면 그 파일은
곧 스펙의 진화를 따라가지 못한다.

### 4.4 Claude Code 비표준 필드 14개 (전수)

출처: Claude Code *Frontmatter reference* (PRD §4.2에서 인용). `strict`에서
전부 `error`이며 메시지가 이식성 문제를 명시한다.

| # | 키 | 타입 | 효과 | 조건부 |
|---|---|---|---|---|
| 1 | `when_to_use` | `string` | 목록에서 `description`에 **덧붙여** 표시. 1536자 예산에 **함께** 소모 | — |
| 2 | `disable-model-invocation` | `bool` | `true`면 Claude가 자동 로드하지 않음. 서브에이전트 프리로드와 예약 작업도 차단 | ≥ 2.1.196 |
| 3 | `user-invocable` | `bool` | `false`면 `/` 메뉴에서 숨고 모델 전용. 기본 `true` | — |
| 4 | `argument-hint` | `string` | 자동완성 힌트. 예: `[issue-number]` | — |
| 5 | `arguments` | `string \| list[str]` | `$name` 위치 인자 치환. 공백 구분 문자열 또는 YAML 리스트 | — |
| 6 | `disallowed-tools` | `string \| list[str]` | 활성 중 도구 풀에서 제거. 이 턴이 지나면 해제 | — |
| 7 | `model` | `string` | 활성 중 모델 오버라이드. `inherit` 유지 가능. `context: fork` 시엔 포크된 서브에이전트 모델 | — |
| 8 | `effort` | `enum` | `low`\|`medium`\|`high`\|`xhigh`\|`max`. 세션 값을 덮어씀 | — |
| 9 | `context` | `enum` | `fork`면 포크된 서브에이전트 컨텍스트에서 실행 | — |
| 10 | `agent` | `string` | `context: fork`일 때 쓸 서브에이전트 종류 | `context: fork` 필요 |
| 11 | `background` | `bool` | `false`면 결과 대기. 기본 `true` | `context: fork` 필요, ≥ 2.1.218 |
| 12 | `hooks` | `map` | 스킬 호출 시 등록되어 **세션 내내 계속 실행**되는 훅. 보안상 중요 (§6.3) | — |
| 13 | `paths` | `string \| list[str]` | 자동 활성화 조건을 glob 패턴으로 제한 | — |
| 14 | `shell` | `enum` | `bash`(기본) 또는 `powershell`. 인라인 명령 블록의 셸 선택 | — |

`is_conditional` 열을 둔 이유: `background`는 `context: fork` 없이는 무의미하다.
필드가 존재한다는 사실만으로는 실제로 작동하는지 알 수 없다. 조건부 필드는
메시지에 "이 필드는 `context: fork`와 함께 있어야 효과가 있습니다"를 덧붙인다.

### 4.5 설명 예산 2중화

**두 개의 서로 다른 예산이 동시에 존재한다.**

| 예산 | 값 | 측정 대상 | 출처 | 성격 |
|---|---|---|---|---|
| 스펙 하드 제한 | **1024자** | `description` 단독 | 스펙 `description` 필드 | 명시적 위반 → `description_too_long` |
| 클라이언트 트렁크 | **1536자** | `description` **+ `when_to_use` 결합** | Claude Code 스킬 목록 | **조용한 절단** → `truncation_risk` |

1536자 제한은 컨텍스트 절약을 위해 목록에서 적용된다 (PRD §4.2). `when_to_use`는
스펙 필드가 아니므로 스펙 검증에는 절대 걸리지 않고, **오직 클라이언트
트렁크에만** 영향을 준다. 그래서 두 검사가 **독립적으로** 필요하다.

| 상황 | `description` | `when_to_use` | 결과 |
|---|---|---|---|
| 전부 통과 | 200자 | 100자 | 통과. 결합 300 < 1536 |
| 결합만 초과 | 900자 | 800자 | **스펙 통과. 그러나 결합 1700 > 1536** → `truncation_risk` |
| `description`만 초과 | 1100자 | 0자 | `description_too_long` |
| 둘 다 초과 | 1100자 | 600자 | **두 진단이 동시에** 발생 |

**가장 위험한 것은 둘째 행이다.** 스펙 검증을 **통과**했는데 실제
클라이언트에서 **조용히 절단**된다. 사용자가 스펙이 말하는 대로
"1024자면 안전하다"고 믿고 작성하면 이 상태가 된다. 원인을 알 수 없으므로
`truncation_risk`를 별도 코드로 둔다 (AC-1.3b).

### 4.6 `name` 필수/선택 불일치

| 대상 | `name` |
|---|---|
| 스펙 | **필수** |
| Claude Code | **선택**. 기본값은 디렉터리 이름 |

그래서 `strict`에서 `name` 누락은 `error`이되, 메시지에 "일부 클라이언트는
디렉터리 이름을 기본값으로 사용합니다"를 덧붙인다. `lenient`에서는 `warn`으로
내린다 — 실제로 로드되므로.

### 4.7 예약 이름

Claude Code가 예약한 이름(PRD §4.9). 이 이름의 스킬은 **조용히 로드되지 않는다**.

| 이름 | 예약 사유 |
|---|---|
| `synced` | `~/.claude/skills/synced/`가 claude.ai 동기화 전용 |
| `anthropic-skills` | claude.ai 동기화 스킬의 네임스페이스 |
| `anthropic-skills:*` | 위 접두사는 전부 예약 |

`reserved_name` 진단은 `KeyClassification`과 별개다. 필드가 아니라
**값**에 대한 규칙이다. `C11` `installer`는 이 진단을 **차단 사유**로 사용한다([§8.5](#85-installplan과-가시성)).

---

## 5. 파서 계약 (`C3` `spec-core`)

### 5.1 프런트매터 추출

```
<파일 시작>
---                      ← 여는 구분자. 반드시 첫 줄
name: example             ← YAML 블록
description: ...
---                      ← 닫는 구분자
(본문)
```

```python
DELIMITER = "---"


def parse_frontmatter(content: str) -> tuple[dict[str, object], str]:
    """프런트매터를 (매핑, 본문)으로 분리한다. 실패 시 ParseError 계열 예외."""
    if not content.startswith(DELIMITER):
        raise ParseError(DiagnosticCode.PARSE_NO_OPENING_DELIMITER,
                         "파일 맨 위에 '---' 구분자가 있어야 합니다.")

    parts = content.split(DELIMITER, 2)
    if len(parts) < 3:
        raise ParseError(DiagnosticCode.PARSE_UNTERMINATED,
                         "프런트매터가 닫히지 않았습니다.")

    raw_yaml, body = parts[1], parts[2].strip()

    try:
        loaded = load_yaml_strict(raw_yaml)
    except YamlError as exc:
        raise ParseError(DiagnosticCode.PARSE_YAML_ERROR, f"YAML 문법 오류: {exc}") from exc

    if not isinstance(loaded, dict):
        raise ParseError(DiagnosticCode.PARSE_NOT_MAPPING,
                         "프런트매터는 키-값 맵이어야 합니다.")
    return loaded, body
```

`split(DELIMITER, 2)`의 `maxsplit=2`가 핵심이다. 본문에 `---`가 있어도
(수평선) 앞의 두 구분자에서만 자르고 나머지는 `body`에 그대로 남는다.
`maxsplit` 없이 자르면 수평선이 구분자로 오인되어 본문이 잘린다.

### 5.2 파일 탐색

```python
CANDIDATE_FILENAMES = ("SKILL.md", "skill.md")   # 대문자 우선, 소문자 폴백
```

참조 구현이 두 가지를 모두 수용한다 (PRD §4.2). 어느 것이 실제로 발견되었는지
`SkillDocument.skill_md_relpath`에 기록해, 재파싱 없이 경고를 정확히 낸다.

### 5.3 파스 오류 4종의 구별

| 코드 | 원인 | 클라이언트가 하는 일 (공식 가이드) |
|---|---|---|
| `parse_no_opening_delimiter` | `---`로 시작하지 않음 | **파일 전체를 본문으로 취급.** 프런트매터 없음 |
| `parse_unterminated` | 닫는 `---` 없음 | 파싱 불가 |
| `parse_yaml_error` | YAML 문법 오류 | **필드 없는 채로 스킬이 로드될 수 있음** (Claude Code 관측) |
| `parse_not_mapping` | 최상위가 맵 아님 (리스트·스칼라) | 파싱 불가 |

**네 경우를 하나로 뭉개면 안 된다.** 사용자가 할 수 있는 조치가 다르다.
`parse_no_opening_delimiter`는 맨 위에 `---` 한 줄을 넣으면 끝나고,
`parse_yaml_error`는 특정 줄의 문법 문제다. "파싱에 실패했습니다" 하나로
내보내면 사용자는 무엇을 고쳐야 하는지 알 수 없다.

### 5.4 관대 YAML 복구 계층

공식 client-implementation 가이드는 다른 클라이언트를 위해 작성된 스킬의
YAML이 **기술적으로 잘못되었으나 관대한 파서가 받아들인** 경우를 다룬다
(PRD §4.2). 대표 예시는 따옴표 안의 콜론이다.

```yaml
# 기술적으로 잘못된 YAML — 콜론이 파싱을 깨뜨림
description: Use this skill when: the user asks about PDFs
```

**복구 전략 (순서대로 시도, 성공하면 사용):**

1. 엄격 파싱
2. 실패하면 **콜론 뒤에 공백이 있는 스칼라 값**들을 따옴표로 감싸 재시도
3. 실패하면 **불량 항목을 `metadata` 하위로 격리**하고 `warning`을 낸다
4. 여전히 실패하면 정직하게 실패 (`parse_yaml_error`)

**복구의 한계선을 정한다.** 복구는 "관대한 파서가 받아들이는 입력"에만 적용한다.
임의로 고치려 들면 사용자의 스킬이 조용히 다른 의미로 바뀐다. 한계를 넘는 것은
진단으로 알리고 사용자가 고르게 한다. `parse_yaml_error`에 복구 시도를 여러 번
했다는 기록을 남겨, 왜 실패했는지 추적 가능하게 한다.

### 5.5 파싱 결과 불변식

| ID | 불변식 |
|---|---|
| `D-P-1` | 파싱 결과는 항상 `(프런트매터 맵, trim된 본문)` 2-튜플이다 |
| `D-P-2` | 파서는 **검증하지 않는다.** 스펙 위반은 `Diagnostic`로, 파싱 실패로 보지 않는다 |
| `D-P-3` | `name` 정규화는 `validate()` 단계에서 수행한다. 파서는 원본을 보존한다 |
| `D-P-4` | 본문이 빈 문자열이어도 오류가 아니다. 스킬이 파일만 있을 수 있다 |

`D-P-2`가 분리 원칙의 핵심이다. 파서와 검증기를 분리하면 파서를 고쳐도
검증 로직과 그 테스트는 손대지 않는다. 반대로 결합하면 "파싱 버그"와
"검증 버그"가 구분되지 않는다.

---

## 6. 정적 분석 모델 (`C5` `script-analyzer`)

### 6.1 스킬 전체가 실행 표면이다

**`scripts/` 디렉터리만 검사하면 안 된다.** Claude Code는 `SKILL.md` 본문의
`` !`<command>` `` 플레이스홀더를 **모델에게 전달하기 전에 셸 명령으로 실행**하고
출력을 그 자리에 치환한다. `` ```! `` 펜스 블록은 여러 줄에 대해 같은 일을 한다
(PRD §4.5).

따라서 **`scripts/`가 전혀 없는 순수 마크다운 스킬이 임의 코드 실행이 가능하다.**
겉보기에는 산문이기 때문에 더 멀쩡해 보이며, 실제로 더 위험하다 — 사용자가
"텍스트 파일이니 안전하다"고 판단하게 만든다.

| 표면 | 위치 | 실행 시점 | 탐지 난이도 |
|---|---|---|---|
| 인라인 플레이스홀더 | `SKILL.md` 본문 | 스킬 로드 시 | 낮음 (패턴 규칙) |
| 펜스 블록 | `SKILL.md` 본문 | 스킬 로드 시 | 낮음 |
| 번들 스크립트 | `scripts/**` | 에이전트가 명령할 때 | 중간 (인터프리터·의존성 추출) |
| 세션 훅 | `hooks` 프런트매터 | 스킬 호출 시, **세션 내내** | 낮음 |
| 도구 사전 승인 | `allowed-tools` | 턴 동안 | 낮음 |

### 6.2 `CapabilityKind` 전수

```python
class CapabilityKind(StrEnum):
    # 본문 실행 표면
    BODY_SHELL_EXEC = "body_shell_exec"                    # !`cmd`, ```!
    SESSION_PERSISTENT_HOOK = "session_persistent_hook"    # hooks
    TOOL_PREAPPROVAL = "tool_preapproval"                  # allowed-tools
    # 스크립트 표면
    DECLARED_DEPENDENCY = "declared_dependency"
    NETWORK_EGRESS = "network_egress"
    CREDENTIAL_ACCESS = "credential_access"
    FS_ESCAPE = "fs_escape"
    SUBPROCESS_SPAWN = "subprocess_spawn"
    DYNAMIC_EVAL = "dynamic_eval"


class CapabilitySeverity(StrEnum):
    INFO = "info"            # 정보성. 위험 아님
    SUSPICIOUS = "suspicious"  # 주의 필요. 맥락에 따라 정상
    DANGEROUS = "dangerous"    # 거의 확실히 위험


class Interpreter(StrEnum):
    PYTHON = "python"
    NODE = "node"
    BASH = "bash"
    RUBY = "ruby"
    DENO = "deno"
    BUN = "bun"
    GO = "go"
    UNKNOWN = "unknown"      # D-5: 탈출구
```

| `CapabilityKind` | 심각도 | 판정 근거 |
|---|---|---|
| `BODY_SHELL_EXEC` | **DANGEROUS** | 로드 시점에 사용자 모르게 실행됨 |
| `SESSION_PERSISTENT_HOOK` | **DANGEROUS** | 스킬이 끝난 뒤에도 세션 내내 실행 |
| `TOOL_PREAPPROVAL` | **DANGEROUS** | 퍼미션 프롬프트 없이 도구 사용 승인 |
| `NETWORK_EGRESS` | **DANGEROUS** | 외부로 데이터 유출 가능 |
| `CREDENTIAL_ACCESS` | **DANGEROUS** | 토큰·키 접근 |
| `FS_ESCAPE` | **DANGEROUS** | 스킬 루트 밖 쓰기/삭제 |
| `SUBPROCESS_SPAWN` | SUSPICIOUS | 자식 프로세스 실행. 정상 스킬도 사용 |
| `DYNAMIC_EVAL` | SUSPICIOUS | `eval`/`exec`. 정상 코드에도 있음 |
| `DECLARED_DEPENDENCY` | **INFO** | 이것은 위험이 **아니다.** 의존성 목록 |

`DECLARED_DEPENDENCY`가 INFO인 이유가 중요하다. "의존성이 12개"를 위험 신호로
표현하면 분석 결과가 의미를 잃는다. 사용자가 알아야 하는 것은
"무엇이 설치되는가"이지 "위험한가"가 아니다. 위험 신호와 정보 신호를 같은
톤으로 표시하면 **신뢰게이트 전체가 무효화**된다.

### 6.3 인라인 플레이스홀더의 정확한 규칙

과다 탐지(false positive)는 신뢰를 파괴한다. 규칙을 정확히 인코딩한다.

```
인라인 형식은 ! 가 행 시작이거나 공백 바로 뒤에 있을 때만 인식된다.
```

| 입력 | 실행되는가 | 이유 |
|---|---|---|
| `` !`git diff HEAD` `` | ✅ | 행 시작 |
| ``` - PR diff: !`gh pr diff` ``` | ✅ | 공백 직후 |
| `` KEY=!`cmd` `` | ❌ | `=`가 직전 문자. **리터럴 텍스트** |
| `` a!`cmd` `` | ❌ | `a`가 직전 문자 |

그리고 **대체는 원본 파일에 대해 1회만** 수행된다. 명령 출력이 추가
플레이스홀더를 만들어도 그것은 확장되지 않는다 (전이적 확장 아님).

```python
INLINE_PLACEHOLDER = re.compile(r"(?:(?<=\s)|^)!`([^`\n]+)`")
FENCED_BLOCK = re.compile(r"^```![ \t]*\n(.*?)^```[ \t]*$", re.DOTALL | re.MULTILINE)
```

`(?<=\s)|^`가 `KEY=!`cmd``를 **제외**하는 핵심이다. `!`만 찾는 단순 패턴은
오탐을 낸다.

> **분석기가 표현해야 할 것**: 이 규칙을 구현에 임베드하지 말고
> `CapabilityFinding.explanation`에 **명시**한다. 전개를 부수적으로 표현하면
> 사용자가 "내 스킬이 더 위험하다고 생각하는 이유"를 이해할 수 없다.

### 6.4 `CapabilityReport` / `CapabilityFinding`

```python
class CapabilityFinding(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: CapabilityKind
    severity: CapabilitySeverity
    relpath: str                              # 발견 위치(상대 경로)
    span: Span | None = None
    summary: str                              # 한국어 1문장
    detail: str                               # 무엇이 왜 위험한지
    evidence: str | None = None               # 발견한 원문 조각
    interpreter: Interpreter | None = None
    declared_dependencies: tuple[str, ...] = ()


class CapabilityReport(BaseModel):
    """스킬 전체의 실행 표면 보고서. 실행 없이정적적으로 산출된다."""

    skill_name: str
    findings: list[CapabilityFinding]
    scanned_files: int
    has_executable_surface: bool = False       # 안전한 스킬의 긍정 신호(§6.5)

    @property
    def max_severity(self) -> CapabilitySeverity | None:
        return max((f.severity for f in self.findings), default=None, key=_SEV_ORDER)
```

### 6.5 안전 신호의 표현

`findings == []`인 스킬은 **그 자체로 정보**다. `C12` UI는 이를
"실행 표면 없음"으로 **긍정적으로** 표시한다 (의도적 설계, PRD §4.5).

분석기가 "문제가 없다"와 "분석하지 못했다"를 구분하도록:

```python
analysis_complete: bool = True   # False면 스캔 자체가 실패(권한 오류 등)
scan_errors: list[str] = []
```

`analysis_complete=False`를 "안전"으로 표시하면 사용자가 잘못 신뢰한다.
**분석 실패는 안전이 아니다.**

### 6.6 분석기의 순수성

`script-analyzer`는 **파일 바이트의 순수 함수**여야 한다.

| 요구 | 이유 |
|---|---|
| 파일 시스템에 쓰지 않는다 | 분석 중 스킬 변조가 불가능해야 한다 |
| 네트워크에 접근하지 않는다 | 분석기가 공격 대상이 되지 않는다 |
| 실행하지 않는다 | 이름이 `sandbox-runner`인 `C6`의 존재 이유가 이것이다 |
| 결정적 | 같은 바이트 → 같은 보고서. 회귀 테스트가 가능 |

이 순수성 덕분에 **악의적 픽스처로철저히 테스트**할 수 있다. "이 페이로드가
탐지되는가"를 실제 실행 없이 검증한다.

### 6.7 의존성 추출

| 포맷 | 위치 | 도구 |
|---|---|---|
| PEP 723 | `.py` 내 `# /// script` 블록 | `tomllib` |
| `package.json` | `dependencies`, `devDependencies` | `json` |
| `requirements.txt` | 전 줄 | 줄 파싱 |
| `go.mod` | `require` 블록 | 정규식 |
| `Gemfile` | `gem` 블록 | 정규식 |
| `*.csproj` / `pom.xml` | | 본 v1 범위 밖 — `analysis_complete`에 기록 |

**추출은 정적 텍스트 분석이며 의존성을 설치하지 않는다.** `uv run`으로
실행하는 것은 `C6`의 몫이고, 그것은 opt-in이다.

### 6.8 샌드박스 모델

```python
class SandboxState(StrEnum):
    READY = "ready"
    UNAVAILABLE = "unavailable"      # 샌드박스 기설 실패 → fail-closed
    DENIED = "denied"                # 사용자 거부


class SandboxProfile(BaseModel):
    """격리 정책. 실패-닫힘의 상태를 명시적으로 모델링한다."""

    network_enabled: bool = False     # 기본 차단
    network_allowlist: tuple[str, ...] = ()
    readonly_mounts: tuple[str, ...] = ("skill_dir",)
    writable_mounts: tuple[str, ...] = ("output_dir",)   # tmpfs
    allow_home: bool = False
    run_as_non_root: bool = True
    wall_clock_timeout_s: int = 60
    memory_limit_mb: int = 512
    cpu_limit: float = 1.0
    max_processes: int = 64
    max_output_bytes: int = 1_048_576


class SandboxRunResult(BaseModel):
    state: SandboxState
    exit_code: int | None
    stdout: str
    stderr: str
    duration_ms: int
    truncated: bool                  # 출력 상한 도달 여부
    timed_out: bool
```

`SandboxState.UNAVAILABLE`이 `FAILED`와 **별개인 값**인 이유: 제약 `C6`은
**fail-closed**를 요구한다. 샌드박스를 세울 수 없으면 **샌드박스 없이 진행되지
않고 오류**가 난다. "실행 실패"와 "격리 실패"를 같은 상태로 두면 소비자가
실패를 무시하고 무격리 실행으로 폴백할 위험이 있다. `UNAVAILABLE`은
**폴백 불가**를 뜻하는 값이다.

---

## 7. 평가 도메인 모델 (`C7` `eval-engine` / `C8` `RunAdapter`)

**이 절이 가장 중요하다.** 공식 문서의 디스크 계약을 **그대로** 구현한다.
공식 문서를 따라 작성된 스킬이 **변환 없이** 스튜디오에서 동작해야 한다
(PRD §4.6).

### 7.1 `evals/evals.json` — 사람이 작성하는 유일한 파일

공식 문서의 원본 예시:

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

```python
class EvalCase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int                                  # 정수. 공식 계약
    prompt: str                              # 실제 사용자가 입력할 문장
    expected_output: str                     # 성공의 모습에 대한 사람이 읽는 설명
    files: list[str] = Field(default_factory=list)      # D-3: 상대 경로
    assertions: list[str] = Field(default_factory=list)  # 채점 가능한 진술


class EvalSuite(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    skill_name: str
    evals: list[EvalCase]
```

| 필드 | 제약 | 비고 |
|---|---|---|
| `EvalCase.id` | 양의 정수, 스위트 내 유일 | 형식상 `int`이나 실제 고유성은 불변식으로 강제 |
| `prompt` | 공백 아님 | "process this data"처럼 모호하면 아무것도 검증하지 못한다 |
| `expected_output` | 공백 아님 | 사람 읽기 설명. **기계 판정 대상이 아님** |
| `files` | 스킬 루트 기준 상대 경로. 스테이징 밖 불가 | §10 |
| `assertions` | 자유 문자열 | 판정 방식은 채점기가 정한다 (§7.5) |

**`expected_output`이 기계 판정 대상이 아닌 이유.** 공식 문서는 이것을
"human-readable description of what success looks like"로 정의한다.
따라서 "기계가 pass_rate를 계산할 수 있는 형태"로 강제하면 공식 계약을
깨뜨린다. 기계 판정은 `assertions`의 역할이다.

### 7.2 `ArmName` — 세 가지 arm

```python
class ArmName(StrEnum):
    WITH_SKILL = "with_skill"
    WITHOUT_SKILL = "without_skill"
    OLD_SKILL = "old_skill"       # 이전 버전 스냅샷 기준선
```

| arm | 의미 | 산출 디렉터리 | 언제 쓰나 |
|---|---|---|---|
| `with_skill` | 스킬 제공 | `with_skill/` | 항상 |
| `without_skill` | 스킬 없음 | `without_skill/` | 스킬의 순수 기여를 측정 |
| `old_skill` | 이전 버전 | `old_skill/` | 개선폭을 측정 |

**A/B 실행은 강제된다.** 한 번의 실행은 결과가 아니다. 차이야 결과다
(PRD §4.6). 케이스 하나가 `with_skill`만 실행되었다면 그것은 **불완전한
측정**이며 `C7`은 이를 명시적으로 경고한다.

### 7.3 `ArmResult` / `Timing` / `Grading`

```python
class Timing(BaseModel):
    """timing.json. 공식 문서는 이 값이 다른 곳에 저장되지 않으므로
    즉시 기록해야 한다고 명시한다."""

    total_tokens: int | None = None
    duration_ms: int | None = None
```

**두 필드가 `| None`인 이유.** 어댑터가 항상 두 지표를 보고하는 것은
보장이 아니다 ([§7.7](#77-runadapter-프로토콜)의 `AdapterCapabilities`).
0을 넣으면 "0토큰으로 성공했다"와 "측정되지 않았다"가 구별되지 않는다.
**`None`이 정직한 값**이다.

```python
class AssertionVerdict(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    UNVERIFIABLE = "unverifiable"   # D-5: 탈출구


class AssertionResult(BaseModel):
    """grading.json의 assertion_results 항목."""

    text: str                                    # 원문 assertion 그대로
    passed: bool
    verdict: AssertionVerdict
    evidence: str | None = None                  # 출력이 인용한 근거
    grader: Literal["deterministic", "llm_judge", "human"]


class Grading(BaseModel):
    """grading.json."""

    assertion_results: list[AssertionResult] = Field(default_factory=list)
    summary: GradingSummary


class GradingSummary(BaseModel):
    passed: int
    failed: int
    unverifiable: int
    total: int
    pass_rate: float
```

**`pass_rate`의 계산 규칙 (명시적 선택).**

```
pass_rate = passed / total
```

`unverifiable`을 분모에서 **제외하지 않는다**. 제외하면 채점이 불가능한
스킬이 "완벽한 점수"를 받는다. 대신 `summary`가 `unverifiable` 개수를
별도로 노출해 사용자가 "점수가 왜 낮은지"와 "판정 자체가 안 됐는지"를
구분하게 한다.

### 7.4 증거 강제 규칙

공식 문서의 채점 원칙은 명확하다 (PRD §4.6):

> *"Require concrete evidence for a PASS. Don't give the benefit of the doubt."*
> *"의견만 말하지 말고 출력을 인용하거나 참조하라."*

```python
def grade_llm_assertion(assertion: str, outputs: list[str],
                        judge_output: JudgeVerdict) -> AssertionResult:
    """LLM 판정에 증거 강제를 적용한다."""
    if not judge_output.passed:
        return AssertionResult(text=assertion, passed=False,
                               verdict=AssertionVerdict.FAIL,
                               evidence=judge_output.evidence, grader="llm_judge")

    if not has_quotable_evidence(judge_output.evidence, outputs):
        # 증거가 없거나 출력을 인용하지 않으면 PASS를 인정하지 않는다.
        return AssertionResult(
            text=assertion, passed=False,
            verdict=AssertionVerdict.UNVERIFIABLE,
            evidence="판정 근거가 실제 출력을 인용하지 않습니다.",
            grader="llm_judge")
    return AssertionResult(text=assertion, passed=True,
                           verdict=AssertionVerdict.PASS,
                           evidence=judge_output.evidence, grader="llm_judge")
```

`has_quotable_evidence()`는 판정 근거에 **출력에서 실제로 존재하는 문자열**이
포함되는지 확인한다. 추상적 문장("차트가 잘 나왔습니다")은 증거가 아니다.

`UNVERIFIABLE`을 `FAIL`과 **다른 값**으로 두는 이유: 사용자가 "이 assertion을
고쳐야 하나, 모델이 못한 것인가"를 구분해야 한다. 두 원인이 다르고 대응도
다르다. `C12` UI는 세 상태를 서로 다른 색으로 표시한다.

### 7.5 채점 파이프라인 — 결정론적 우선

공식 문서 (PRD §4.6):

> *"코드로 검사할 수 있는 것(유효한 JSON, 정확한 행 수, 기대 치수의 파일 존재)에는
> 검증 스크립트를 써라. 스크립트가 LLM 판단보다 기계적 검사에 더 신뢰할 만하다."*

```python
class GradingStage(StrEnum):
    DETERMINISTIC = "deterministic"   # 항상 먼저
    LLM_JUDGE = "llm_judge"           # 남은 것만
    HUMAN = "human"                   # assertion으로 표현 불가


class DeterministicChecker(Protocol):
    """기계 판정 가능한 assertion. 구현은 assertion 텍스트에서 매칭된다."""

    checker_id: str
    def matches(self, assertion: str) -> bool: ...
    def check(self, assertion: str, outputs: list[str],
              expected_output: str) -> AssertionResult | None: ...
```

기본 제공 결정론적 체커:

| 체커 | 판정 | 예시 assertion |
|---|---|---|
| `file_exists` | 산출 파일 존재 | "차트 이미지 파일을 포함한다" |
| `valid_json` | 출력이 유효 JSON | "출력이 유효한 JSON이다" |
| `valid_csv` | CSV 파싱 가능 | "CSV로 파싱된다" |
| `image_dimensions` | 이미지 최소 치수 | "가로 800px 이상이다" |
| `contains_heading` | 특정 제목 존재 | "요약 섹션을 포함한다" |
| `count_at_least` | 개수 하한 | "권고가 3개 이상이다" |
| `line_count` | 행 수 범위 | "100줄 미만이다" |

**파이프라인 규칙:**

```python
def grade_case(case: EvalCase, outputs: list[str],
               checkers: list[DeterministicChecker],
               judge: LlmJudge) -> Grading:
    results: list[AssertionResult] = []
    remaining: list[str] = []

    # 1단계: 결정론적 체커가 claim할 수 있는 것을 먼저 처리
    for assertion in case.assertions:
        for checker in checkers:
            hit = checker.matches(assertion)
            if hit:
                res = checker.check(assertion, outputs, case.expected_output)
                if res is not None:
                    results.append(res)
                break
        else:
            remaining.append(assertion)

    # 2단계: 남은 것만 LLM 판정으로
    for assertion in remaining:
        results.append(grade_llm_assertion(assertion, outputs, judge.judge(assertion, outputs)))

    return Grading(assertion_results=results, summary=summarize(results))
```

**AC-2.8의 검증 가능성.** 이 구조 덕분에 "결정론적 assertion은 LLM 판정을
호출하지 않는다"를 **테스트로 증명**할 수 있다. 판정 어댑터에 호출 카운터를
두고, 결정론적 assertion만 있는 케이스에서 카운터가 `0`인지 단언한다.
파이프라인 순서가 뒤집히면 이 테스트가 즉시 실패한다.

### 7.6 `Feedback` — 사람의 검토

```python
class Feedback(BaseModel):
    """feedback.json. eval 디렉터리별 사용자 메모."""

    notes: dict[str, str] = Field(default_factory=dict)   # eval 디렉터리 이름 → 메모
```

**빈 문자열은 정상값이며 "의견 없음"을 뜻한다.** 공식 문서는 *"문제가 있으면
기별적인 메모를 남기고, 비어 있으면 그 테스트 케이스는 검토를 통과한 것"*이라
명시한다 (PRD §4.6). 따라서 `""`를 "미검토"로 해석하면 안 된다.
**`None`(키 없음)이 "미검토"이고 `""`가 "이상 없음"**이다.

| 값 | 의미 |
|---|---|
| 키 없음 | 사람이 아직 검토하지 않음 |
| `""` | 검토했고 이상 없음 |
| `"축 레이블이 없다"` | 검토했고 구체적 문제 있음 |

이 구분이 뒤집히면 UI가 "검토 필요"인 케이스를 "통과"로 보여준다.
`C12`는 이 구분을 그대로 사용한다.

### 7.7 `RunAdapter` 프로토콜

```python
class AdapterCapabilities(BaseModel):
    """어댑터가 항상 제공할 수 있는 것과 아닐 수 있는 것을 명시."""

    reports_tokens: bool = False
    reports_duration: bool = True
    supports_skill_loading: bool = True
    supports_clean_context: bool = False   # 런마다 새 세션으로 격리 가능한가
    supports_subagent_isolation: bool = False


class RunRequest(BaseModel):
    prompt: str
    input_files: tuple[str, ...]
    output_dir: str
    skill_dir: str | None = None       # None이면 without_skill arm
    max_turns: int = 20
    disable_model_invocation: bool = False   # §7.9


class RunAdapter(Protocol):
    """제공자 어댑터. G5: 스튜디오는 특정 벤더에 종속되지 않는다."""

    adapter_id: str
    capabilities: AdapterCapabilities

    async def run(self, request: RunRequest) -> ArmResult: ...
```

**`capabilities`가 `| None` 대신 선언적이어야 하는 이유.** 제3의 어댑터가
`total_tokens`를 보고하지 못할 수 있다. `None`으로 값을 넣으면
"0토큰"과 "미보고"가 같아진다. `reports_tokens=False`면
`Timing.total_tokens = None`이고 `C12`는 그 칸에 "—"을 표시한다.

**`MockAdapter`** 는 CI의 중심이다 (AC-2.6).

```python
class MockAdapter:
    """결정적 canned 트랜스크립트. 네트워크·API 키 불필요."""

    adapter_id = "mock"
    capabilities = AdapterCapabilities(reports_tokens=True, reports_duration=True,
                                       supports_clean_context=True)

    def __init__(self, script: Path) -> None:
        self._script = script      # 케이스별 예상 출력 디렉터리
```

`MockAdapter` 덕분에 **전체 L3 파이프라인이 CI에서 오프라인·무API키로
결정적으로** 돈다. 이것이 AC-2.6의 근거이며, 이 단계의 설계 중심이다.

### 7.8 `disable-model-invocation`의 처리

`disable-model-invocation: true`인 스킬은 Claude Code에서 **자동 로드되지
않는다** (PRD §4.2 필드 #2). 따라서 with_skill arm에서 이 스킬을 자동 활성화
시키는 것은 **실제 클라이언트가 결코 지나지 않는 경로를 테스트**하는 것이고,
결과는 무의미하다.

```python
class ArmResult(BaseModel):
    outputs: list[str]
    timing: Timing
    grading: Grading
    skill_auto_activated: bool | None = None    # None이면 어댑터가 보고 못함
    notes: list[str] = Field(default_factory=list)
```

`C7`은 `EvalCase`를 실행하기 전에 스킬 프런트매터를 읽어
`disable-model-invocation`을 확인하고, 참이면:

1. with_skill arm에서도 **명시적 호출로만** 스킬을 로드한다.
2. `ArmResult.notes`에 `"disable-model-invocation: true — 자동 활성화를 건너뛰고 명시적으로 로드했습니다"`를 기록한다.
3. `C12` 리포트에 이 사실을 **눈에 띄게** 표시한다 (AC-2.1e).

3번이 없으면 사용자는 "왜 스킬이 안 먹혔지"를 추적할 수 없다.

### 7.9 `Benchmark` / `MetricStats` / `BenchmarkDelta`

```python
class MetricStats(BaseModel):
    """집계 통계. n을 반드시 저장한다."""

    mean: float
    stddev: float | None = None   # n < 2면 None. 계산하지 않는다.
    n: int


class ArmSummary(BaseModel):
    pass_rate: MetricStats
    time_seconds: MetricStats
    # 어댑터가 토큰을 보고하지 않으면 None이다(AdapterCapabilities).
    # MetricStats를 유지하지 않는다 — 0 토큰으로 보고하면
    # "0토큰으로 성공"과 "미보고"가 구별되지 않는다(§7.9).
    tokens: MetricStats | None = None


class BenchmarkDelta(BaseModel):
    pass_rate: float
    time_seconds: float
    tokens: float


class Benchmark(BaseModel):
    """benchmark.json."""

    run_summary: dict[ArmName, ArmSummary]
    delta: BenchmarkDelta | None = None      # 기준 arm 없으면 None
```

**`stddev: float | None`이 이 도메인의 가장 중요한 설계다.** 공식 문서는
명시적으로 경고한다 (PRD §4.6):

> *"표준편차(stddev)는 arm당 여러 번 실행했을 때만 의미가 있다. 초기 반복에서
> 테스트 케이스가 2~3개이고 단일 실행이라면, 원시 pass 개수와 delta에 집중하라."*

그러므로:

- `n == 1` → `stddev = None`. **0.0이 아니다.** 0.0은 "편차가 없다"를
  주장하므로, 단일 실행에서 오해를 유발한다.
- `tokens`에 `MetricStats`가 없어도 된다. `reports_tokens=False`인
  어댑터에서는 `tokens` 대신 `None`이 들어간다. `ArmSummary.tokens: MetricStats | None`.

`C12`는 `stddev is None`일 때 차트에 표준편차 영역을 **그리지 않고**
"런 부족 — 반복 실행 필요"를 표시한다 (AC-2.7). **성공을 그리는 척해서는 안 된다.**

### 7.10 `AssertionAnalysis` — 공식 문서가 지시하는 4종 분석

공식 문서는 집계 통계를 해석하는 방법을 4가지 제시한다 (PRD §4.6).

```python
class AnalysisPattern(StrEnum):
    PASSES_BOTH = "passes_both"        # 양쪽 통과 → 노이즈
    FAILS_BOTH = "fails_both"          # 양쪽 실패 → 깨진 assertion
    ONLY_WITH_SKILL = "only_with_skill"  # 스킬의 실제 가치
    HIGH_VARIANCE = "high_variance"    # 모호한 지시 또는 flaky


class AssertionAnalysis(BaseModel):
    pattern: AnalysisPattern
    assertion_texts: list[str]
    explanation: str        # 한국어. 무슨 조치를 해야 하는지
    severity: Literal["info", "action_required"]
```

| 패턴 | 판정 | 설명 | 조치 |
|---|---|---|---|
| `passes_both` | 두 arm 모두 PASS | 스킬 없이도 되므로 통과율을 부풀린다 | assertion을 스킬의 가치에 맞게 좁힌다 |
| `fails_both` | 두 arm 모두 FAIL | assertion이 깨졌거나 너무 어려운 케이스 | assertion 또는 케이스를 고친다 |
| `only_with_skill` | with만 PASS, without은 FAIL | **스킬이 실제로 기여하는 지점** | 유지. 이것이 정답 |
| `high_variance` | 반복 간 `stddev` 높음 | 프롬프트가 flaky하거나 지시가 모호 | 지시를 구체화하거나 예시를 추가 |

`only_with_skill`이 유일하게 "좋은" 패턴이라는 점을 명시한다. 사용자가
스킬을 평가할 때 보는 것은 결국 이 패턴의 유무다.

### 7.11 워크스페이스 레이아웃

공식 계약을 **바이트 호환**으로 생성한다 (AC-2.5).

```
<skill-name>-workspace/
└── iteration-1/
    ├── eval-top-months-chart/
    │   ├── with_skill/
    │   │   ├── outputs/
    │   │   ├── timing.json
    │   │   └── grading.json
    │   ├── without_skill/
    │   │   ├── outputs/
    │   │   ├── timing.json
    │   │   └── grading.json
    │   └── feedback.json          # 또는 iteration 루트. 공식 예시 참조
    ├── eval-clean-missing-emails/
    │   └── ...
    └── benchmark.json
```

| 경로 규칙 | 결정 |
|---|---|
| `eval-<slug>` | 케이스 `id`에서 **슬러그 생성**. 표시는 사람이 읽는 이름 |
| `iteration-N` | 1부터 증가. 이전 반복을 덮어쓰지 않는다 |
| `timing.json` | `C7`이 **실행의 부수 효과로** 기록. 사용자가 하는 단계가 아니다 |
| `outputs/` | 어댑터가 만든 산출 파일. 비어 있어도 디렉터리는 만든다 |

`iteration-N`을 덮어쓰지 않는 이유: 반복 간 비교가 이 도구의 목적이다.
1번 반복을 덮어쓰면 개선폭을 측정할 수 없다.

---

## 8. 패키징 · 설치 모델 (`C10` `packager` / `C11` `installer`)

### 8.1 `ArtifactManifest` — 아카이브 **외부**

```python
class FileDigest(BaseModel):
    relpath: str
    sha256: str
    size_bytes: int
    mode: str          # "0644" 또는 "0755"


class TreeDigest(BaseModel):
    """트리 전체 해시. 파일 나열 순서에 무관해야 한다."""

    sha256: str
    file_count: int
    total_bytes: int


class ArtifactManifest(BaseModel):
    """아카이브와 함께 제공되지만 아카이브 '내부'가 아니다."""

    artifact_name: str
    artifact_sha256: str
    tree: TreeDigest
    files: list[FileDigest]        # relpath 정렬
    skill_name: str
    spec_version: str              # 스튜디오 버전이 아니라 사용한 스펙 판독본
    created_with: str              # "skill-studio/0.1.0"
    license: str | None = None
    compatibility: str | None = None
    created_at: str                # ISO 8601. 재현성 비교 시 제외 대상
```

**`manifest.json`이 아카이브 밖에 있는 이유.** 식별성과 해시 검사가
**추출 없이** 가능해야 한다. 아카이브 내부에 넣으면 검증 전에 먼저 풀어야
하고, 검사할 대상이 손상되었을 때(해시 불일치) 진위를 판단할 근거가 사라진다.
요약 정보를 신뢰할 수 없으면 요약 정보는 없다.

**`created_at`만 재현성 비교에서 제외한다.** 시간은 본질적으로 비결정적이며,
제외하지 않으면 AC-3.1이 영영 성립하지 않는다. **제외 목록을 명시하지 않으면
"재현 가능"의 정의가 구현마다 달라진다** — 그래서 이 문서에서 고정한다.

### 8.2 재현성 고정 파라미터

동일 입력 → **바이트 동일** 아카이브. 이를 위해 고정해야 하는 것:

| 파라미터 | 값 | 비고 |
|---|---|---|
| 엔트리 정렬 | `relpath` 오름차순, **`LC_ALL=C`** | 로케일에 따라 `가`/`z` 순서가 뒤집힌다 |
| 디렉터리 엔트리 | **포함하지 않는다** | 포함하면 개수·모드가 달라질 수 있다. 파일만으로 결정론을 확보한다 |
| tar 포맷 | GNU 고정, **USTAR 금지** | USTAR는 긴 경로에서 PAX 헤더를 자동 삽입한다 |
| PAX 확장 헤더 | **전부 비활성** | mtime·atime을 담은 확장 헤더가 빌드마다 달라지는 원인 |
| mtime | 고정값 (`0` 또는 `SOURCE_DATE_EPOCH`) | 파일 시스템의 실제 mtime은 비결정적 |
| uid / gid | `0` / `0` | 소유자 정보 제거 |
| owner 표기 | numeric (`uname`/`gname` 빈 문자열) | 이름이 환경(`useradd`)에 따라 달라진다 |
| 디렉터리 모드 | `0755` | |
| 파일 모드 | `0644` | |
| `scripts/**` 모드 | 원본이 실행 가능이면 `0755`, 아니면 `0644` | 유일한 예외 |
| ACL / xattr | 제거 | 파일 시스템에 따라 붙는다 |
| gzip 압축 레벨 | 고정 (예: 9) | 기본값이 라이브러리마다 다르다 |
| gzip `mtime` | `0` | |
| gzip 파일명 필드 | **미포함** | 원본 파일명이 기록된다 |
| gzip `OS` 바이트 | **고정** (`\x03` Unix) | 헤더 마지막 1바이트가 빌드 OS를 기록한다 |
| 심볼릭 링크 | **허용하지 않음** | 대상 경로가 환경 의존적이 된다 |

**가장 많이 빠지는 4가지와 그것이 바이트를 바꾸는 이유.**

| 빠지기 쉬운 항목 | 왜 바이트가 달라지는가 |
|---|---|
| `LC_ALL=C` 정렬 | 로케일에 따라 한글과 영문 순서가 뒤집힌다 |
| PAX 헤더 비활성 | 긴 경로에서 자동 삽입되고, mtime을 담은 확장 헤더가 된다 |
| gzip `OS` 바이트 | 헤더 마지막 1바이트가 빌드 OS를 기록한다 |
| 디렉터리 엔트리 제외 | 디렉터리 개수와 순서가 아카이브 구조에 영향을 준다 |

**검증은 서로 다른 두 임시 루트에서 한다.** 같은 프로세스에서 두 번 빌드하면
`mtime` 같은 환경 값이 공유되어 **거짓 통과**할 수 있다. 경로를 달리해
빌드하고 바이트를 비교해야 실제 재현성이 증명된다 (AC-3.1).

**심볼릭 링크를 패키징에서 제외하는 이유.** §10에서 아카이브가 제공하는
심볼릭 링크를 거부한다고 한다. 그것이 일관된다. 사용자 작성 스킬의
심볼릭 링크는 로컬 설치에서 추종하지만(§8.6), 패키징하면 상대 경로 계산이
환경 의존적이 되어 재현성이 깨진다.

### 8.3 `TreeDigest` 계산

```
1. 스킬 루트 아래 모든 일반 파일을 수집한다.
2. 각 파일의 relpath를 POSIX 형식('/' 구분)으로 정규화한다.
3. 각 파일에 대해: sha256(파일 바이트)를 계산한다.
4. 항목들을 (relpath, sha256) 순으로 정렬한다.
5. 각 줄을 "sha256␠␠relpath\n" 형식으로 이어붙인다.
6. 그 바이트열의 sha256이 tree digest다.
```

| 결정 | 이유 |
|---|---|
| 경로와 해시를 함께 해싱 | 파일 **이름** 변경이 반드시 트리 해시를 바꾼다 |
| 정렬 후 해싱 | 파일 나열 순서와 무관해야 한다 |
| 경로를 정규화 | `a/b`와 `a\b`가 같은 파일이어야 한다 |
| 도구 메타데이터 제외 | mtime·mode가 아닌 **내용과 경로만** |

### 8.4 `InstallTarget` / `ClientKind`

```python
class InstallScope(StrEnum):
    PROJECT = "project"
    USER = "user"


class ClientKind(StrEnum):
    AGENTS = "agents"      # ~/.agents/skills/ — 크로스 클라이언트 규약
    CLAUDE = "claude"
    CURSOR = "cursor"
    COPILOT = "copilot"
    CODEX = "codex"
    WINDSURF = "windsurf"


class ResolvedInstallTarget(BaseModel):
    """**내부 전용.** 절대 경로를 포함하므로 wire에 올리지 않는다."""

    model_config = ConfigDict(frozen=True)

    scope: InstallScope
    client: ClientKind
    abs_path: str        # D-3 예외: OS 호출에는 절대 경로가 필요하다.


class InstallTargetView(BaseModel):
    """**wire 안전.** `C12`가 받는 형태. 경로는 표시용으로만 담는다."""

    model_config = ConfigDict(frozen=True)

    scope: InstallScope
    client: ClientKind
    display_path: str    # 예: "~/.agents/skills/<name>/" (홈 축약 표기)
    writable: bool | None = None   # 사전 검사 결과
```

`display_path`가 `abs_path`를 대체한다. **`C12`는 절대 경로를 절대 받지 않는다.**
절대 경로가 UI에 나가면 사용자가 복사해 임의 위치에 스킬을 놓을 수 있고,
§9.4의 "클라이언트가 경로를 만들지 못한다"는 경계가 무너진다.
내부 계산은 `ResolvedInstallTarget`가 하고, wire에는 표시 문자열만 나간다.

대상 경로 매트릭스:

| scope | `AGENTS` | `CLAUDE` | `CURSOR` | `COPILOT` | `CODEX` | `WINDSURF` |
|---|---|---|---|---|---|---|
| `USER` | `~/.agents/skills/` | `~/.claude/skills/` | `~/.cursor/skills/` | — | `~/.codex/skills/` | `~/.windsurf/skills/` |
| `PROJECT` | `<proj>/.agents/skills/` | `<proj>/.claude/skills/` | `<proj>/.cursor/skills/` | `<proj>/.github/copilot/skills/` | `<proj>/.codex/skills/` | `<proj>/.windsurf/skills/` |

`AGENTS`가 `USER`·`PROJECT` 양쪽에 있는 이유: 공식 client-implementation
가이드가 이 경로를 "크로스 클라이언트 상호운용" 규약으로 명시한다 (PRD §4.9).
`C11`의 기본 추천 대상이다.

### 8.5 `InstallPlan`과 가시성

```python
class InstallPlan(BaseModel):
    """파괴적 작업 전에 항상 먼저 만든다. 사용자가 승인한 뒤 실행.

    `target`은 wire 안전한 `InstallTargetView`다. `resolved`는 내부 계산용이며
    `exclude=True`로 직렬화에서 제외된다.
    """

    target: InstallTargetView
    resolved: ResolvedInstallTarget | None = Field(default=None, exclude=True)
    skill_name: str
    source_relpath: str
    action: Literal["create", "update", "replace", "noop", "blocked"]
    blockers: list[Diagnostic] = Field(default_factory=list)
    warnings: list[Diagnostic] = Field(default_factory=list)
    shadowed_by: list[InstallTargetView] = Field(default_factory=list)
    reserved_name_conflict: bool = False


class VisibilityReport(BaseModel):
    """설치 후 실제 클라이언트 탐색을 재현한 결과."""

    target: InstallTargetView
    found: bool
    found_at: str | None = None
    is_shadowed: bool = False
    shadowing_source: str | None = None
    reserved_name: bool = False
    notes: list[str] = Field(default_factory=list)
```

**`VisibilityReport`가 "설치 성공"의 정의다.** "바이트를 썼다"가 아니라
**"클라이언트가 찾는다"** (PRD §4.9). `found=False`면 설치는 실패한 것이다.

`reserved_name_conflict`의 기본 처리 — **차단(blocked)**:

| 근거 | 설명 |
|---|---|
| 사후 발견이 불가능하다 | 예약 이름은 **조용히** 로드되지 않는다. 경고만 남기면 사용자는 스킬이 왜 동작 안 하는지 알아채지 못한다 |
| 되돌릴 수 없다 | 설치 후 발견되면, 스킬이 "설치되었으나 무효"인 상태로 남는다 |
| 대안이 있다 | 이름을 바꾸면 된다. `quick_fix`로 제공 |

`blocked`가 기본이고 `warn`은 선택적 오버라이드다. `C12`가 오버라이드
UI를 제공할지 여부는 [03. UI 디자인 §7.7](./03-ui-design.md#77-설치-및-가시성)에서 결정한다.

### 8.6 설치 시점의 신뢰 비대칭

| 상황 | 심볼릭 링크 | 이유 |
|---|---|---|
| 로컬 스캔 (`S1` 라이브러리) | **추종** | 사용자 설정이 합법적으로 자주 쓰인다 (PRD §4.9) |
| 아카이브 임포트 (`C4`) | **거부** | 공격자가 공급할 수 있다 |
| 패키징 (`C10`) | **제외** | 재현성이 깨진다 (§8.2) |

**세 처리가 다르지만 근거는 하나다: 콘텐츠의 출처 신뢰도가 다르다.**
사용자가 직접 만든 링크는 신뢰한다. 원격에서 받은 아카이브 안의 링크는
검증 없이 신뢰하면 탈출 경로가 된다. 이 비대칭은 코드와 테스트 양쪽에
명확히 드러나야 하며, 하나의 규칙으로 합치면 합법적 설치를 깨거나
트래버설을 허용한다 (제약 `C16`).

---

## 9. IPC 계약 (`C9` `ipc-contract`)

### 9.1 `Handshake`

```python
CONTRACT_VERSION = "1.0.0"

class Handshake(BaseModel):
    contract_version: str
    studio_version: str
    client_id: str
    capabilities: list[str] = Field(default_factory=list)
```

**버전 불일치는 명확한 시작 오류로 처리한다** (AC-5.2). 3계층 깊은
`KeyError`로 투명해서는 안 된다. `C1`은 불일치 시:

1. `contractVersion`의 주 버전·부 버전이 다르면 → **거부하고 종료**.
2. 주 버전이 같고 부 버전만 다르면 → 경고 후 계속(추가 필드는 무시).
3. 서버가 모르는 메서드 → `MethodNotFound` 에러. 조용히 무시 금지.

주 버전을 경계로 삼는 이유: 부 버전은 추가 가능(호환), 주 버전은
**파괴적 변경**(비호환)이다.

### 9.2 `Envelope[T]`

```python
class Envelope(BaseModel, Generic[T]):
    id: str                 # UUID. 요청-응답 상관 키
    method: str
    params: dict[str, Any]
    result: T | None = None
    error: RpcError | None = None
    seq: int | None = None  # 스트리밍 시퀀스. §9.3


class RpcError(BaseModel):
    code: str               # 안정 문자열
    message: str            # 한국어, 사용자 표시용
    detail: dict[str, str] = Field(default_factory=dict)   # Any 금지 (§2.4)
    retriable: bool = False
```

**오류에 `retriable`이 있는 이유.** `C12`가 "다시 시도" 버튼을 띄울지
결정해야 한다. 재시도 가능한 오류(`ETIMEDOUT`)와 불가능한 오류
(`VALIDATION_FAILED`)를 구분하지 않으면 사용자에게 의미 없는 버튼을 준다.

### 9.3 스트리밍

테스트 실행 로그는 요청 하나에 대한 **점진적 이벤트**다. 폴링은 비효율적이고,
장시간 실행에서 진행 상황이 보이지 않는 것은 신뢰를 깎는다.

```python
class StreamEventType(StrEnum):
    RUN_STARTED = "run_started"
    CASE_STARTED = "case_started"
    CASE_COMPLETED = "case_completed"
    STDOUT_CHUNK = "stdout_chunk"
    STDERR_CHUNK = "stderr_chunk"
    GRADED = "graded"
    BENCHMARK_READY = "benchmark_ready"
    RUN_FAILED = "run_failed"
    RUN_CANCELLED = "run_cancelled"


class StreamEvent(BaseModel):
    seq: int                       # 단조 증가. 클라이언트 재정렬용
    run_id: str
    case_id: int | None = None
    arm: ArmName | None = None
    type: StreamEventType
    payload: dict[str, Any] = Field(default_factory=dict)
```

`seq`가 **단조 증가**하는 이유: 네트워크·IPC 경계에서 순서가 뒤집힐 수 있다.
클라이언트가 `seq`로 재정렬하고 **갭을 감지하면** 스트림 유실을 알 수 있다.
샘플링하면 "로그가 빠졌다"를 사용자가 모른다.

### 9.4 `RpcMethod` 열거형

| 도메인 | 메서드 | PRD |
|---|---|---|
| **C3** | `spec.validate` · `spec.parse` · `spec.catalogScan` | §4.2 |
| **C4** | `io.import` · `io.export` · `io.readSkill` · `io.writeSkill` | §4.4 |
| **C5** | `analyze.capabilities` | §4.5 |
| **C6** | `sandbox.runScript` · `sandbox.probe` | §4.5 |
| **C7** | `eval.loadSuite` · `eval.run` · `eval.cancelRun` · `eval.listRuns` | §4.6 |
| **C8** | `eval.listAdapters` | §4.6 |
| **C10** | `package.build` · `package.preview` | §4.8 |
| **C11** | `install.plan` · `install.execute` · `install.uninstall` · `install.list` | §4.9 |
| **C9** | `sys.handshake` · `sys.health` | §4.7 |

**경로 문자열을 wire로 보내지 않는다는 규칙.** 클라이언트는
`skill_id`(상대 경로)나 `ClientKind`만 보낸다. 서버가 식별자를 경로로
해석한다. 이렇게 하면 클라이언트가 임의 경로를 만들어 디스크를 훑는 것이
구조적으로 불가능해진다. `install.plan`에 절대 경로를 받는 매개변수가
**존재하지 않아야 한다**.

### 9.5 생성 파이프라인

```
Pydantic 모델 (진실 공급원)
        │
        ├─ model_json_schema() ──► JSON Schema ──► 수동 검토·외부 도구 제공용
        │
        └─ datamodel-code-generator ──► TypeScript 타입
                                              │
                                    src/contract/generated.ts (커밋)
                                              │
                                    tsc --noEmit 가 CI에서 불일치 검출
```

| 규칙 | 근거 |
|---|---|
| 생성물은 **커밋**한다 | diff를 통해 계약 변화를 리뷰에서 눈으로 확인한다 |
| `generated.ts`는 **수정 금지** | 헤더 주석으로 표시. 수정은 재생성으로 덮어써진다 |
| CI는 **재생성 후 diff가 없음**을 확인한다 | 손으로 편집한 것이 있으면 빌드가 실패한다 |
| `contractVersion`은 **Pydantic에서 파생** | 두 곳에서 따로 쓰면 어긋난다 |

`C12`는 wire 타입을 손으로 쓰지 않는다. 계약이 바뀌면 TS 빌드가 깨진다
(AC-5.1, 제약 `C11`).

---

## 10. 경로 안전성 데이터 (`C4` `skill-io`)

### 10.1 임포트 파이프라인

```
소스 → [STAGING] → 경로 안전성 검사 → L1 strict 검증 → 정적 분석 → 신뢰 게이트 → 원자적 설치
                    ↓ 실패                    ↓ 실패                    ↓ 위험
                  즉시 거부                설치 금지                 명시적 동의
```

**어떤 단계도 건너뛸 수 없다.** 특히 경로 안전성 검사는
**목적지 외 어떤 것도 쓰지 않은 상태로** 완료되어야 한다. 스테이징은
임시 디렉터리이며, 검사가 끝나기 전까지 라이브 경로에는 아무것도 쓰지 않는다.

### 10.2 거부 규칙

| 코드 | 조건 | 근거 |
|---|---|---|
| `path_traversal` | 항목 경로가 `..`를 포함하거나, 정규화 후 스테이징 밖에 위치 | 디렉터리 탈출 |
| `absolute_path` | 항목 경로가 `/` 또는 드라이브 문자로 시작 | 임의 위치 쓰기 |
| `symlink_escape` | 심볼릭 링크의 해석 결과가 스테이징 밖에 위치 | 링크를 통한 탈출 |
| `skill_md_misplaced` | `SKILL.md`가 예상 깊이에 없음 | 스킬이 아니다 |
| `size_exceeded` | 압축 해제 크기 상한 초과 | 디스크 고갈 |
| `file_count_exceeded` | 파일 수 상한 초과 | 자원 고갈 |
| `setuid_bits` | setuid/setgid 비트가 설정됨 | 권한 상승 |
| `unknown_archive_format` | 지원하지 않는 포맷 | 명시적 실패 |

**상한 값은 정책으로 노출한다.** 사용자가 조정한 상한을 넘으면
`size_exceeded`에 실제 값과 상한을 함께 보여준다. 숫자만 던지지 않는다.

### 10.3 `EvalCase.files`의 경로 안전성

평가 케이스의 `files`는 **스킬 소유자가 작성**하므로 임포트와 같은 출처가
아니다. 그러나 스튜디오가 스테이징 밖에 쓰지 않도록 규칙은 필요하다.

```python
def resolve_eval_input(skill_root: Path, relpath: str) -> Path:
    """평가 입력 파일을 스킬 루트 안으로만 해석한다."""
    candidate = (skill_root / relpath).resolve()
    root = skill_root.resolve()
    if not candidate.is_relative_to(root):
        raise PathSafetyError("path_traversal",
                              f"평가 입력 '{relpath}'이(가) 스킬 루트 밖에 있습니다.")
    return candidate
```

심볼릭 링크는 `resolve()` 후 비교하므로 링크를 통한 탈출도 막는다.

---

## 11. JSON Schema 전략

### 11.1 진실 공급원과 파생물

**Pydantic 모델이 유일한 진실 공급원이다** (`D-1`). JSON Schema는 생성물이며
**손으로 편집하지 않는다.** 편집하면 Pydantic과 어긋나고, 어느 쪽이 진실인지
모르게 된다.

### 11.2 `additionalProperties: false`와 이식성 충돌

폐쇄 집합(스펙의 6개 필드)은 JSON Schema에서 `additionalProperties: false`로
표현된다. 그런데 클라이언트 확장 필드(`context` 등)는 **스펙에 없고 그래서
스키마 위반**이다.

| 표면 | 처리 |
|---|---|
| `SkillFrontmatter` | `extra="forbid"` → `additionalProperties: false` |
| 클라이언트 확장 필드 | 파싱은 성공, **분류는 별도 경로** (§4.2) |
| 소비 방법 | 클라이언트는 `clientExtensionFields` 배열을 함께 받아 위험을 판단 |

스키마가 "이것은 스펙이다"라고 말하고, 같은 응답의 다른 필드가
"그러나 이것은 이식성 위험이 있다"고 말한다. **정보를 잃지 않으면서
폐쇄 집합의 이점을 유지**하는 방법이다.

### 11.3 OpenAPI 대 JSON Schema

| 용도 | 사용할 것 | 이유 |
|---|---|---|
| TS 타입 생성 | **JSON Schema** (Pydantic `model_json_schema()`) | 언어 중립. 생성기가 안정적 |
| 외부 문서·도구 제공 | JSON Schema | `additionalProperties` 등 어노성션이 유지됨 |
| REST 문서 | **OpenAPI** (FastAPI 자동 생성) | 파이썬 라우트에서 파생되므로 유지보수 비용 0 |

FastAPI가 OpenAPI를 라우트에서 자동 생성하므로, **스키마를 두 번 정의할
이유가 없다.** OpenAPI는 FastAPI가, JSON Schema는 Pydantic이 각자 자기
근원에서 만든다. 어느 것도 손으로 쓰지 않는다.

### 11.4 스키마 버전과 하위 호환

버전은 **문자열 하나**로 wire에 실린다. 비교는 별도 유틸이 한다 —
`SemVer` 같은 외부 타입에 의존하지 않는다(그것이 없으면 이 문서의 예제가
실행 불가능한 의사코드가 된다).

```python
CONTRACT_VERSION: Final[str] = "1.0.0"


def parse_version(v: str) -> tuple[int, int, int]:
    """'1.2.3' → (1, 2, 3). 형식이 아니면 ValueError."""
    parts = v.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"버전 형식이 아님: {v!r}")
    return (int(parts[0]), int(parts[1]), int(parts[2]))


def is_compatible(client: str, server: str) -> bool:
    """주 버전이 같으면 호환. 부·패치 차이는 무시한다."""
    c_major, _, _ = parse_version(client)
    s_major, _, _ = parse_version(server)
    return c_major == s_major
```

| 변경 유형 | 버전 영향 | 클라이언트 동작 |
|---|---|---|---|
| 필드 추가 (필수 아님) | `minor`↑ | 무시해도 안전 |
| 필드 추가 (필수) | `major`↑ | **거부** |
| 필드 삭제 | `major`↑ | **거부** |
| 필드 의미 변경 | `major`↑ | **거부** |
| 제약 완화 | `minor`↑ | 계속 동작 |
| 제약 강화 | `major`↑ | **거부** |

제약 강화가 `major`인 이유: 이전에 통과하던 스킬이 이제 실패할 수 있다.
클라이언트가 조용히 더 엄격해지는 것은 버전에 hiding되어야 한다.

---

## 12. 모듈 배치 — 250 pure-LOC 상한 준수

이 문서가 정의한 모델은 그 자체로 상한을 초과한다. **모듈 경계를 먼저
확정한다.** 나중에 나누면 순환 import가 생기고, 순환 import는 규칙의 단일
진실 공급원을 깨뜨린다([01. 아키텍처 §2.1](./01-architecture.md#21-단일-진실-공급원-single-source-of-truth)).

**상한: 모듈당 250 pure LOC.**(환경의 `programming` 규약)

### 12.1 `spec-core` (C3)

| 모듈 | 책임 | 대략 LOC |
|---|---|---|
| `spec_core/frontmatter.py` | `SkillFrontmatter`, `RawFrontmatter`, `ClassifiedFrontmatter`, 강제 변환 | ~90 |
| `spec_core/parser.py` | 프런트매터 추출, 오류 4종, 파일 탐색 | ~110 |
| `spec_core/naming.py` | `name` 규칙, NFKC, 유니코드 | ~70 |
| `spec_core/diagnostics.py` | `Diagnostic`, `DiagnosticCode`, `Severity`, `Span`, `QuickFix` | ~120 |
| `spec_core/rules.py` | 규칙 본문 (프로필 무관) | ~180 |
| `spec_core/severity.py` | `_SEVERITY_MAP` 전부 | ~80 |
| `spec_core/extensions.py` | `ExtensionRegistry`, `KeyClassification`, `classify_keys()` | ~110 |
| `spec_core/budgets.py` | 설명 예산 2중, 예약 이름 | ~60 |
| `spec_core/catalog.py` | 카탈로그 스캔 (메모리 효율) | ~80 |

**`rules.py`가 `severity.py`를 import하고, 그 반대는 하지 않는다.**
의존 방향이 한쪽이므로 순환이 생기지 않는다. `rules.py`는 **심각도를
정하지 않고** 코드와 위치만 낸다.

### 12.2 평가 도메인 (C7/C8)

| 모듈 | 책임 | 대략 LOC |
|---|---|---|
| `eval/suite.py` | `EvalSuite`, `EvalCase`, 반올림 | ~70 |
| `eval/workspace.py` | 워크스페이스 트리 기록 | ~100 |
| `eval/runner.py` | A/B 오케스트레이션, 격리, 취소 | ~150 |
| `eval/grading.py` | `Grading`, `AssertionResult`, verdict | ~90 |
| `eval/checkers.py` | 결정론적 체커 레지스트리 | ~160 |
| `eval/judge.py` | LLM 판정 + 증거 강제 | ~90 |
| `eval/benchmark.py` | `Benchmark`, `MetricStats`, 저수량 상태 | ~90 |
| `eval/analysis.py` | 4종 패턴 분석 | ~80 |
| `adapters/protocol.py` | `RunAdapter`, `AdapterCapabilities` | ~60 |
| `adapters/mock.py` | `MockAdapter` | ~90 |

**`checkers.py`가 `judge.py`를 import하지 않는다.** 채점 파이프라인
순서는 `grading.py`가 소유한다(§7.5). 그래야 "결정론적 우선"이
구조로 보장되고 AC-2.8의 테스트가 의미를 갖는다.

### 12.3 IPC 계약 (C9)

| 모듈 | 책임 | 대략 LOC |
|---|---|---|
| `ipc/envelope.py` | `Envelope[T]`, `RpcError`, `Handshake` | ~80 |
| `ipc/stream.py` | `StreamEvent`, `StreamEventType` | ~60 |
| `ipc/params.py` | `parse_params()` — `Any` → 구체 타입 검증 | ~70 |
| `ipc/methods/spec.py` | `C3` 관련 메서드 파라미터·응답 | ~90 |
| `ipc/methods/io.py` | `C4` 관련 | ~80 |
| `ipc/methods/testing.py` | `C5`·`C6`·`C7` 관련 | ~120 |
| `ipc/methods/packaging.py` | `C10`·`C11` 관련 | ~90 |

**`params.py`의 존재 이유.** §2.4에서 `Any`를 경계 직전에만 허용한다고
했다. `parse_params()`가 그 경계다. 메서드 핸들러는 `Any`를 **직접 받지
않고** `parse_params()`가 검증한 구체 모델을 받는다. 이 경계가 없으면
`D-4`(경계 양방향 검증)가 무의미해진다.

### 12.4 패키징·설치 (C10/C11)

| 모듈 | 책임 | 대략 LOC |
|---|---|---|
| `packager/tarbuild.py` | 결정적 tar.gz (PAX 비활성, LC_ALL=C) | ~140 |
| `packager/manifest.py` | `ArtifactManifest`, `FileDigest` | ~90 |
| `packager/digest.py` | `TreeDigest` 알고리즘 | ~70 |
| `installer/targets.py` | 대상 매트릭스, 경로 조립 | ~90 |
| `installer/atomic.py` | 임시 디렉터리 + 검증 + rename | ~110 |
| `installer/visibility.py` | 클라이언트 탐색 재현 | ~120 |
| `installer/precedence.py` | 우선순위, 섀도잉 탐지 | ~80 |

### 12.5 순환 금지 규칙

| 금지 | 대신 |
|---|---|
| `rules.py` → `severity.py` | 허용 (단방향) |
| `severity.py` → `rules.py` | **금지** |
| `checkers.py` ↔ `judge.py` | **금지** — `grading.py`가 조율 |
| `ipc/envelope.py` → `ipc/methods/*` | **금지** — `params.py`가 중개 |
| `ipc/methods/*` → `spec_core/*` | **금지** — 파라미터 모델은 `ipc/`가 소유 |

**CI 검사:** `import-linter` 또는 `grimp`로 위 금지 규칙을 단언한다.
위반하면 빌드가 실패한다. 이것은 아키텍처 문서 §10의 "규칙의 단일 진실
공급원"을 **실행 가능한 문턱**으로 만드는 장치다 — `C4` Rust LOC 예산
검사(`T5-4`)와 같은 취지다.

---

## 13. 저장 형식 요약

| 파일 | 소유 | 작성자 | 스키마 | 절 |
|---|---|---|---|---|
| `SKILL.md` | 사용자 | 사람 | `SkillDocument` | §3.4 |
| `evals/evals.json` | 사용자 | **사람** (유일) | `EvalSuite` | §7.1 |
| `evals/files/*` | 사용자 | 사람 | — | — |
| `*-workspace/iteration-N/eval-*/with_skill/timing.json` | 도구 | `C7` | `Timing` | §7.3 |
| `…/with_skill/grading.json` | 도구 | `C7` | `Grading` | §7.3 |
| `…/without_skill/…` | 도구 | `C7` | 동일 | §7.2 |
| `…/old_skill/…` | 도구 | `C7` | 동일 | §7.2 |
| `…/feedback.json` | 사람 | 사람 | `Feedback` | §7.6 |
| `…/benchmark.json` | 도구 | `C7` | `Benchmark` | §7.9 |
| `manifest.json` (아카이브 외부) | 도구 | `C10` | `ArtifactManifest` | §8.1 |
| `extensions.json` | 도구 | `C10` 배포 | `ExtensionRegistry` | §4.3 |
| 캐시 인덱스 | 도구 | `C2` | (버전 스탬프) | §1.3 |

공식 문서는 **`evals/evals.json`만 사람이 작성한다**고 명시하고 나머지는
"에이전트·스크립트 또는 사람이 생성한다"고 한다 (PRD §4.6). 위 표는 이를
정확히 반영한다. 특히 `timing.json`은 공식 문서가 "이 값은 어디에도 저장되지
않으므로 즉시 기록하라"고 경고하는데, `C7`이 **실행의 부수 효과로** 기록하므로
사용자가 놓칠 수 없다.

---

## 14. 검증

| 데이터 규칙 | 검증 방법 | 명령 | AC |
|---|---|---|---|
| 반올림 항등 | `D-TEST-3` | `pytest tests/test_roundtrip.py -k roundtrip` | AC-1.3 |
| 경계값 64/1024/500 | `D-TEST-4` | `pytest tests/test_limits.py` | AC-1.2 |
| 유니코드 이름 허용 | `D-TEST-2` | `pytest tests/test_name.py -k unicode` | AC-1.4 |
| 프로필 심각도 분기 | `D-TEST-6` | `pytest tests/test_profiles.py` | AC-1.5 |
| 파스 오류 4종 | `D-TEST-5` | `pytest tests/test_parser.py -k error` | AC-1.6 |
| unquoted 콜론 복구 | — | `pytest tests/test_recovery.py` | AC-1.7 |
| 설명 예산 2중 | `D-TEST-7` | `pytest tests/test_budgets.py` | AC-1.3b |
| 예약 이름 | — | `pytest tests/test_reserved.py` | AC-1.3c |
| 확장 분류 3분류 | — | `pytest tests/test_extensions.py` | AC-1.3a |
| 차분 준수 | §14 | `pytest tests/conformance/test_vs_skills_ref.py` | AC-1.9 |
| 카탈로그 스캔 성능·메모리 | `D-TEST-8` | `pytest tests/test_catalog.py --durations=5` | AC-1.10 |
| body 실행 표면 탐지 | §6.3 | `pytest tests/test_analyzer.py -k body_shell` | AC-2.1a–2.1d |
| 결정론적 우선순위 | §7.5 | `pytest tests/test_grading.py -k no_llm` | AC-2.8 |
| 증거 없는 PASS 강등 | §7.4 | `pytest tests/test_grading.py -k evidence` | AC-2.9 |
| `n<2`에서 stddev None | §7.9 | `pytest tests/test_benchmark.py -k low_n` | AC-2.7 |
| 재현성(바이트 동일) | §8.2 | `pytest tests/test_packager.py -k reproducible` | AC-3.1 |
| 경로 트래버설 차단 | §10.2 | `pytest tests/test_pathsafety.py` | AC-4.1/4.2 |
| 계약 생성 일관성 | §9.5 | `make contract-check && tsc --noEmit` | AC-5.1 |

**수동 검출이 필요한 항목.** `D-TEST-2`(유니코드 이름)는 자동 테스트로
충분히 검증된다. 반면 `parse_yaml_error`의 **메시지 품질**과
`client_extension_field`의 **안내 문구**는 사람이 읽어야 한다. 자동 테스트는
"메시지가 존재한다"만 보장하고 "메시지가 사용자를안내한다"는 건 보장하지 않는다.
[03. UI 디자인 §12](./03-ui-design.md#12-오류--엣지-상태-카탈로그)가 이 수동 검토 항목을
화면 단위로 정의한다.

---

## 15. 열린 이슈

| ID | 이슈 | 영향 | 처리 |
|---|---|---|---|
| `O-1` | **스펙이 JSON Schema를 배포하지 않는다.** 규칙은 `skills-ref` demo 코드에만 존재하며 그 라이브러리는 스스로 production 용도를 거부한다 | 스펙이 바뀌면 우리 검증기가 조용히 뒤처진다 | 차분 준수 하네스를 CI에서 돌려 **드리프트를 빨간 빌드로 바꾼다** (AC-1.9). `skills-ref`는 **개발 의존성으로만** 고정 (제약 `C3`) |
| `O-2` | 유니코드 `name`에서 스펙 산문과 참조 구현이 불일치 | 어느 쪽이 맞는가 | 참조 구현을 따르고 `spec_ambiguity` 진단으로 노출. 조용히 선택하지 않는다 |
| `O-3` | 어댑터가 `total_tokens`·`duration_ms`를 보고하지 않을 수 있음 | `timing.json` 불완전 | `AdapterCapabilities`로 선언. `None`으로 기록하고 0을 넣지 않는다 |
| `O-4` | 레지스트리 갱신 책임 | 새 클라이언트 필드를 놓치면 오탐 | 레지스트리에 `verified_against` 버전을 기록. `C4`가 기여하고 `C3`이 소비 |
| `O-5` | `metadata` 최상위 키와 스펙 필드명 충돌 | 조용한 오해 | `metadata` 직렬화 시 스펙·클라이언트 필드명 키를 경고 |
| `O-6` | 캐시 무효화 시점이 파일시스템 이벤트에 의존 | 오래된 검증 결과 표시 | 스탬프 불일치 시 폐기. 이벤트는 최적화일 뿐 유일한 근거가 아니다 |
| `O-7` | 유니코드 그래프메 클러스터 정규화 규칙이 스펙에 없음 | 시각적으로 같은 이름이 불일치 판정 | NFKC는 사양상 표준이나 클러스터 처리는 미정. `known-divergence`에 기록 |

---

**다음 문서** — [03. UI 디자인](./03-ui-design.md)은 이 문서의
`Diagnostic`·`CapabilityReport`·`Grading`·`VisibilityReport`를 화면에서
어떻게표현하는지 설계한다.
