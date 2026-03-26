# Spokit API 명세 (프론트 전달용)

이 문서는 `docs/endpoints.md`의 엔드포인트 목록을 기준으로 **요청/응답 필드**를 요약한 명세입니다.

## 공통
- 인증: `Authorization: Bearer <access_token>`
- 성공 응답 래퍼(기본):
  ```json
  {"message": "...", "data": ...}
  ```
- 실패 응답 포맷:
  ```json
  {"error": "Invalid request", "message": "...", "code": "ERROR_CODE"}
  ```
- 타입 표기
  - `string`, `number`, `boolean`, `uuid`, `datetime`, `object`, `array`, `null`
  - `uuid`는 문자열 UUID입니다.

---

## 1) 인증/유저

### POST /api/auth/google/
- 설명: Google `id_token` 로그인/회원가입
- 요청
  ```json
  {"id_token": "..."}
  ```
- 응답 `data`
  - `refresh` (string)
  - `access` (string)
  - `username` (string)
  - `email` (string)
  - `role` (string)
  - `is_new` (boolean)
  - 참고: `username`이 이미 존재하면 서버가 자동으로 suffix를 붙여 유니크하게 보정합니다.

### GET /api/me/profile/
- 응답 `data`
  - `id` (uuid)
  - `email` (string)
  - `username` (string)
  - `riding_since` (number | null)
  - `region` (string)
  - `intro` (string)
  - `sns_link` (string)
  - `profile_image` (uuid | null)

### PATCH /api/me/profile/
- 요청 (수정 가능 필드)
  - `username` (string)
  - `riding_since` (number | null)
  - `region` (string)
  - `intro` (string)
  - `sns_link` (string)
  - `profile_image` (uuid | null)
- 응답: `GET /api/me/profile/`와 동일
- 참고: `username`은 빈 값 불가이며, 이미 사용 중인 값이면 400 오류가 반환됩니다.

### GET /api/users/<uuid>/profile/
- 응답 `data`
  - `id` (uuid)
  - `username` (string)
  - `riding_since` (number | null)
  - `intro` (string)
  - `region` (string)
  - `sns_link` (string)
  - `profile_image` (object | null)
    - `url` (string)
    - `width` (number | null)
    - `height` (number | null)

### GET /api/me/profile/stats/
- 응답 `data`
  - `total` (number)
  - `by_status` (object: `{status: count}`)

---

## 2) 자전거(Bikes)

### GET /api/me/bikes/
- 응답 `data`: Bike[]

Bike
- `id` (uuid)
- `owner` (uuid)
- `name` (string)
- `frame_name` (string)
- `main_image_url` (string | null)
- `is_posted` (boolean)
- `created_at` (datetime)
- `updated_at` (datetime)
- `builds` (BikeBuildMeta[])

### POST /api/me/bikes/
- 요청
  - `name` (string)
  - `frame_name` (string)
  - `main_image` (uuid | null)
- 응답: Bike

### GET /api/me/bikes/<uuid>/
- 응답: Bike

### PATCH /api/me/bikes/<uuid>/
- 요청: Bike 일부
- 응답: Bike

### DELETE /api/me/bikes/<uuid>/
- 응답: message만

---

## 3) 자전거 빌드(Bike Builds)

### GET /api/me/bike-builds/?visibility=&ordering=
- 응답 `data`: BikeBuildMeta[]

BikeBuildMeta
- `id` (uuid)
- `owner` (object | null)
  - `id` (uuid)
  - `username` (string)
- `base_bike` (object)
  - `id` (uuid)
  - `frame_name` (string)
- `title` (string)
- `is_public` (boolean)
- `created_at` (datetime)
- `updated_at` (datetime)
- `main_image_url` (string | null)
- `like_count` (number)
- `is_liked` (boolean)

### POST /api/me/bike-builds/
- 요청
  - `base_bike` (uuid)
  - `title` (string)
  - `components` (object<string, string[]>)
  - `note` (string)
  - `is_public` (boolean)
  - `main_image` (uuid | null)
  - `images` (uuid[]) 최대 9장
- 응답: BikeBuildDetail

### GET /api/bike-builds/<uuid>/
- 응답 `data`: BikeBuildDetail

BikeBuildDetail
- `id` (uuid)
- `base_bike` (object)
  - `id` (uuid)
  - `frame_name` (string)
- `title` (string)
- `components` (object<string, string[]>)
- `note` (string)
- `is_public` (boolean)
- `created_at` (datetime)
- `updated_at` (datetime)
- `main_image` (object | null)
  - `url` (string)
  - `width` (number | null)
  - `height` (number | null)
- `images` (array)
  - `id` (uuid)
  - `url` (string)
  - `width` (number | null)
  - `height` (number | null)
  - `order` (number)
  - `caption` (string)
- `like_count` (number)
- `is_liked` (boolean)

### PATCH /api/me/bike-builds/<uuid>/
- 요청: BikeBuildWrite 일부
- 응답: BikeBuildDetail

### DELETE /api/me/bike-builds/<uuid>/
- 응답: message만

### GET /api/public/bike-builds/?limit=&offset=
- 응답 `data`
  - `count` (number)
  - `next` (string | null)
  - `previous` (string | null)
  - `results` (BikeBuildMeta[])

### POST /api/bike-builds/<uuid>/like/
- 응답 `data`
  - `liked` (boolean)
  - `like_count` (number)

---

## 4) 소개 신청(Submission)

### GET /api/submissions/ (또는 /api/me/submissions/)
- 응답 `data`
  - `count` (number)
  - `results` (SubmissionListItem[])

SubmissionListItem
- `id` (uuid)
- `title` (string)
- `status` (string)
- `bike_frame` (string | null)
- `build_title` (string | null)
- `created_at` (datetime)
- `updated_at` (datetime)

### POST /api/submissions/
- 요청
  - `title` (string, optional)
  - `story_blocks` (array)
    - `question_id` (string)
    - `answer` (string)
    - `images` (string[] URL, optional)
  - 아래 중 1택:
    - `build_id` (uuid)
    - `new_build_payload` (object)
      - `bike`: `{frame_name: string, name?: string}`
      - `build`: `{title: string, components: object, note: string, is_public: boolean}`
    - `build_snapshot` (object)
- 응답 `data`: SubmissionDetail

SubmissionDetail
- `id` (uuid)
- `user` (uuid)
- `title` (string)
- `build_snapshot` (object)
- `story_blocks` (array)
  - `question_id` (string)
  - `question_text` (string, optional)
  - `answer` (string)
  - `images` (string[] URL, optional)
- `rider_snapshot` (object)
- `status` (string)
- `reason_code` (string | null)
- `reason_detail` (string)
- `created_at` (datetime)
- `updated_at` (datetime)

`rider_snapshot` 구조
- `id` (uuid)
- `username` (string)
- `riding_since` (number | null)
- `intro` (string)
- `region` (string)
- `sns_link` (string)
- `profile_image` (object | null)
  - `url` (string)
  - `width` (number | null)
  - `height` (number | null)

### GET /api/submissions/<uuid>/ (또는 /api/me/submissions/<uuid>/)
- 응답: SubmissionDetail (위와 동일)

### PATCH /api/submissions/<uuid>/
- 요청: Submission 일부 (draft/rejected만)
- 응답: SubmissionDetail

### DELETE /api/submissions/<uuid>/
- 응답: message만

### POST /api/submissions/<uuid>/submit/
- 응답: SubmissionDetail
- 실패 시 `code=SUBMISSION_NOT_READY`, `data`:
  - `missing_required_ids` (string[])
  - `missing_groups` (string[])
  - `need_more_optional_answers` (number)

### POST /api/submissions/<uuid>/resubmit/
- 요청: `{comment?}`
- 응답: SubmissionDetail

### POST /api/submissions/<uuid>/validate/
- 응답 `data`
  - `submittable` (boolean)
  - `missing_required_ids` (string[])
  - `missing_groups` (string[])
  - `need_more_optional_answers` (number)

### GET /api/question-set/?version=
- 응답 `data`
  - `version` (string)
  - `group_labels` (object)
  - `groups` (object)
  - `questions` (array)
  - `metadata` (object)

---

## 5) 게시글(Posts)

### GET /api/posts/?q=&limit=&offset=
- 응답 `data`
  - `count` (number)
  - `next` (string | null)
  - `previous` (string | null)
  - `results` (PostListItem[])
  - `q` 검색 범위: `main_title`, `content_md`, `frame_brand`

PostListItem
- `id` (uuid)
- `author` (object | null)
  - `id` (uuid)
  - `username` (string)
- `slug` (string)
- `main_title` (string)
- `thumbnail_image` (object | null)
  - `url` (string)
  - `purpose` (string)
  - `order` (number)
  - `caption` (string)
- `created_at` (datetime)
- `is_editor_pick` (boolean)
- `tags` (array)
  - `id` (uuid)
  - `name` (string)
  - `created_at` (datetime)
  - `updated_at` (datetime)
- `like_count` (number)
- `comment_count` (number)
- `is_liked` (boolean)

### GET /api/posts/<slug>/
- 응답 `data`: PostDetail

PostDetail
- `id` (uuid)
- `author` (object | null)
  - `id` (uuid)
  - `username` (string)
- `submission` (object | null)
  - `id` (uuid)
  - `status` (string)
  - `build_snapshot` (object)
  - `story_snapshot` (array)
  - `rider_snapshot` (object)
- `rider` (uuid | null)
- `main_title` (string)
- `content_md` (string)
- `content_html` (string)
- `content_json` (object)
- `frame_brand` (string)
- `frame_type` (string)
- `slug` (string)
- `status` (string)
- `published_at` (datetime | null)
- `created_at` (datetime)
- `updated_at` (datetime)
- `is_editor_pick` (boolean)
- `tags` (array)
  - `id` (uuid)
  - `name` (string)
  - `created_at` (datetime)
  - `updated_at` (datetime)
- `images` (array)
  - `id` (uuid)
  - `url` (string)
  - `purpose` (string)
  - `order` (number)
  - `caption` (string)
  - `created_at` (datetime)
- `thumbnail_image` (object | null)
  - `url` (string)
  - `purpose` (string)
  - `order` (number)
  - `caption` (string)
- `like_count` (number)
- `comment_count` (number)
- `is_liked` (boolean)
- `view_count` (number)

### GET /api/posts/popular/
- 응답 `data`
  - `count` (number)
  - `results` (PostListItem[])

### POST /api/posts/<slug>/like/
- 응답 `data`
  - `liked` (boolean)
  - `like_count` (number)

### POST /api/posts/<slug>/comments/
- 요청: `{content: string}`
- 응답 `data`: Comment

Comment
- `id` (uuid)
- `user` (string)
- `content` (string)
- `created_at` (datetime)

### PATCH /api/posts/<slug>/comments/<uuid:comment_id>/
- 요청: `{content: string}`
- 응답: Comment

### DELETE /api/posts/<slug>/comments/<uuid:comment_id>/
- 응답: message만

---

## 6) 스튜디오(운영진)

### GET /api/studio/dashboard/?limit=
- 응답 `data`
  - `total_pending` (number)
  - `total_posting` (number)
  - `pending` (SubmissionDetail[])
  - `posting` (SubmissionDetail[])
  - `pending_top` (SubmissionSummary[])
  - `posting_top` (SubmissionSummary[])
  - `status_counts` (object)
  - `post_status_counts` (object)
  - `total_published_posts` (number)
  - `total_working_posts` (number)
  - `total_draft_posts` (number)
  - `total_rejected_submissions` (number)
  - `total_pending_submissions` (number)
  - `working_posts` (PostSummary[])
  - `stats_last_updated` (datetime)

SubmissionSummary
- `id` (uuid)
- `title` (string)
- `status` (string)
- `created_at` (datetime)
- `updated_at` (datetime)
- `rider` (object)
  - `id` (uuid)
  - `username` (string)
  - `riding_since` (number | null)
  - `region` (string)
  - `intro` (string)
  - `sns_link` (string)

PostSummary
- `id` (uuid)
- `main_title` (string)
- `slug` (string)
- `status` (string)
- `published_at` (datetime | null)
- `updated_at` (datetime)
- `author_name` (string | null)
- `rider` (object | null)
  - `id` (uuid)
  - `username` (string)
  - `riding_since` (number | null)
  - `region` (string)
  - `intro` (string)
  - `sns_link` (string)

### GET /api/studio/submissions/?status=
- 응답 `data`: StudioSubmissionListItem[]

StudioSubmissionListItem
- `id` (uuid)
- `title` (string)
- `status` (string)
- `created_at` (datetime)
- `updated_at` (datetime)
- `rider` (object)
  - `id` (uuid)
  - `username` (string)

### GET /api/studio/submissions/<uuid>/
- 응답 `data.submission`: SubmissionDetail + `rider`
- `rider` 필드
  - `id` (uuid)
  - `username` (string)
  - `riding_since` (number | null)
  - `region` (string)
  - `intro` (string)
  - `sns_link` (string)

### PATCH /api/studio/submissions/<uuid>/
- 요청: Submission 일부
- 응답: SubmissionDetail

### PATCH /api/studio/submissions/<uuid>/status/
- 요청: `{status: string, reason_code?: string, reason_detail?: string}`
- 응답: SubmissionDetail

### GET /api/studio/posts/?status=&q=&ordering=
- 응답 `data`: StudioPostListItem[]

StudioPostListItem
- `id` (uuid)
- `slug` (string)
- `thumbnail_image` (object | null)
  - `url` (string)
  - `purpose` (string)
  - `order` (number)
  - `caption` (string)
- `main_title` (string)
- `display_date` (datetime)
- `rider` (object | null)
  - `id` (uuid)
  - `username` (string)

### POST /api/studio/posts/
- 요청: PostWrite (아래)
- 응답: PostDetail

### GET /api/studio/posts/<slug>/
- 응답 `data.post`: PostDetail

### PATCH /api/studio/posts/<slug>/
- 요청: PostWrite 일부
- 응답: PostDetail

### DELETE /api/studio/posts/<slug>/
- 응답: message만

### GET /api/studio/staff/<uuid>/
### PATCH /api/studio/staff/<uuid>/
- 응답 `data`
  - `id` (uuid)
  - `email` (string)
  - `username` (string)
  - `role` (string)
  - `bio` (string)
  - `contact_email` (string)
  - `permissions` (object)

PostWrite 필드
- `submission` (uuid, optional)
- `bike` (uuid, required)
- `build` (uuid, required)
- `build_snapshot` (object, 운영진만 수정 가능)
- `rider` (uuid, optional)
- `main_title` (string)
- `content_md` (string)
- `content_html` (string)
- `content_json` (object)
- `frame_brand` (string)
- `frame_type` (string)
- `slug` (string)
- `status` (string)
- `is_editor_pick` (boolean)
- `tags` (uuid[])
- `images` (array)
  - `base_image` (uuid)
  - `purpose` (string)
  - `order` (number | null)
  - `caption` (string)

---

## 7) 이미지

### POST /api/images/
- 요청
  - `url` (string)
  - `s3_key` (string)
  - `width` (number | null)
  - `height` (number | null)
  - `filesize` (number | null)
- 응답 `data`
  - `id` (uuid)
  - `url` (string)
  - `s3_key` (string)
  - `width` (number | null)
  - `height` (number | null)
  - `filesize` (number | null)

### POST /api/images/upload/
- multipart 파일 업로드 → BaseImage 생성
- 응답: BaseImage (위와 동일)

---

## 8) 통합 검색

### GET /api/search/?q=&type=&sort=&preview_limit=&page=&page_size=
- `type`: `all` | `magazine` | `archive` | `riders` (기본 `all`)
- `sort`: `relevance` | `latest` | `popular` (기본 `relevance`)
  - `popular`은 `magazine`/`archive`에만 의미 있으며, `riders`는 `relevance`로 동작합니다.
  - `magazine` 인기 기준: 좋아요 + 댓글 합, `archive` 인기 기준: 좋아요 수
- `preview_limit`: `all`일 때 그룹별 미리보기 개수 (기본 3, 최대 10)
- `page`, `page_size`: 탭 목록용 (기본 `page=1`, `page_size=12`, 최대 24)

#### type=all 응답 `data`
- `query` (string)
- `type` (string)
- `sort` (string)
- `groups`
  - `magazine`
    - `items` (PostSearch[])
    - `has_more` (boolean)
    - `view_all_url` (string)
  - `archive`
    - `items` (BuildSearch[])
    - `has_more` (boolean)
    - `view_all_url` (string)
  - `riders`
    - `items` (RiderSearch[])
    - `has_more` (boolean)
    - `view_all_url` (string)

#### type=magazine/archive/riders 응답 `data`
- `query` (string)
- `type` (string)
- `sort` (string)
- `page` (number)
- `page_size` (number)
- `has_more` (boolean)
- `items` (PostSearch[] | BuildSearch[] | RiderSearch[])

PostSearch
- `id` (uuid)
- `slug` (string)
- `main_title` (string)
- `is_editor_pick` (boolean)
- `image` (object | null, 썸네일 우선)
  - `url` (string)
  - `purpose` (string)
- `tags` (array)
  - `id` (uuid)
  - `name` (string)
- `matched_excerpt` (string | null)
- `created_at` (datetime)

RiderSearch
- `id` (uuid)
- `username` (string)
- `location` (string, region)
- `bio` (string, intro)
- `profile_image` (object | null)
  - `url` (string)
  - `width` (number | null)
  - `height` (number | null)

BuildSearch
- `id` (uuid)
- `title` (string)
- `main_image` (object | null)
  - `url` (string)
  - `width` (number | null)
  - `height` (number | null)
- `matched_components` (string[]) (없으면 빈 배열)

---

## 9) 홈

### GET /api/home/
- 응답 `data`
  - `posts` (array)
    - `id` (uuid)
    - `slug` (string)
    - `main_title` (string)
    - `is_editor_pick` (boolean)
    - `image` (object | null)
      - `url` (string)
      - `purpose` (string)
    - `created_at` (datetime)

---

## 10) 문서
- `GET /api/schema/`
- `GET /api/docs/`
- `GET /api/redoc/`
