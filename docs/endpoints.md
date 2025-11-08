# Spokit Backend Endpoints

> ✅ 모든 API 응답은 실패 시 다음 포맷을 사용합니다.
>
> ```json
> {
>   "error": "Invalid request",
>   "message": "자세한 설명",
>   "code": "ERROR_CODE"
> }
> ```
>
> HTTP 상태 코드는 상황에 따라 `400`(검증 실패), `401`(인증 필요), `403`(권한 부족), `404`(존재하지 않음) 등을 반환합니다.
> 모든 성공 응답은 `{"message": "...", "data": ...}` 형태를 사용하며, 일부 삭제 등은 `data` 없이 메시지만 내려줍니다.

## 인증/권한 요약
- 기본 인증: JWT(Access/Refresh). `Authorization: Bearer <token>` 헤더 사용.
- 명시적으로 `AllowAny` 로 표시된 엔드포인트만 비로그인 접근 가능.
- `visibility` 쿼리는 기본 목록 엔드포인트(`/api/bikes/`, `/api/bike-builds/`)에서만 의미가 있으며, 로그인 사용자가 자신의 리소스를 필터링할 때 활용합니다.

### 비로그인 접근 가능 API
- `POST /api/auth/jwt/create/`, `POST /api/auth/jwt/refresh/`, `POST /api/auth/google/`
- `GET /api/bikes/<uuid>/detail/` (공개 자전거만 조회 가능)
- `GET /api/posts/`, `GET /api/posts/<slug>/`
- `GET /api/question-set/`
- `GET /api/schema/`, `/api/docs/`, `/api/redoc/`

> OpenAPI 스키마에서는 위 엔드포인트들에 `Public` 태그가 추가되어 있어 쉽게 필터링할 수 있습니다.

---

## 1. 인증 & 사용자
| Method | Path | 권한 | 설명 |
| --- | --- | --- | --- |
| POST | `/api/auth/jwt/create/` | 누구나 | 이메일/비밀번호로 액세스·리프레시 토큰 발급 |
| POST | `/api/auth/jwt/refresh/` | 누구나 | 리프레시 토큰으로 액세스 토큰 재발급 |
| POST | `/api/auth/google/` | 누구나 | Google `id_token` 기반 로그인/회원가입 |
| GET | `/api/me/profile/` | 로그인 | 내 프로필 조회 |
| PATCH | `/api/me/profile/` | 로그인 | 닉네임, 소개 등 수정 |
| GET | `/api/me/profile/stats/` | 로그인 | 신청서 상태 통계 |
| GET | `/api/me/submissions/` | 로그인 | 내 신청서 목록 (`count`, `results`) |
| GET | `/api/me/submissions/<uuid>/` | 로그인 | 내 신청서 상세 |
| PATCH | `/api/me/submissions/<uuid>/` | 로그인 | 내 신청서 부분 수정 |

- `/api/me/submissios/` 는 `/api/me/submissions/` 의 오타 호환 라우트입니다.

---

## 2. 자전거(Bikes)
### 2.1 내 자전거 보기
- `GET /api/bikes/?visibility=<public|private>` *(로그인)*
  - 자신의 자전거 목록을 반환합니다. `visibility` 를 생략하면 전체가 내려옵니다.

### 2.2 다른 사용자 자전거/빌드 보기
- `GET /api/users/<user_uuid>/bikes/`
  - 로그인 필요. 해당 사용자의 공개 자전거만 반환합니다.
  - 각 자전거에는 공개 빌드의 `id`/`title`을 담은 `build_names` 배열이 포함됩니다.
- `GET /api/users/<user_uuid>/bike-builds/`
  - 로그인 필요. 해당 사용자의 공개 빌드만 반환합니다.
- `GET /api/bikes/?owner=<user_uuid>` *(하위 호환용)*

### 2.3 세부 엔드포인트
| Method | Path | 권한 | 설명 |
| --- | --- | --- | --- |
| GET | `/api/bikes/<uuid>/` | 조건부* | 자전거 상세. 소유자만 비공개 자전거 확인 가능 |
| GET | `/api/bikes/<uuid>/builds/` | 로그인 | 소유자는 전체, 타인은 공개 빌드만 확인 |
| POST | `/api/bikes/` | 로그인 | 자전거 등록 (요청 사용자가 자동 소유자) |
| PATCH/PUT | `/api/bikes/<uuid>/` | 소유자 | 자전거 수정 |
| DELETE | `/api/bikes/<uuid>/` | 소유자 | 자전거 삭제 |

- *비로그인은 공개 자전거에 한해 상세 조회가 가능합니다.

---

## 3. 자전거 빌드(Bike Builds)
- 모든 빌드 관련 엔드포인트는 로그인 필요입니다.
- 자신의 빌드 목록: `GET /api/bike-builds/?visibility=<public|private>`
  - `visibility` 생략 시 전체, `public`/`private` 로 필터 가능.
- 타인의 공개 빌드 목록: `GET /api/users/<user_uuid>/bike-builds/`
- 특정 자전거의 빌드 목록: `GET /api/bikes/<bike_uuid>/builds/`
- 빌드 상세: `GET /api/bike-builds/<uuid>/` (공개 빌드 또는 소유자)
- 빌드 수정: `PATCH /api/bike-builds/<uuid>/` (소유자)
- 빌드 생성: `POST /api/bike-builds/` (소유자) — 요청 본문 핵심 필드
  ```json
  {
    "base_bike": "<bike_uuid>",
    "title": "Midnight Track Setup",
    "components": {
      "frame_setup": ["Engine 11 Vortex"],
      "wheel": ["Phil Wood hub", "H Plus Son rim"],
      "drivetrain": ["Miche Primato crank", "17T cog", "Dura-Ace lockring"],
      "cockpit": ["Nitto B123"],
      "seat": ["Thomson Elite"],
      "brake": ["Tektro R540"],
      "etc": ["Garmin mount"]
    },
    "note": "도심 야간 주행 세팅",
    "is_public": true
  }
  ```
  - `components`는 **카테고리 → 문자열 리스트** 구조로 통일됩니다. 허용 카테고리: `frame_setup`, `wheel`, `cockpit`, `drivetrain`, `seat`, `brake`, `etc`.
  - 각 카테고리는 공백 제거 후 남는 문자열만 저장되며, 최소 3개 이상의 카테고리가 채워져야 합니다.
  - 문자열 한 개만 보낼 경우 자동으로 리스트로 승격됩니다.
  - 허용되지 않은 카테고리를 넘기면 400 오류(`{"components": {"unknown": "허용되지 않은 카테고리입니다."}}`)가 발생합니다.

| Method | Path | 설명 |
| --- | --- | --- |
| GET | `/api/bike-builds/` | 내 빌드 목록 (visibility 필터 지원) |
| GET | `/api/users/<uuid>/bike-builds/` | 특정 사용자의 공개 빌드 목록 |
| GET | `/api/bike-builds/<uuid>/` | 빌드 상세 (소유자 또는 공개) |
| POST | `/api/bike-builds/` | 빌드 생성 (소유 자전거에 한함) |
| PATCH | `/api/bike-builds/<uuid>/` | 빌드 일부 수정 (소유자) |

---

## 4. 소개 신청(Submission)
- 모든 신청 API는 로그인 사용자 전용입니다.

| Method | Path | 설명 |
| --- | --- | --- |
| GET | `/api/submissions/` | 내 신청서 목록 |
| POST | `/api/submissions/` | 신청서 생성 (`title`, `story_blocks`, `build_snapshot` 등) |
| GET | `/api/submissions/<uuid>/` | 신청서 상세 |
| PATCH | `/api/submissions/<uuid>/` | 신청서 일부 수정 (PUT 미지원) |
| DELETE | `/api/submissions/<uuid>/` | 신청서 삭제 |
| POST | `/api/submissions/<uuid>/submit/` | 초안 → 접수(`submitted`) 전환 |
| POST | `/api/submissions/<uuid>/resubmit/` | 반려 → 재신청(`resubmitted`) (Body: `comment` 선택) |

- 반려된 신청서는 `reason_code`(사전 정의된 카테고리)와 `reason_detail`(추가 설명)로 사유가 전달됩니다.

### 4.1 운영진 워크플로우 `/api/submission-workflow/<uuid>/`
| Method | Action | 권한 | 설명 |
| --- | --- | --- | --- |
| POST | `/review/` | Staff 이상 | `in_review` 상태로 전환 |
| POST | `/approve/` | Editor/Admin | `approved` 상태로 전환 |
| POST | `/reject/` | Editor/Admin | 반려 처리, Body: `reason_code`, `reason_detail`(선택) |

- 모든 상태 전이는 `SubmissionStatusLog` 에 남습니다.

### 4.2 질문 세트 `/api/question-set/`
- `GET /api/question-set/?version=<id>` 로 질문 세트를 조회합니다.
- `version` 생략 시 기본 버전(`v1_3`)이 사용되며, 응답에는 `questions`, `groups`, `metadata` 등이 포함됩니다.

---

## 5. 게시글(Posts)
- 비로그인은 발행된 게시글만 조회할 수 있고, 작성/수정/삭제는 Editor 이상 스태프만 가능합니다.

| Method | Path | 권한 | 설명 |
| --- | --- | --- | --- |
| GET | `/api/posts/` | 누구나 | 게시글 목록. 비스태프는 발행(`published`)만 확인 |
| GET | `/api/posts/<slug>/` | 누구나 | 게시글 상세 (발행 글 조회 시 `view_count` 1 증가) |
| POST | `/api/posts/` | Editor/Admin | 게시글 생성 |
| PATCH | `/api/posts/<slug>/` | Editor/Admin | 게시글 수정 |
| DELETE | `/api/posts/<slug>/` | Editor/Admin | 게시글 삭제 |

| Method | Path | 권한 | 설명 |
| --- | --- | --- | --- |
| POST | `/api/posts/<slug>/like/` | 로그인 | 좋아요 토글 응답: `liked`, `like_count` |
| POST | `/api/posts/<slug>/comments/` | 로그인 | 댓글 작성 (`content` 필드) |

---

## 6. 스튜디오(운영진)
| Method | Path | 권한 | 설명 |
| --- | --- | --- | --- |
| GET | `/api/studio/dashboard/` | Staff | 접수/검토 중 신청 요약 |
| GET | `/api/studio/submissions/<uuid>/` | Staff | 신청 상세 조회 |
| PATCH | `/api/studio/submissions/<uuid>/` | Staff | 신청 일부 수정 |
| GET | `/api/studio/staff/<uuid>/` | Admin | 운영진 프로필 조회 |
| PATCH | `/api/studio/staff/<uuid>/` | Admin | 운영진 정보 수정 |

---

## 7. 문서 & 스키마
| Path | 설명 |
| --- | --- |
| `GET /api/schema/` | OpenAPI 스키마(JSON) |
| `GET /api/docs/` | Swagger UI |
| `GET /api/redoc/` | ReDoc 문서 |

---

최근 업데이트: 2025-10-21
