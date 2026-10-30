// Syntax validation is separate from existence and availability in the API catalog.
export function normalizeHallSlug(value) {
  if (typeof value !== 'string') return ''
  const slug = value.trim().toLowerCase()
  return slug.length <= 100 && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug) ? slug : ''
}

export function normalizeHallRecords(records = [], { includeInactive = false } = {}) {
  const seen = new Set()
  return records.flatMap((record) => {
    const slug = normalizeHallSlug(record?.slug)
    if (!slug || seen.has(slug) || (!includeInactive && record.is_active === false)) return []
    seen.add(slug)
    const temporary = record.is_temporary === true
    return [{
      ...record,
      slug,
      name: record.name || slug,
      aliases: Array.isArray(record.aliases) ? [...record.aliases] : [],
      description: record.description || record.short_description || '',
      is_temporary: temporary,
      is_active: record.is_active !== false,
      icon: temporary ? '🖼️' : '🏛️',
      type: temporary ? '临展' : '常设展厅',
      zone: record.floor == null ? '' : `${record.floor} 层`,
      highlights: Array.isArray(record.highlights) ? [...record.highlights] : [],
    }]
  }).sort((a, b) => (a.display_order ?? 0) - (b.display_order ?? 0) || a.slug.localeCompare(b.slug))
}

export function resolveHall(value, records) {
  const key = String(value || '').trim()
  if (!key) return null
  const matches = records.filter((hall) => hall.slug === normalizeHallSlug(key)
    || hall.name === key || hall.aliases?.includes(key))
  return matches.length === 1 ? matches[0] : null
}

export function hallDisplayName(value, records) {
  return resolveHall(value, records)?.name || value || '未选择展厅'
}

export function buildHallDirectoryRoute(records) {
  const steps = normalizeHallRecords(records).map((hall, index) => ({
    order: index + 1,
    hall_slug: hall.slug,
    hall_name: hall.name,
    title: hall.name,
    focus: hall.description || '结合现场展签与展品资料观察。',
    reason: '按馆方设置的展厅顺序参观，可按兴趣调整。',
    minutes: hall.estimated_duration_minutes ?? 0,
    tags: [hall.type],
  }))
  return { title: '馆方展厅顺序', summary: '当前开放展厅的参观参考顺序。', steps }
}
