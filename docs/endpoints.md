# Spokit Backend Endpoints

## Public Pages (Django templates)
- `/` → 게시글 리스트 / 홈 (post:list)
- `/posts/new/` → 새 게시글 작성 (post:create, 로그인 필요)
- `/posts/<slug>/edit/` → 게시글 수정 (post:edit)
- `/posts/<slug>/` → 게시글 상세 (post:detail)
- `/posts/<slug>/like/` → 좋아요 토글 (POST, post:toggle_like)
- `/posts/autosave/` → 신청서 초안 자동 저장 (POST, post:submission_autosave)
- `/tags/<slug>/` → 태그별 게시글 목록 (post:tagged)
- `/gear-calc/` → 기어 계산 팝업에 사용되는 데이터 (post:gear_calc)
- `/submit/` → 소개 신청 폼 (post:submit, 로그인 필요)

## 사용자/관리자 페이지
- `/users/login/` → 로그인 (user:login)
- `/users/logout/` → 로그아웃 (user:logout)
- `/users/signup/` → 회원가입 (user:signup)
- `/users/profile/` → 내 신청 현황 (user:profile)
- `/users/submissions/<int:pk>/edit/` → 내 신청 수정 (user:submission_edit)
- `/users/admin/dashboard/` → 관리자 대시보드 (user:admin_dashboard)
- `/users/admin/submissions/<int:pk>/` → 관리자 신청 상세 (user:admin_submission_detail)

## REST API (인증 필요)

### Posts
- `GET /api/posts/`
  설명: 게시글 목록. staff는 모든 상태, 일반 사용자는 발행(PUBLISHED)된 게시글만 확인
  쿼리: DRF 페이지네이션(`?page=1`, `?page_size=20` 등)
  응답 예시:
```
[
  {
    "id": 1,
    "title": "테스트 게시글",
    "slug": "test-post",
    "summary": "요약",
    "body": "본문",
    "status": "published",
    "published_at": "2025-09-20T12:34:56Z",
    "cover_image": null,
    "tags": [1, 2]
  }
]
```

- `POST /api/posts/`
  설명: 새 게시글 생성 (staff 권한)
  본문(JSON): `title`, `slug`, `summary`, `body`, `status`, `featured`, `tags`, `cover_image` 등

- `GET /api/posts/<id>/`
  설명: 게시글 상세
- `PUT/PATCH /api/posts/<id>/`
  설명: 게시글 수정
- `DELETE /api/posts/<id>/`
  설명: 게시글 삭제

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
  "message": "소개글",
  "sns_links": ["https://instagram.com/..."],
  "bike": {
    "name": "픽시 #1",
    "spec": {"frame": "Cinelli", "wheelset": "H+Son"}
  }
}
```
- `GET /api/submissions/<id>/`
  설명: 소개 신청 상세 (본인 or 관리자)
- `PUT/PATCH /api/submissions/<id>/`
  설명: 소개 신청 수정
- `DELETE /api/submissions/<id>/`
  설명: 소개 신청 삭제

### 문서/스키마
- `GET /api/schema/` → OpenAPI 스키마(JSON)
- `GET /api/docs/` → Swagger UI
- `GET /api/redoc/` → ReDoc 문서

## 기타 엔드포인트
- `POST /ckeditor/upload/` → CKEditor 이미지 업로드
- `GET /ckeditor/browse/`
- `/media/<path>` → runserver 개발 환경에서 미디어 서빙
- `/admin/...` → Django admin 전체

업데이트: 2025-10-01 20:02:47
