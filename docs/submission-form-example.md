# 소개 신청서 작성 페이지 예시

React + Axios로 `POST /api/submissions/` 및 `POST /api/submissions/<id>/submit/` 를 호출하는 간단한 폼 예시입니다. TipTap이나 기타 에디터를 연결할 수도 있지만, 여기서는 질문-답변 텍스트와 이미지 URL 배열을 입력받는 기본 흐름만 보여줍니다.

```tsx
import { useState } from "react";
import axios from "axios";

type StoryBlock = {
  question_id: string;
  answer: string;
  images?: string[];
};

export function SubmissionForm() {
  const [title, setTitle] = useState("");
  const [storyBlocks, setStoryBlocks] = useState<StoryBlock[]>([
    { question_id: "intro_1", answer: "" },
  ]);
  const [frameName, setFrameName] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const handleBlockChange = (index: number, field: keyof StoryBlock, value: string) => {
    setStoryBlocks((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });
  };

  const addBlock = () => {
    setStoryBlocks((prev) => [...prev, { question_id: "custom", answer: "" }]);
  };

  const handleSubmit = async () => {
    try {
      const payload = {
        title,
        story_blocks: storyBlocks,
        build_snapshot: { frame_name: frameName },
      };
      const response = await axios.post("/api/submissions/", payload, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
      });
      setStatusMessage(`초안이 저장되었습니다. ID: ${response.data.id}`);
    } catch (error: any) {
      setStatusMessage(error.response?.data?.message ?? "저장 실패");
    }
  };

  return (
    <div className="space-y-4">
      <input
        className="border p-2 w-full"
        placeholder="신청서 제목"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <input
        className="border p-2 w-full"
        placeholder="프레임 이름"
        value={frameName}
        onChange={(e) => setFrameName(e.target.value)}
      />

      {storyBlocks.map((block, index) => (
        <div key={index} className="border rounded p-3 space-y-2">
          <input
            className="border p-2 w-full"
            placeholder="질문 ID"
            value={block.question_id}
            onChange={(e) => handleBlockChange(index, "question_id", e.target.value)}
          />
          <textarea
            className="border p-2 w-full"
            rows={3}
            placeholder="답변"
            value={block.answer}
            onChange={(e) => handleBlockChange(index, "answer", e.target.value)}
          />
        </div>
      ))}
      <button type="button" onClick={addBlock} className="px-3 py-1 bg-gray-200 rounded">
        질문 추가
      </button>

      <button
        type="button"
        onClick={handleSubmit}
        className="px-4 py-2 bg-black text-white rounded"
      >
        초안 저장
      </button>

      {statusMessage && <p className="text-sm mt-2">{statusMessage}</p>}
    </div>
  );
}
```

- 저장 후 `SubmissionViewSet.submit` 엔드포인트(`/api/submissions/<id>/submit/`)를 호출하면 접수 상태(`submitted`)로 전환할 수 있습니다.
- 스토리 블록마다 이미지 업로드가 필요하다면 입력 값 대신 파일 업로드 컴포넌트를 연결하고, 업로드된 URL을 `images` 배열에 채워 넣으면 됩니다.
- `build_snapshot`은 사용자가 신청 시 선택하거나 입력한 자전거/빌드 정보를 JSON 형태로 넣어주면 되고, 추후 Post 생성 시 자동으로 활용됩니다.
