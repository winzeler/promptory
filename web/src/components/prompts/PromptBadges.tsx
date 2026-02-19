interface Props {
  type: string;
  environment: string;
  modalityOutput?: string;
}

const envColors: Record<string, string> = {
  production: "bg-green-100 text-green-700",
  staging: "bg-yellow-100 text-yellow-700",
  development: "bg-gray-100 text-gray-700",
};

const typeColors: Record<string, string> = {
  chat: "bg-blue-100 text-blue-700",
  tts: "bg-purple-100 text-purple-700",
  completion: "bg-indigo-100 text-indigo-700",
  transcription: "bg-pink-100 text-pink-700",
  image: "bg-orange-100 text-orange-700",
};

const modalityColors: Record<string, string> = {
  tts: "bg-purple-100 text-purple-700",
  audio: "bg-teal-100 text-teal-700",
  image: "bg-orange-100 text-orange-700",
};

export default function PromptBadges({ type, environment, modalityOutput }: Props) {
  return (
    <div className="flex gap-1">
      <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${typeColors[type] ?? "bg-gray-100 text-gray-700"}`}>
        {type}
      </span>
      <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${envColors[environment] ?? "bg-gray-100 text-gray-700"}`}>
        {environment}
      </span>
      {modalityOutput && modalityOutput !== "text" && (
        <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${modalityColors[modalityOutput] ?? "bg-gray-100 text-gray-700"}`}>
          {modalityOutput}
        </span>
      )}
    </div>
  );
}
