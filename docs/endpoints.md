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

## 인증/권한 요약
- 기본 인증: JWT(Access/Refresh). `Authorization: Bearer <token>` 헤더 사용.
- 명시적으로 `AllowAny` 로 표시된 엔드포인트만 비로그인 접근 가능.

---

## 1. 인증 & 사용자
| Method | Path | 권한 | 비고 |
| --- | --- | --- | --- |
| POST | `/api/auth/jwt/create/` | 누구나 | 이메일/비밀번호로 액세스·리프레시 토큰 발급 |
| POST | `/api/auth/jwt/refresh/` | 누구나 | 리프레시 토큰으로 액세스 토큰 재발급 |
| POST | `/api/auth/google/` | 누구나 | Google `id_token` 기반 로그인/회원가입 |
| GET  | `/api/me/profile/` | 로그인 | 내 프로필 조회 |
| PATCH| `/api/me/profile/` | 로그인 | 닉네임, 소개 등 수정 |
| GET  | `/api/me/profile/stats/` | 로그인 | 신청서 상태 통계 |
| GET  | `/api/me/submissions/` | 로그인 | 내 신청서 목록 |
| GET  | `/api/me/submissions/<uuid>/` | 로그인 | 신청서 상세 |
| PATCH| `/api/me/submissions/<uuid>/` | 로그인 | 신청서 일부 수정 |

---

## 2. 자전거(Bikes)
### 2.1 내 자전거 / 타 사용자 공개 자전거
`GET /api/bikes/`
- **Query Params**
  - `owner` (선택): 다른 사용자의 공개 자전거 조회.
  - `include_hidden` (선택, `true/1/yes/on`): `owner`가 본인일 때 비공개까지 포함.
- **동작**
  - 파라미터 없음 → 로그인한 사용자의 자전거 목록. `include_hidden=true` 없이 호출하면 공개 빌드만 포함한 요약.
  - `owner=<id>` → 지정 사용자의 공개 자전거만 (비로그인 가능).
- **응답 필드**
  - 자전거 요약: `id`, `name`, `frame_brand`, `frame_name`, `frame_type`, `created_at`, `updated_at`
  - 본인/`include_hidden=true`인 경우에 한해 빌드 목록(`builds`)이 함께 내려갑니다.

### 2.2 자전거 상세/수정
| Method | Path | 권한 | 설명 |
| --- | --- | --- | --- |
| GET | `/api/bikes/<uuid>/` | 로그인 | 소유자이거나 공개 자전거일 때 상세 확인 |
| POST | `/api/bikes/` | 로그인 | 새 자전거 등록 (owner 자동 설정) |
| PATCH/PUT | `/api/bikes/<uuid>/` | 로그인 & 소유자 | 자전거 수정 |
| DELETE | `/api/bikes/<uuid>/` | 로그인 & 소유자 | 자전거 삭제 |

### 2.3 공개 자전거 목록 전용
`GET /api/bikes/public/?owner=<uuid>` (비로그인 가능) → 프레임 정보 요약만 반환.

---

## 3. 자전거 빌드(Bike Builds)
> **주의:** 빌드 API는 모두 로그인 필요. 타 사용자의 공개 빌드를 조회하려면 `owner` 파라미터를 사용하세요.

| Method | Path | Query Params | 설명 |
| --- | --- | --- | --- |
| GET | `/api/bike-builds/` | `owner` (선택), `include_hidden` (선택) | 파라미터 없음 → 내 빌드 전체. `owner` 지정 → 해당 사용자 공개 빌드. `include_hidden=true` → 본인일 때 비공개 포함. |
| GET | `/api/bike-builds/<uuid>/` |  | 소유자는 전체, 타인은 공개 빌드만. |
| POST | `/api/bike-builds/` |  | 빌드 등록 (`base_bike`, `components`, `note`, `is_public`). |
| PATCH/PUT | `/api/bike-builds/<uuid>/` |  | 빌드 수정 (소유자 전용). |
| DELETE | `/api/bike-builds/<uuid>/` |  | 빌드 삭제 (소유자 전용). |

### 빌드 입력 규칙 요약
- `components` 는 최소 3개 카테고리를 포함해야 하며, 각 카테고리는 문서에 정의된 키(`wheel`, `drivetrain` 등)를 사용.
- 카테고리별 `details`는 `front`/`rear` 구분과 `etc` 자유 입력을 지원.
- `is_public` 으로 빌드 공개 여부 제어(프레임이 비공개면 자동 비노출).

---

## 4. 소개 신청(Submission)
| Method | Path | 설명 |
| --- | --- | --- |
| GET | `/api/submissions/` | 내 신청서 목록 |
| POST | `/api/submissions/` | 신청서 생성 (`title`, `story_blocks`, `build_snapshot` 등) |
| GET | `/api/submissions/<uuid>/` | 신청서 상세 |
| PATCH | `/api/submissions/<uuid>/` | 신청서 일부 수정 |
| DELETE | `/api/submissions/<uuid>/` | 신청서 삭제 |
| POST | `/api/submissions/<uuid>/submit/` | 초안 → 접수(submitted) 전환 |
| POST | `/api/submissions/<uuid>/resubmit/` | 반려 → 재신청(resubmitted) (Body: `comment` 선택) |

### 운영진 워크플로우 `/api/submission-workflow/<uuid>/`
| Method | Action | 권한 | 설명 |
| --- | --- | --- | --- |
| POST | `/review/` | Reviewer 이상 | `in_review` 상태로 전환 |
| POST | `/approve/` | Editor/Admin | `approved` 상태로 전환 |
| POST | `/reject/` | Editor/Admin | `rejected` 상태로 전환 (Body: `reason`) |

모든 상태 전이는 `SubmissionStatusLog`에 기록됩니다.

---

## 5. 게시글(Posts)
| Method | Path | 권한 | 설명 |
| --- | --- | --- | --- |
| GET | `/api/posts/` | 누구나 | 공개 게시글 목록. 스태프는 모든 상태 확인 |
| GET | `/api/posts/<slug>/` | 누구나 | 게시글 상세 |
| POST | `/api/posts/` | 스태프 | 게시글 생성 |
| PATCH | `/api/posts/<slug>/` | 스태프 | 게시글 수정 |
| DELETE | `/api/posts/<slug>/` | 스태프 | 게시글 삭제 |
| POST | `/api/posts/<slug>/like/` | 로그인 | 좋아요 토글 |
| POST | `/api/posts/<slug>/comments/` | 로그인 | 댓글 작성 (`content`) |

---

## 6. 스튜디오(운영진)
| Method | Path | 권한 | 설명 |
| --- | --- | --- | --- |
| GET | `/api/studio/dashboard/` | Staff | 접수/검토 중 신청 요약 |
| GET | `/api/studio/submissions/<uuid>/` | Staff | 신청 상세/검토 |
| PATCH | `/api/studio/submissions/<uuid>/` | Staff | 신청 수정 |
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

최근 업데이트: 2025-10-18
