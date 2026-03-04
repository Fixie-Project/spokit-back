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
> 모든 성공 응답은 `{"message": "...", "data": ...}` 형태를 원칙으로 사용하며, 토글/삭제/일부 내부 운영 API는 예외적으로 `data` 없이 메시지만 반환할 수 있습니다.

## 인증/권한 요약
- 기본 인증: JWT(Access/Refresh). `Authorization: Bearer <token>` 헤더 사용.
- 현재 토큰 발급은 `POST /api/auth/google/` 만 활성화되어 있습니다. 이메일/비밀번호 기반 JWT 엔드포인트는 비활성화 상태입니다.
- 비로그인 접근은 아래 **Public 엔드포인트** 목록과 공개 리소스 조회(예: 공개 빌드 상세)에 한해 가능합니다.
- `visibility` 쿼리는 `/api/me/bike-builds/`에서만 의미가 있으며, 로그인 사용자가 자신의 리소스를 필터링할 때 활용합니다.

### 비로그인 접근 가능 API
- `POST /api/auth/google/`
- `GET /api/users/<uuid>/profile/`
- `GET /api/public/bike-builds/`
- `GET /api/posts/`, `GET /api/posts/<slug>/`
- `GET /api/posts/popular/`
- `GET /api/bike-builds/<uuid>/` (공개 빌드만)
- `GET /api/question-set/`
- `GET /api/search/`
- `GET /api/home/`
- `GET /api/schema/`, `/api/docs/`, `/api/redoc/`

> OpenAPI 스키마에 노출되는 주요 공개 엔드포인트에는 `Public` 태그가 추가되어 있어 쉽게 필터링할 수 있습니다.  
> 이 태그는 문서 분류용 라벨이며, 권한은 각 API의 permission 설정을 기준으로 판단합니다.

---

## 1. 인증 & 사용자
| Method | Path | 권한 | 설명 |
| --- | --- | --- | --- |
| POST | `/api/auth/google/` | 누구나 | Google `id_token` 기반 로그인/회원가입 |
| GET | `/api/me/profile/` | 로그인 | 내 프로필 조회 |
| PATCH | `/api/me/profile/` | 로그인 | 사용자명, 소개 등 수정 |
| GET | `/api/users/<uuid>/profile/` | 누구나 | 사용자 공개 프로필 조회 |
| GET | `/api/me/profile/stats/` | 로그인 | 신청서 상태 통계 |
| GET | `/api/me/submissions/` | 로그인 | 내 신청서 목록 (`count`, `results`) |
| GET | `/api/me/submissions/<uuid>/` | 로그인 | 내 신청서 상세 |
| PATCH | `/api/me/submissions/<uuid>/` | 로그인 | 내 신청서 부분 수정 |

### Deprecated/Removed
- `POST /api/auth/jwt/create/`, `POST /api/auth/jwt/refresh/` (현재 비활성화)

---

## 2. 자전거(Bikes)
Bikes는 프레임 단위로 빌드를 묶어 관리하기 위한 엔티티이며, 마이페이지 “프레임별” 탭에서 주로 사용됩니다.
공개 여부는 BikeBuild 단위에서만 의미가 있습니다.
### 2.1 내 자전거 보기 (마이페이지 · 프레임별)
- `GET /api/me/bikes/` *(로그인)*
  - 내 자전거(프레임) 목록을 반환합니다.
  - 마이페이지 “프레임별” 탭에서 사용합니다.

### 2.2 공개 자전거 보기
- 현재 공개 자전거 엔드포인트는 제공하지 않습니다.
- 공개 탐색은 빌드 단위(`/api/public/bike-builds/`)로만 제공합니다.

### 2.3 자전거 세부 엔드포인트
| Method | Path | 권한 | 설명 |
| --- | --- | --- | --- |
| GET | `/api/me/bikes/<uuid>/` | 소유자 | 내 자전거 상세(비공개 포함) |
| PATCH/PUT | `/api/me/bikes/<uuid>/` | 소유자 | 내 자전거 수정 |
| DELETE | `/api/me/bikes/<uuid>/` | 소유자 | 내 자전거 삭제 |
| POST | `/api/me/bikes/` | 로그인 | 자전거(프레임) 등록 |

> 비로그인은 자전거 상세를 직접 조회하지 않으며, 공개 빌드 상세(`/api/bike-builds/<uuid>/`)로 접근합니다.

### Deprecated/Removed
- `/api/bikes/`, `/api/bikes/<uuid>/`, `/api/bikes/<uuid>/builds/`
- `/api/users/<user_uuid>/bikes/`
- `/api/public/bikes/`



---

## 3. 자전거 빌드(Bike Builds)
BikeBuild는 아카이브/탐색/공유의 중심이 되는 콘텐츠 단위입니다.
### 3.1 내 빌드 보기 (마이페이지 · 빌드별)
- `GET /api/me/bike-builds/?visibility=<public|private>&ordering=<created_at|-created_at|title|-title>` *(로그인)*
  - 내 빌드 목록을 반환합니다. `visibility` 생략 시 전체가 내려옵니다.
  - 마이페이지 “빌드별” 탭에서는 기본적으로 `ordering=-created_at` 을 사용합니다.
  - 응답에는 `like_count`, `is_liked`가 포함됩니다.

### 3.2 공개 빌드 아카이브 (탐색)
- `GET /api/public/bike-builds/?limit=<n>&offset=<n>` *(비로그인)*
  - 전체 공개 빌드 목록(아카이브)입니다. 기본 `limit=10`, 최대 `50`.
  - 응답 `data`는 `{count, next, previous, results}` 구조입니다.
  - 응답에는 `like_count`, `is_liked`가 포함됩니다.

### 3.3 빌드 상세
- `GET /api/bike-builds/<uuid>/` *(비로그인 가능, 조건부)*
  - 접근 규칙: 공개 빌드는 누구나, 비공개는 소유자만 조회 가능합니다.
  - 소유자는 동일 경로에서 `PATCH/DELETE`도 가능하며, 내 리소스 경로(`/api/me/bike-builds/<uuid>/`) 사용을 권장합니다.
  - 응답에는 `like_count`, `is_liked`가 포함됩니다.

### 3.4 빌드 수정/생성 (내 리소스)
- `GET /api/me/bike-builds/<uuid>/` *(소유자)* — 내 빌드 상세
- `POST /api/me/bike-builds/` *(로그인)* — 빌드 생성 (내 자전거에 한함) — 요청 본문 핵심 필드
- `PATCH /api/me/bike-builds/<uuid>/` *(소유자)* — 빌드 일부 수정
- `DELETE /api/me/bike-builds/<uuid>/` *(소유자)* — 빌드 삭제
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
    "is_public": true,
    "main_image": "<base_image_id>",
    "images": ["<base_image_id>", "<base_image_id>"]
  }
  ```
  - `components`는 **카테고리 → 문자열 리스트** 구조로 통일됩니다. 허용 카테고리: `frame_setup`, `wheel`, `cockpit`, `drivetrain`, `seat`, `brake`, `etc`.
  - 각 카테고리는 공백 제거 후 남는 문자열만 저장되며, 최소 3개 이상의 카테고리가 채워져야 합니다.
  - 문자열 한 개만 보낼 경우 자동으로 리스트로 승격됩니다.
  - 허용되지 않은 카테고리를 넘기면 400 오류(`{"components": {"unknown": "허용되지 않은 카테고리입니다."}}`)가 발생합니다.
  - `images`는 최대 5장. 초과 시 400.

| Method | Path | 설명 |
| --- | --- | --- |
| GET | `/api/me/bike-builds/` | 내 빌드 목록 (쿼리: visibility, ordering) |
| GET | `/api/public/bike-builds/` | 전체 공개 빌드 목록 |
| GET | `/api/bike-builds/<uuid>/` | 빌드 상세 (소유자 또는 공개) |
| GET | `/api/me/bike-builds/<uuid>/` | 내 빌드 상세 |
| POST | `/api/me/bike-builds/` | 빌드 생성 (소유 자전거에 한함) |
| PATCH | `/api/me/bike-builds/<uuid>/` | 빌드 일부 수정 (소유자) |
| DELETE | `/api/me/bike-builds/<uuid>/` | 빌드 삭제 (소유자) |
| POST | `/api/bike-builds/<uuid>/like/` | 빌드 좋아요 토글 |

### Deprecated/Removed
- `/api/bike-builds/` (내 빌드 목록 에일리어스)
- `/api/bikes/<bike_uuid>/builds/`

### Planned (v0.3)
- `/api/users/<user_uuid>/bike-builds/` (공개 빌드만, AllowAny 예정)

---

## 4. 소개 신청(Submission)
- 모든 신청 API는 로그인 사용자 전용입니다.
- 이미지 첨부는 각 `story_blocks[].images` 배열로 전달/조회합니다. 상위 레벨 `images` 필드는 요청·응답 모두 포함되지 않습니다.

| Method | Path | 설명 |
| --- | --- | --- |
| GET | `/api/submissions/` | 내 신청서 목록 |
| POST | `/api/submissions/` | 신청서 생성 (`title`, `story_blocks`, `build_snapshot` 등) |
| GET | `/api/submissions/<uuid>/` | 신청서 상세 |
| PATCH | `/api/submissions/<uuid>/` | 신청서 일부 수정 (초안/반려 상태만) |
| DELETE | `/api/submissions/<uuid>/` | 신청서 삭제 (초안/반려 상태만) |
| POST | `/api/submissions/<uuid>/submit/` | 초안 → 접수(`submitted`) 전환 |
| POST | `/api/submissions/<uuid>/resubmit/` | 반려 → 재신청(`resubmitted`) (Body: `comment` 선택) |
| POST | `/api/submissions/<uuid>/validate/` | 제출 가능 여부 확인 |

- `build_id`(내 빌드 선택) 또는 `new_build_payload`(새 자전거+빌드 생성) 중 하나만 사용 가능합니다.
- 둘 다 없으면 `build_snapshot` 제공이 필요합니다.
- `build_id`는 본인 소유 빌드만 허용됩니다.
- `new_build_payload` 구조: `bike: {frame_name, name?}`, `build: {title, components, note, is_public}`
- `title`은 선택이며, 비우면 `라이더명 - 빌드명` 형식으로 자동 생성됩니다.
- 목록 응답 `results`는 `id`, `title`, `status`, `bike_frame`, `build_title`, `created_at`, `updated_at` 필드만 포함합니다.
- 반려된 신청서는 `reason_code`(사전 정의된 카테고리)와 `reason_detail`(추가 설명)로 사유가 전달됩니다.
- 수정/삭제 허용 상태: `draft`, `rejected`. 그 외 상태에서는 `INVALID_STATUS` 오류가 반환됩니다.

### 4.1 운영진 워크플로우 `/api/submission-workflow/<uuid>/`
| Method | Action | 권한 | 설명 |
| --- | --- | --- | --- |
| POST | `/review/` | Staff 이상 | `in_review` 상태로 전환 |
| POST | `/approve/` | Editor/Admin | `approved` 상태로 전환 |
| POST | `/reject/` | Editor/Admin | 반려 처리, Body: `reason_code`, `reason_detail`(선택) |

- 모든 상태 전이는 `SubmissionStatusLog` 에 남습니다.

### 4.2 질문 세트 `/api/question-set/`
- `GET /api/question-set/?version=<id>` 로 질문 세트를 조회합니다.
- `version` 생략 시 기본 버전(`v1_6`)이 사용되며, 응답에는 `questions`, `groups`, `metadata` 등이 포함됩니다.

---

## 5. 게시글(Posts)
- 비로그인은 발행된 게시글만 조회할 수 있고, 작성/수정/삭제는 Editor 이상 스태프만 가능합니다.

| Method | Path | 권한 | 설명 |
| --- | --- | --- | --- |
| GET | `/api/posts/` | 누구나 | 게시글 목록. 비스태프는 발행(`published`)만 확인 |
  - `?q=` 파라미터로 제목/부제/본문/브랜드에 키워드 검색 가능 |
  - `?limit=<n>&offset=<n>` 지원 (기본 `limit=9`, 최대 `30`)
  - 응답 `data`: `{count, next, previous, results}` (`results`는 `PostListSerializer` 배열)
  - 응답(`PostListSerializer`): `id`, `author`, `slug`, `main_title`, `sub_title`, `thumbnail_image`, `created_at`, `is_editor_pick`, `tags`, `like_count`, `comment_count`(annotate), `is_liked`(로그인 시 사용자 기준, 미로그인 `false`) |
| GET | `/api/posts/<slug>/` | 누구나 | 게시글 상세 (발행 글 조회 시 `view_count` 1 증가) |
| GET | `/api/posts/popular/` | 누구나 | 좋아요+댓글 기준 Top 3 발행 글 |
  - 응답 `data`: `{count, results}` |

| Method | Path | 권한 | 설명 |
| --- | --- | --- | --- |
| POST | `/api/posts/<slug>/like/` | 로그인 | 좋아요 토글 응답: `liked`, `like_count` |
| POST | `/api/posts/<slug>/comments/` | 로그인 | 댓글 작성 (`content` 필드) — 비스태프는 발행 글에만 가능 |
| PATCH | `/api/posts/<slug>/comments/<uuid:comment_id>/` | 작성자 | 본인 댓글 일부 수정 |
| DELETE | `/api/posts/<slug>/comments/<uuid:comment_id>/` | 작성자 | 본인 댓글 삭제 |

---

## 6. 스튜디오(운영진)
| Method | Path | 권한 | 설명 |
| --- | --- | --- | --- |
| GET | `/api/studio/dashboard/` | Staff | 접수/검토 중 신청 요약 |
| GET | `/api/studio/posts/` | Editor/Admin | 게시글 목록(상태/검색/정렬) |
| POST | `/api/studio/posts/` | Editor/Admin | 게시글 생성(신청서 없이도 가능, 있으면 approved여야 함) |
| GET | `/api/studio/posts/<slug>/` | Editor/Admin | 게시글 상세 조회 |
| PATCH | `/api/studio/posts/<slug>/` | Editor/Admin | 게시글 일부 수정(작성/검토/발행 등) |
| DELETE | `/api/studio/posts/<slug>/` | Editor/Admin | 게시글 삭제 |
| GET | `/api/studio/submissions/` | Staff | 신청 목록(상태 필터 지원) |
| GET | `/api/studio/submissions/<uuid>/` | Staff | 신청 상세 조회 *(submitted이면 자동 in_review 전환)* |
| PATCH | `/api/studio/submissions/<uuid>/` | Staff | 신청 일부 수정 |
| PATCH | `/api/studio/submissions/<uuid>/status/` | Staff | 신청 상태만 변경 |
| GET | `/api/studio/staff/<uuid>/` | Admin | 운영진 프로필 조회 |
| PATCH | `/api/studio/staff/<uuid>/` | Admin | 운영진 정보 수정 |

### `/api/studio/dashboard/` 응답 필드 (확장)
- 응답: `message/data` 래퍼, `data`에 아래 필드 포함
- 기본 제공: `total_pending`, `total_posting`, `pending`, `posting` (생성일 내림차순)
  - `pending`: submitted/in_review, `posting`: approved(기획 승인 완료)
- 요약 리스트: `pending_top`, `posting_top` (최대 5건 기본, `?limit=<n>`으로 1~50 조정)
- 신청 상태 집계: `status_counts` (`status` → 건수 맵)
- 게시글 상태 집계: `post_status_counts`, `total_published_posts`, `total_working_posts`
- 추가 카운트: `total_draft_posts`, `total_rejected_submissions`, `total_pending_submissions`
- 작업 중인 글: `working_posts` (상태: `draft|review`, 최신 수정순, 최대 `limit`건)
- 메타: `stats_last_updated` (서버 기준 타임스탬프)

### `/api/studio/posts/` (운영진)
- 쿼리: `status=<draft|review|published>`, `q=<keyword>`, `ordering=<created_at|-created_at|updated_at|-updated_at|published_at|-published_at>`
- 응답: `message/data` 래퍼, `data`는 `PostStudioSerializer` 배열 — 퍼블릭 제한 없이 모든 상태 노출, 조회수 증분 없음.
- POST: `PostWriteSerializer`로 생성, 연결된 신청서가 있으면 `approved` 상태여야 하며, 신청서 없이도 생성 가능.

### `/api/studio/posts/<slug>/`
- GET: `message/data` 래퍼, `data`는 `{ "post": ... }`, 상태 무관, 조회수 증분 없음.
- PATCH: `PostWriteSerializer`로 일부 수정. 상태가 `published`로 바뀌면 연동된 신청서가 `approved→published`로 전환됨.
- DELETE: `message`만 반환 (data 없음)

### `/api/studio/submissions/`
- 목록 응답: `message/data` 래퍼, `data`는 미리보기 전용 필드(`SubmissionPreviewSerializer`)
  - `id`, `title`, `status`, `created_at`, `updated_at`
  - `rider`: id/username/riding_since/region/intro/sns_link
  - `bike_frame`: 신청서에 연결된 자전거 프레임명 (없으면 null)
  - `build_title`: 신청서에 연결된 빌드 이름 (없으면 null)

### `/api/studio/submissions/<uuid>/`
- GET: `message/data` 래퍼, `data`는 `{ "submission": ... }` 형태
- PATCH: `message/data` 래퍼, `data`는 수정된 submission 객체

---


## 7. 문서 & 스키마
| Path | 설명 |
| --- | --- |
| `GET /api/schema/` | OpenAPI 스키마(JSON) |
| `GET /api/docs/` | Swagger UI |
| `GET /api/redoc/` | ReDoc 문서 |

---

## 8. 이미지 업로드 메타 등록
| Method | Path | 권한 | 설명 |
| --- | --- | --- | --- |
| POST | `/api/images/` | 로그인 | 업로드된 이미지의 메타데이터를 등록하고 `BaseImage.id`를 반환 |
| POST | `/api/images/upload/` | 로그인 | multipart 파일 업로드→BaseImage 생성·반환 (jpg/jpeg/png/webp, 10MB 제한) |

요청 예시:
```json
{
  "url": "https://s3.../image.jpg",
  "s3_key": "path/to/image.jpg",
  "width": 1200,
  "height": 800,
  "filesize": 204800
}
```

응답 예시:
```json
{
  "message": "이미지 메타데이터를 등록했습니다.",
  "data": {
    "id": "<base_image_id>",
    "url": "https://s3.../image.jpg",
    "s3_key": "path/to/image.jpg",
    "width": 1200,
    "height": 800,
    "filesize": 204800
  }
}
```

## 9. 통합 검색
- `GET /api/search/?q=<keyword>&type=&sort=&preview_limit=&page=&page_size=` (누구나)
  - `type`: `all|magazine|archive|riders` (기본 `all`)
  - `sort`: `relevance|latest|popular` (기본 `relevance`)
  - `preview_limit`: `all`일 때 그룹별 미리보기 개수 (기본 3, 최대 10)
  - `page`, `page_size`: 탭 목록용 (기본 `page=1`, `page_size=12`, 최대 24)
  - `q` 누락 시 400 에러 반환
  - `popular`은 `magazine`/`archive`에만 의미 있으며, `riders`는 `relevance`로 동작
  - 검색 범위:
    - magazine: `main_title`, `sub_title`, `content`, `tags`
    - archive: `frame_name`, `components`
    - riders: `username`, `region`, `intro`
  - magazine 응답에는 `matched_excerpt`가 포함될 수 있습니다.
  - archive 응답에는 `matched_components`가 포함될 수 있습니다.
  - type=all 응답: `{"message": "...", "data": {query,type,sort,groups:{magazine,archive,riders}}}`
  - type=magazine/archive/riders 응답: `{"message": "...", "data": {query,type,sort,page,page_size,has_more,items}}`

---

## 10. 홈
- `GET /api/home/` (누구나)
  - 최신 게시글 4건을 반환합니다.
  - 응답 래퍼: `{"message": "홈 데이터를 조회했습니다.", "data": {posts}}`

최근 업데이트: 2026-01-28
