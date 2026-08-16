const SHANGHAI_FORMATTER = new Intl.DateTimeFormat('zh-CN', {
  timeZone: 'Asia/Shanghai',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hourCycle: 'h23',
})

/**
 * 后端 created_at / started_at 为 UTC naive（SQLite 丢 tzinfo，无 Z 后缀）。
 * 显示层统一按 UTC 解析后转东八区墙钟：'2026-07-28T00:46:14' → '2026-07-28 08:46:14'。
 * 空值返回 '-'；无法解析的输入原样返回。
 */
export function formatUtcAsShanghai(value: string | null | undefined): string {
  if (!value) return '-'
  const normalized = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value) ? value : `${value}Z`
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) return value
  return SHANGHAI_FORMATTER.format(date).replace(/\//g, '-')
}
