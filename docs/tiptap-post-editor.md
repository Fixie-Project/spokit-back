# TipTap 기반 포스트 작성 페이지 예시

다음 예시는 React + Vite(또는 Next.js) 환경에서 [@tiptap/react](https://tiptap.dev/)를 이용해 포스트 작성 페이지를 구성하고, Spokit 백엔드의 `/api/posts/` API로 콘텐츠를 업로드하는 흐름을 보여줍니다. 실제 프로젝트에서는 상태 관리, 에러 처리, 인증 토큰 주입 등을 프로젝트 규칙에 맞게 보완하세요.

## 1. 설치

```bash
npm install @tiptap/react @tiptap/starter-kit @tiptap/extension-link axios
```

## 2. PostEditor 컴포넌트

```tsx
// src/components/PostEditor.tsx
import { useCallback, useState } from "react";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Link from "@tiptap/extension-link";
import axios from "axios";

const API_ENDPOINT = "/api/posts/"; // 백엔드 프록시/도메인에 맞게 수정

export function PostEditor() {
  const [title, setTitle] = useState("");
  const [subTitle, setSubTitle] = useState("");
  const [status, setStatus] = useState("draft");
  const [frameBrand, setFrameBrand] = useState("");
  const [frameType, setFrameType] = useState("Alloy");
  const [isSubmitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const editor = useEditor({
    extensions: [StarterKit, Link.configure({ openOnClick: false })],
    content: "<p>당신의 이야기로 채워주세요.</p>",
  });

  const handleSubmit = useCallback(async () => {
    if (!editor) return;
    setSubmitting(true);
    setError(null);

    try {
      const payload = {
        main_title: title,
        sub_title: subTitle,
        content_md: editor.getHTML(),
        content_html: editor.getHTML(),
        content_json: editor.getJSON(),
        frame_brand: frameBrand,
        frame_type: frameType,
        slug: title.toLowerCase().replace(/\s+/g, "-"),
        status,
      };

      await axios.post(API_ENDPOINT, payload, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          "Content-Type": "application/json",
        },
      });

      alert("포스트가 저장되었습니다.");
    } catch (err: any) {
      setError(err.response?.data?.message ?? err.message);
    } finally {
      setSubmitting(false);
    }
  }, [editor, title, subTitle, status, frameBrand, frameType]);

  return (
    <div className="w-full max-w-3xl mx-auto space-y-4">
      <div>
        <label className="block text-sm font-medium">Title</label>
        <input
          className="w-full border rounded p-2"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="메인 타이틀"
        />
      </div>

      <div>
        <label className="block text-sm font-medium">Subtitle</label>
        <input
          className="w-full border rounded p-2"
          value={subTitle}
          onChange={(e) => setSubTitle(e.target.value)}
          placeholder="부제"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium">Frame Brand</label>
          <input
            className="w-full border rounded p-2"
            value={frameBrand}
            onChange={(e) => setFrameBrand(e.target.value)}
            placeholder="예: Affinity"
          />
        </div>
        <div>
          <label className="block text-sm font-medium">Frame Type</label>
          <select
            className="w-full border rounded p-2"
            value={frameType}
            onChange={(e) => setFrameType(e.target.value)}
          >
            <option value="Alloy">Alloy</option>
            <option value="Carbon">Carbon</option>
            <option value="Chromoly">Chromoly</option>
            <option value="Steel">Steel</option>
            <option value="Titanium">Titanium</option>
          </select>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium">Status</label>
        <select
          className="border rounded p-2"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="draft">Draft</option>
          <option value="review">Review</option>
          <option value="published">Published</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">본문</label>
        <div className="border rounded min-h-[300px]">
          <EditorContent editor={editor} />
        </div>
        <div className="flex gap-2 mt-2">
          <button onClick={() => editor?.chain().focus().toggleBold().run()}>Bold</button>
          <button onClick={() => editor?.chain().focus().toggleItalic().run()}>Italic</button>
          <button onClick={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()}>
            H2
          </button>
        </div>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        type="button"
        className="bg-black text-white px-4 py-2 rounded disabled:opacity-50"
        disabled={isSubmitting}
        onClick={handleSubmit}
      >
        {isSubmitting ? "저장 중..." : "포스트 저장"}
      </button>
    </div>
  );
}
```

## 3. 라우트 연결

```tsx
// src/pages/post-write.tsx
import { PostEditor } from "../components/PostEditor";

export default function PostWritePage() {
  return (
    <main className="min-h-screen bg-gray-50 py-10">
      <h1 className="text-2xl font-bold text-center mb-8">새 포스트 작성</h1>
      <PostEditor />
    </main>
  );
}
```

## 4. 주의사항
- 인증 토큰은 로컬 저장소 대신 안전한 상태 관리/쿠키를 사용하세요.
- 파일 업로드나 이미지 삽입은 TipTap Extension(Image/StarterKit)으로 확장할 수 있습니다.
- 게시글 저장 시 `slug` 충돌 처리, `tags`, `is_editor_pick` 등 추가 필드를 API 스펙에 맞게 더 붙이면 됩니다.

이 예시를 기반으로, Spokit 백엔드에서 요구하는 필드를 갖춘 실제 작성 페이지를 빠르게 구성할 수 있습니다.
