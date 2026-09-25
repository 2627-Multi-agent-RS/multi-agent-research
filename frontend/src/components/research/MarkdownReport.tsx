import type { Components } from 'react-markdown';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { WriterOutput } from '../../types/research';

const mdComponents: Components = {
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noreferrer">
      {children}
    </a>
  ),
  table: ({ children }) => (
    <div className="md-table-wrap">
      <table className="md-table">{children}</table>
    </div>
  ),
};

export function MarkdownReport({ report }: { report: WriterOutput }) {
  return (
    <article className="report-preview">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Final output</p>
          <h2>{report.title}</h2>
        </div>
      </div>

      {report.warnings.length > 0 && (
        <div className="warn-callout" role="note">
          <p className="warn-title">Cảnh báo dữ liệu</p>
          <ul>
            {report.warnings.map((w) => (
              <li key={w.slice(0, 48)}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="md-report">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
          {report.content}
        </ReactMarkdown>
      </div>

      {report.citations.length > 0 && (
        <div className="cite-list">
          <p className="eyebrow">Tài liệu tham khảo</p>
          <ol>
            {report.citations.map((c) => (
              <li key={c.id} id={`cite-${c.id}`}>
                <a href={c.url} target="_blank" rel="noreferrer">
                  {c.title}
                </a>
                <span className="cite-snippet">{c.snippet}</span>
              </li>
            ))}
          </ol>
        </div>
      )}
    </article>
  );
}
