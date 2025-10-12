# Spokit Backend Endpoints

## REST API (인증 필요)

### Posts
- `GET /api/posts/`
  설명: 게시글 목록. staff는 모든 상태, 일반 사용자는 발행(PUBLISHED)된 게시글만 확인
- `GET /api/posts/<slug>/`
  설명: 슬러그 기준 게시글 상세
- `POST /api/posts/`
  설명: 게시글 생성 (스태프 전용)
- `PATCH /api/posts/<slug>/`
  설명: 게시글 부분 수정 (스태프 전용)
- `DELETE /api/posts/<slug>/`
  설명: 게시글 삭제 (스태프 전용)
- `POST /api/posts/<slug>/like/`
  설명: 좋아요 토글 (로그인 필요)
- `POST /api/posts/<slug>/comments/`
  설명: 댓글 작성 (`content` 필드 필요, 로그인 필요)
- `POST /api/gear-calc/`
  설명: 기어비 계산. 본문 예시: `{ "front_teeth": 48, "rear_teeth": 17, "wheel_size": "700c" }`
- `POST /api/posts/autosave/`
  설명: 신청 기반 게시글 초안 자동 저장 (`submission`, `draft` 필드 필요, 스태프 전용)

### Bikes
- `GET /api/bikes/`
  설명: 로그인 사용자의 자전거 목록과 스펙
  응답: `id`, `name`, `is_primary`, `spec`, `created_at`, `updated_at`
- `POST /api/bikes/`
  설명: 자전거 등록 (owner=현재 사용자)
  본문(JSON): `name`, `is_primary`, `spec`
- `GET /api/bikes/<id>/`
  설명: 특정 자전거 조회
- `PUT/PATCH /api/bikes/<id>/`
  설명: 자전거/스펙 수정
- `DELETE /api/bikes/<id>/`
  설명: 자전거 삭제

### Submissions
- `GET /api/submissions/`
  설명: 내 소개 신청 목록
- `POST /api/submissions/`
  설명: 소개 신청 생성
  본문(JSON 예시):
```
{
  "title": "나의 픽시",
  "story_blocks": [
    {
      "question_id": "intro_1",
      "answer": "제 픽시는 ...",
      "images": ["https://cdn.example.com/123.jpg"]
    }
  ],
  "external_story_url": "https://notion.so/...",
  "sns_links": ["https://instagram.com/..."],
  "bike": {
    "name": "픽시 #1",
    "spec": {"frame": "Cinelli", "wheelset": "H+Son"}
  }
}
```
- `GET /api/submissions/<id>/`
  설명: 소개 신청 상세 (본인 or 관리자)
- `PATCH /api/submissions/<id>/`
  설명: 소개 신청 부분 수정(필요한 필드만 전달)
- `DELETE /api/submissions/<id>/`
  설명: 소개 신청 삭제

### User (My Page)
- `GET /api/me/profile/`
  설명: 내 신청 통계
- `GET /api/me/submissions/`
  설명: 내 신청 목록 (로그인 필요)
- `GET /api/me/submissions/<id>/`
  설명: 신청 상세 (로그인 필요)
- `PATCH /api/me/submissions/<id>/`
  설명: 신청 일부 수정 (스토리 블록/외부 링크 등)

### Studio (Staff 전용)
- `GET /api/studio/dashboard/`
  설명: 대기/진행 중 신청 요약 (스태프 권한)
- `GET /api/studio/submissions/<id>/`
  설명: 신청 상세 및 검토 메모 (스태프 권한)
- `PATCH /api/studio/submissions/<id>/`
  설명: 신청 내용/상태 부분 수정 (스태프 권한)
- `POST /api/studio/submissions/<id>/notes/`
  설명: 검토 메모 등록 (스태프 권한)

### 문서/스키마
- `GET /api/schema/` → OpenAPI 스키마(JSON)
- `GET /api/docs/` → Swagger UI
- `GET /api/redoc/` → ReDoc 문서

## 기타 엔드포인트
- `/media/<path>` → runserver 개발 환경에서 미디어 서빙
- `/admin/...` → Django admin 전체

업데이트: 2025-10-01 20:02:47
