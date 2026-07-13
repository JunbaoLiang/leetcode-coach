/** minimal markdown rendering (headings/bold/lists/code) — no external deps */
export default function Markdown({ text }: { text: string }) {
  const blocks = text.split(/\n{2,}/)
  const inline = (s: string) =>
    s.split(/(\*\*[^*]+\*\*|`[^`]+`)/).map((part, i) =>
      part.startsWith('**') && part.endsWith('**') ? (
        <strong key={i}>{part.slice(2, -2)}</strong>
      ) : part.startsWith('`') && part.endsWith('`') ? (
        <code key={i} className="rounded bg-paper-deep px-1 font-mono text-[0.9em]">
          {part.slice(1, -1)}
        </code>
      ) : (
        part
      ),
    )
  return (
    <div className="space-y-3 text-sm leading-relaxed">
      {blocks.map((block, i) => {
        const lines = block.split('\n')
        if (block.startsWith('```')) {
          const code = block.replace(/^```[a-z]*\n?/, '').replace(/\n?```$/, '')
          return (
            <pre
              key={i}
              className="overflow-x-auto rounded-md bg-paper-deep p-3 font-mono text-xs leading-relaxed"
            >
              {code}
            </pre>
          )
        }
        if (block.startsWith('# '))
          return (
            <h1 key={i} className="font-display text-xl font-semibold">
              {block.slice(2)}
            </h1>
          )
        if (block.startsWith('## '))
          return (
            <h2 key={i} className="font-display text-base font-semibold text-vermilion-deep">
              {block.slice(3)}
            </h2>
          )
        if (lines.every((l) => l.startsWith('- ') || l.startsWith('* ')))
          return (
            <ul key={i} className="list-inside list-disc space-y-1">
              {lines.map((l, j) => (
                <li key={j}>{inline(l.slice(2))}</li>
              ))}
            </ul>
          )
        return <p key={i}>{inline(block)}</p>
      })}
    </div>
  )
}
