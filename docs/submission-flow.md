# Submission 프론트 구현 가이드

이 문서는 현재 백엔드 구현 기준의 소개 신청서(Submission) 플로우를 프론트에서 그대로 따라갈 수 있도록 정리한 것입니다.
모든 응답은 `{"message": "...", "data": ...}` 래퍼 형태입니다.

---

## 1) 기본 엔드포인트
- 질문 세트 조회: `GET /api/question-set/?version=<id>`
- 신청서 생성/조회/수정/삭제: `POST|GET|PATCH|DELETE /api/submissions/`
- 내 신청서 목록: `GET /api/me/submissions/`
- 제출(접수): `POST /api/submissions/<uuid>/submit/`
- 재신청: `POST /api/submissions/<uuid>/resubmit/`
- 제출 가능 여부 확인(선택): `POST /api/submissions/<uuid>/validate/`

운영진 전용(참고):
- 검토 전환: `POST /api/submission-workflow/<uuid>/review/`
- 승인: `POST /api/submission-workflow/<uuid>/approve/`
- 반려: `POST /api/submission-workflow/<uuid>/reject/`
- 운영진 상세/상태 변경: `/api/studio/submissions/<uuid>/`, `/api/studio/submissions/<uuid>/status/`

---

## 2) 질문 세트 사용법
1. 프론트가 처음 로딩될 때 질문 세트 호출:
   - `GET /api/question-set/` (기본 버전은 v1_6)
2. 응답의 주요 필드:
   - `groups`: 그룹별 질문 배열
   - `group_labels`: 그룹 라벨
   - `required_ids`: 필수 질문 id 목록 (있을 경우 반드시 포함)
   - `metadata.require_one_from_groups`: 해당 그룹 중 최소 1개는 답변 필요

프론트는 아래 규칙을 함께 적용해야 합니다:
- `required_ids`에 포함된 질문은 반드시 답변
- `required_ids`(예: `me`, `final`)를 제외한 **추가 답변 3개 이상**
- `require_one_from_groups` 그룹은 각 그룹에서 최소 1개 답변

---

## 3) 생성 요청 구조

### 공통 필드
```json
{
  "title": "신청서 제목",
  "story_blocks": [
    { "question_id": "intro_1", "answer": "답변", "images": [] },
    { "question_id": "me_1", "answer": "답변" },
    { "question_id": "final_1", "answer": "답변" }
  ]
}
```

`story_blocks` 규칙:
- 각 블록은 `question_id`, `answer` 필수
- `images`는 선택(문자열 URL 배열)
- 필수 질문을 제외하고 **추가 3개 이상** 필요

### 빌드 연결 방법 (3가지 중 1택)
1) **기존 빌드 선택**
```json
{
  "build_id": "<내 빌드 UUID>"
}
```
- 본인 소유 빌드만 허용됨

2) **새 자전거 + 새 빌드 생성**
```json
{
  "new_build_payload": {
    "bike": { "frame_name": "Cinelli Mash", "name": "My Frame" },
    "build": {
      "title": "Night Setup",
      "components": {
        "frame_setup": ["Cinelli Mash"],
        "wheel": ["H Plus Son"],
        "cockpit": ["Nitto"]
      },
      "note": "도심 세팅",
      "is_public": true
    }
  }
}
```

3) **빌드 스냅샷 직접 제공**
```json
{
  "build_snapshot": { "frame_name": "Unknown Frame" }
}
```
- `build_id` / `new_build_payload`가 없을 때만 사용

---

## 4) 상태 전이(사용자 기준)
```
draft -> submitted -> in_review -> approved -> published
draft -> rejected -> resubmitted -> in_review
```

사용자 액션:
- 생성하면 기본 상태는 `draft`
- 제출: `POST /api/submissions/<uuid>/submit/` -> `submitted`
- 반려된 경우: `POST /api/submissions/<uuid>/resubmit/` -> `resubmitted`

수정/삭제 가능 상태:
- `draft`, `rejected`에서만 `PATCH/DELETE` 허용

---

## 5) 제출 검증 실패 응답
```json
{
  "error": "Invalid request",
  "message": "제출 조건을 만족하지 않습니다.",
  "code": "SUBMISSION_NOT_READY",
  "data": {
    "missing_required_ids": ["final_1"],
    "missing_groups": ["outro"],
    "need_more_optional_answers": 2
  }
}
```

---

## 6) 응답 예시(생성)
```json
{
  "message": "신청서를 등록했습니다.",
  "data": {
    "id": "uuid",
    "title": "신청서 제목",
    "status": "draft",
    "story_blocks": [],
    "build_snapshot": {},
    "created_at": "2026-01-01T00:00:00Z"
  }
}
```

---

## 7) 프론트 체크리스트
- [ ] 필수 질문 제외 `story_blocks` 3개 이상 보장
- [ ] `required_ids` 질문은 반드시 포함
- [ ] `require_one_from_groups` 그룹 조건 체크
- [ ] 빌드 연결 방식 1개만 선택(`build_id` / `new_build_payload` / `build_snapshot`)
- [ ] 제출 후 상태 변경 UI 반영(`draft` -> `submitted`)
- [ ] 반려 시 재신청 버튼 노출 및 `resubmit` 호출
