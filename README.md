# Spokit 초기 세팅

장고(Django)를 기반으로 한 픽시 커뮤니티 아카이브의 초기 프로젝트 구조입니다. Docker를 이용해 Postgres 데이터베이스와 함께 실행할 수 있으며, AWS EC2에 배포할 수 있도록 기본 스크립트와 설정을 포함합니다. 패키지 관리는 Poetry로 구성했습니다.

## 프로젝트 구조

```
spokit/
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── manage.py
├── pyproject.toml
├── config/
├── app/
│   ├── post/
│   └── user/
├── templates/
│   ├── post/ (홈, 상세, 태그, 기어 계산기, 스포킷 신청)
│   └── user/ (로그인, 가입, 프로필)
├── static/
├── envs/
└── docker/entrypoint.sh
```

## 사전 준비

- Docker & Docker Compose 설치
- Poetry 설치 (로컬 개발 시)
- AWS EC2 (Ubuntu 22.04 추천) 인스턴스 및 보안 그룹(80, 443, 8000, 5432 포트 열기) 준비
- 도메인 및 SSL은 추후 Nginx/Certbot 구성 시 세팅

## Poetry 환경 (로컬)

1. 의존성 설치
   ```bash
   poetry install
   ```
   > 최초 실행 시 네트워크에 연결되어 있어야 하며, `poetry lock`이 자동으로 생성됩니다.

2. 개발 서버 실행
   ```bash
   poetry run python manage.py migrate
   poetry run python manage.py createsuperuser
   poetry run python manage.py runserver
   ```

3. 테스트 실행
   ```bash
   poetry run pytest
   ```

## 로컬 개발 (Docker Compose)

1. 개발용 환경변수 파일 복사 후 필요값 수정
   ```bash
   cp envs/dev.env .env
   ```
2. 컨테이너 실행 (Poetry dev 그룹 포함)
   ```bash
   docker compose up --build
   ```
3. 데이터베이스 마이그레이션과 슈퍼유저 생성 (초기 1회)
   ```bash
   docker compose exec web python manage.py migrate
   docker compose exec web python manage.py createsuperuser
   ```
4. 브라우저에서 http://localhost:8000 접속 후 사이트 확인

테스트 실행:
```bash
docker compose exec web poetry run pytest
```

## 구현된 주요 기능

- 운영자 게시 전용 포스트 모델(태그·스펙·커버 이미지·공개 상태)과 태그 기반 탐색
- 댓글 & 좋아요(회원 전용) + 메시지 피드백
- 기어비 계산기(`/gear-calc`)와 소개 신청 폼(`/submit`)
- Django Admin에서 태그/포스트/댓글/좋아요/신청 관리 가능
- 이메일 기반 회원가입 + 로그인/로그아웃/프로필 페이지 제공
- 슈퍼유저 전용 관리자 대시보드(`/users/admin/dashboard/`) 제공
  - 대시보드에서 최근 신청글 확인 및 Django Admin으로 바로 이동
  - `/posts/new/` 경로에서 신청서를 불러와 게시글을 작성하고 자동 임시저장
- `/posts/<slug>/edit/`에서 관리자 모드로 게시글을 수정할 수 있으며, 신청서와 연동됩니다.
- 회원 마이페이지에서 소개 신청 진행 상황·반려 사유·완료된 게시글 확인 및 재수정 가능
- 신청 폼에서 프레임·휠셋 등 부품 정보를 세부 항목으로 저장해 추후 검색과 게시글 스펙에 활용
- 소개 신청서는 SNS 링크 중심으로 제출하며, 진행 상태는 자동으로 업데이트
- REST API(`/api/…`)로 바이크 및 소개 신청 데이터를 연동할 수 있도록 DRF ViewSet을 제공

## 주요 Django 설정

- 기본 언어: 한국어(`ko-kr`), 시간대: `Asia/Seoul`
- 데이터베이스: PostgreSQL (`POSTGRES_*` 환경변수로 제어)
- 정적 파일: Whitenoise + `static/` 폴더, `collectstatic` 시 `staticfiles/`에 저장
- 게시글·태그·댓글 모델은 `app.post` 앱에서 관리
- 소개 신청 흐름은 `app.submission`, 회원 자전거/부품 데이터는 `app.bike` 앱에서 관리
- 인증 관련 뷰/폼은 `app.user` 앱에서 관리하며 Django 기본 User 모델을 확장

## 운영 환경 (예시)

1. EC2 인스턴스에 Docker & Docker Compose 설치
   ```bash
   sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin
   sudo usermod -aG docker $USER
   ```
   이후 로그아웃/로그인

2. 프로젝트 코드 배포 (예: git clone)
   ```bash
   git clone <repository-url> spokit
   cd spokit
   ```

3. 환경변수 파일 작성
   ```bash
   cp envs/prod.env .env
   # 환경에 맞게 값 수정 (SECRET_KEY, 도메인 등)
   ```

4. 프로덕션 빌드/실행 (dev 의존성 제외)
   ```bash
   docker compose build --build-arg POETRY_INSTALL_ARGS="--no-root --only main"
   docker compose -f docker-compose.yml up -d
   ```

5. 로그 확인 및 서비스 점검
   ```bash
   docker compose logs -f web
   ```

추후 Nginx 리버스 프록시 및 SSL 인증서 설정을 추가하면 운영 준비가 완료됩니다.

## 다음 단계 제안

1. CI/CD 파이프라인 구성 (GitHub Actions 등)
2. Nginx + Certbot을 통한 HTTPS 구성
3. 블로그 기능 확장 (카테고리, 태그, 검색 등)
