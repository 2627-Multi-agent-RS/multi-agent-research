import { Search, Sparkles } from 'lucide-react';
import { FormEvent, useState } from 'react';

interface ResearchInputProps {
  disabled: boolean;
  isConnected: boolean;
  onSubmit: (topic: string) => void;
}

export function ResearchInput({ disabled, isConnected, onSubmit }: ResearchInputProps) {
  const [topic, setTopic] = useState('');
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const isValid = topic.trim().length >= 10 && topic.trim().length <= 500;

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    setHasSubmitted(true);
    if (!isValid || disabled || !isConnected) return;
    onSubmit(topic.trim());
  };

  return (
    <form className="research-form" onSubmit={handleSubmit}>
      <div className="form-label-row">
        <label htmlFor="research-topic">Bạn muốn nghiên cứu điều gì?</label>
        <span className="character-count">{topic.length}/500</span>
      </div>
      <div className={`input-shell ${hasSubmitted && !isValid ? 'input-error' : ''}`}>
        <Search size={20} aria-hidden="true" />
        <input
          id="research-topic"
          value={topic}
          onChange={(event) => { setTopic(event.target.value); setHasSubmitted(false); }}
          placeholder="Ví dụ: Tác động của xe điện lên thị trường năng lượng năm 2025"
          maxLength={500}
          disabled={disabled}
        />
        <button type="submit" disabled={disabled || !isConnected} title="Bắt đầu nghiên cứu">
          <Sparkles size={17} aria-hidden="true" />
          {disabled ? 'Đang xử lý...' : 'Bắt đầu'}
        </button>
      </div>
      {hasSubmitted && !isValid && <p className="form-hint error-text">Chủ đề cần dài từ 10 đến 500 ký tự.</p>}
      {!isConnected && <p className="form-hint">Đang chờ kết nối tới research gateway...</p>}
    </form>
  );
}
