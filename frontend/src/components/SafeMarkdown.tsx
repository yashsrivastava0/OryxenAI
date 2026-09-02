import type { ComponentChildren, VNode } from "preact";

export interface MarkdownHeading {
  id: string;
  text: string;
  level: number;
}

const MAX_MARKDOWN_LENGTH = 200000;
const SAFE_URL_PATTERN = /^https?:\/\/[^\s<>"']+$/i;

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

export function extractHeadings(markdown: string): MarkdownHeading[] {
  const headings: MarkdownHeading[] = [];
  const lines = (markdown || "").split(/\r?\n/);
  const seenIds = new Set<string>();

  for (const line of lines) {
    const match = /^(#{1,4})\s+(.+)$/.exec(line);
    if (match && match[1] && match[2]) {
      const level = match[1].length;
      const text = match[2].trim();
      let id = slugify(text) || "section";
      let count = 1;
      while (seenIds.has(id)) {
        id = `${slugify(text) || "section"}-${count++}`;
      }
      seenIds.add(id);
      headings.push({ id, text, level });
    }
  }

  return headings;
}

function renderInline(text: string): ComponentChildren {
  // Matches **bold**, *italic*, `code`, and [label](url)
  const tokens = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g);

  return tokens.map((token, index) => {
    if (!token) return null;

    const boldMatch = /^\*\*([^*]+)\*\*$/.exec(token);
    if (boldMatch && boldMatch[1]) return <strong key={index}>{boldMatch[1]}</strong>;

    const italicMatch = /^\*([^*]+)\*$/.exec(token);
    if (italicMatch && italicMatch[1]) return <em key={index}>{italicMatch[1]}</em>;

    const codeMatch = /^`([^`]+)`$/.exec(token);
    if (codeMatch && codeMatch[1]) return <code key={index}>{codeMatch[1]}</code>;

    const linkMatch = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(token);
    if (linkMatch && linkMatch[1] && linkMatch[2]) {
      const label = linkMatch[1];
      const url = linkMatch[2].trim();
      if (SAFE_URL_PATTERN.test(url)) {
        return (
          <a key={index} href={url} target="_blank" rel="noopener noreferrer">
            {label}
          </a>
        );
      }
      // Unsafe protocols are rendered as safe text
      return <span key={index}>{label} ({url})</span>;
    }

    return token;
  });
}

export interface SafeMarkdownProps {
  content: string;
  className?: string;
}

export function SafeMarkdown({ content, className = "markdown-content" }: SafeMarkdownProps) {
  let text = String(content || "");
  let truncated = false;

  if (text.length > MAX_MARKDOWN_LENGTH) {
    text = text.slice(0, MAX_MARKDOWN_LENGTH);
    truncated = true;
  }

  const lines = text.split(/\r?\n/);
  const elements: VNode[] = [];
  const seenIds = new Set<string>();

  let i = 0;
  let currentParagraph: string[] = [];

  function flushParagraph() {
    if (!currentParagraph.length) return;
    const key = `p-${elements.length}`;
    elements.push(
      <p key={key}>
        {currentParagraph.map((line, idx) => (
          <span key={idx}>
            {idx > 0 ? " " : ""}
            {renderInline(line)}
          </span>
        ))}
      </p>,
    );
    currentParagraph = [];
  }

  while (i < lines.length) {
    const rawLine = lines[i];
    if (rawLine === undefined) {
      i++;
      continue;
    }
    const line = rawLine;

    // Heading
    const headingMatch = /^(#{1,4})\s+(.+)$/.exec(line);
    if (headingMatch && headingMatch[1] && headingMatch[2]) {
      flushParagraph();
      const level = headingMatch[1].length;
      const headingText = headingMatch[2].trim();
      let id = slugify(headingText) || "section";
      let count = 1;
      while (seenIds.has(id)) {
        id = `${slugify(headingText) || "section"}-${count++}`;
      }
      seenIds.add(id);

      const Tag = `h${level}` as "h1" | "h2" | "h3" | "h4";
      elements.push(
        <Tag key={`h-${elements.length}`} id={id}>
          {renderInline(headingText)}
        </Tag>,
      );
      i++;
      continue;
    }

    // Horizontal Rule
    if (/^---+$/.test(line.trim())) {
      flushParagraph();
      elements.push(<hr key={`hr-${elements.length}`} />);
      i++;
      continue;
    }

    // Unordered List
    const bulletMatch = /^[-*]\s+(.+)$/.exec(line);
    if (bulletMatch && bulletMatch[1]) {
      flushParagraph();
      const items: string[] = [bulletMatch[1]];
      i++;
      while (i < lines.length) {
        const nextLine = lines[i];
        if (nextLine === undefined) break;
        const nextBullet = /^[-*]\s+(.+)$/.exec(nextLine);
        if (nextBullet && nextBullet[1]) {
          items.push(nextBullet[1]);
          i++;
        } else {
          break;
        }
      }
      elements.push(
        <ul key={`ul-${elements.length}`}>
          {items.map((item, idx) => (
            <li key={idx}>{renderInline(item)}</li>
          ))}
        </ul>,
      );
      continue;
    }

    // Ordered List
    const orderedMatch = /^\d+\.\s+(.+)$/.exec(line);
    if (orderedMatch && orderedMatch[1]) {
      flushParagraph();
      const items: string[] = [orderedMatch[1]];
      i++;
      while (i < lines.length) {
        const nextLine = lines[i];
        if (nextLine === undefined) break;
        const nextOrdered = /^\d+\.\s+(.+)$/.exec(nextLine);
        if (nextOrdered && nextOrdered[1]) {
          items.push(nextOrdered[1]);
          i++;
        } else {
          break;
        }
      }
      elements.push(
        <ol key={`ol-${elements.length}`}>
          {items.map((item, idx) => (
            <li key={idx}>{renderInline(item)}</li>
          ))}
        </ol>,
      );
      continue;
    }

    // Empty line
    if (!line.trim()) {
      flushParagraph();
      i++;
      continue;
    }

    // Accumulate into paragraph
    currentParagraph.push(line);
    i++;
  }

  flushParagraph();

  return (
    <div className={className}>
      {truncated && (
        <p className="markdown-truncated-warning">
          <small>Output was truncated for display length.</small>
        </p>
      )}
      {elements}
    </div>
  );
}
