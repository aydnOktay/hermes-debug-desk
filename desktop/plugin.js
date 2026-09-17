/**
 * Debug Desk — today's git + last Hermes terminal failure.
 *
 * Unified package: this file is copied to $HERMES_HOME/desktop-plugins/debug-desk/.
 * Enable the desktop half in Capabilities → Plugins (separate from plugins.enabled).
 */

import { host, useValue, useQuery, useMutation, queryClient } from '@hermes/plugin-sdk'
import { jsx, jsxs } from 'react/jsx-runtime'
import { useMemo } from 'react'

const FRESH_MS = 15 * 60 * 1000

function typeEntries(types) {
  if (!types || typeof types !== 'object') return []
  return Object.entries(types).sort((a, b) => b[1] - a[1])
}

function formatTime(iso) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return iso
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return iso
  }
}

function isFresh(failure) {
  if (!failure || !failure.ts) return false
  const t = Date.parse(failure.ts)
  if (Number.isNaN(t)) return false
  return Date.now() - t < FRESH_MS
}

function Section({ title, children }) {
  return jsxs('div', {
    style: { display: 'flex', flexDirection: 'column', gap: 6 },
    children: [
      jsx('div', {
        style: {
          fontSize: 11,
          letterSpacing: '0.04em',
          textTransform: 'uppercase',
          color: 'var(--ui-text-tertiary)',
        },
        children: title,
      }),
      children,
    ],
  })
}

function DeskPane({ ctx }) {
  const cwd = useValue(host.state.cwd) || ''
  const query = useQuery({
    queryKey: ['debug-desk', 'board', cwd],
    queryFn: () => ctx.rest('/board' + (cwd ? `?cwd=${encodeURIComponent(cwd)}` : '')),
    refetchInterval: 5000,
  })
  const mutate = useMutation({
    mutationFn: () => ctx.rest('/summarize', { method: 'POST', body: { cwd } }),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['debug-desk'] })
    },
  })

  const git = query.data && query.data.git
  const failure = query.data && query.data.failure
  const types = useMemo(() => typeEntries(git && git.types), [git])
  const fresh = Boolean((query.data && query.data.fresh) || isFresh(failure))

  return jsxs('div', {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 14,
      padding: 12,
      height: '100%',
      overflow: 'auto',
      fontSize: 13,
      color: 'var(--ui-text-secondary)',
    },
    children: [
      jsxs('div', {
        style: { display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' },
        children: [
          jsx('div', {
            style: { fontWeight: 600, color: 'var(--ui-text-secondary)' },
            children: 'Debug Desk',
          }),
          jsx('div', {
            style: { fontSize: 11, color: 'var(--ui-text-tertiary)' },
            children: git && git.branch ? git.branch : '',
          }),
        ],
      }),

      query.isLoading
        ? jsx('div', { style: { color: 'var(--ui-text-tertiary)' }, children: 'Loading…' })
        : null,
      query.error
        ? jsx('div', {
            style: { color: 'var(--ui-text-secondary)', fontSize: 12 },
            children:
              'Backend unreachable. Enable debug-desk in plugins.enabled and restart the gateway.',
          })
        : null,

      jsx(Section, {
        title: 'Today',
        children:
          git && git.ok
            ? jsxs('div', {
                style: { display: 'flex', flexDirection: 'column', gap: 8 },
                children: [
                  jsxs('div', {
                    children: [
                      jsx('span', {
                        style: { fontSize: 22, fontWeight: 650, color: 'var(--ui-text-secondary)' },
                        children: String(git.commit_count || 0),
                      }),
                      jsx('span', {
                        style: { marginLeft: 6, color: 'var(--ui-text-tertiary)' },
                        children: git.commit_count === 1 ? 'commit' : 'commits',
                      }),
                    ],
                  }),
                  types.length
                    ? jsx('div', {
                        style: { display: 'flex', flexWrap: 'wrap', gap: 6 },
                        children: types.map(([name, count]) =>
                          jsxs(
                            'span',
                            {
                              style: {
                                fontSize: 11,
                                padding: '2px 6px',
                                border: '1px solid var(--ui-stroke-secondary)',
                                borderRadius: 4,
                              },
                              children: [name, ' ', count],
                            },
                            name,
                          ),
                        ),
                      })
                    : jsx('div', {
                        style: { color: 'var(--ui-text-tertiary)' },
                        children: 'No conventional-commit types yet.',
                      }),
                  git.files && git.files.length
                    ? jsx('div', {
                        style: {
                          fontSize: 12,
                          color: 'var(--ui-text-tertiary)',
                          lineHeight: 1.45,
                        },
                        children: git.files.slice(0, 12).join('\n'),
                      })
                    : jsx('div', {
                        style: { color: 'var(--ui-text-tertiary)' },
                        children: 'No files touched today.',
                      }),
                ],
              })
            : jsx('div', {
                style: { color: 'var(--ui-text-tertiary)' },
                children: (git && git.error) || 'Open a git repo to see today’s digest.',
              }),
      }),

      jsx(Section, {
        title: 'Last failure',
        children: failure
          ? jsxs('div', {
              style: { display: 'flex', flexDirection: 'column', gap: 8 },
              children: [
                jsxs('div', {
                  style: { display: 'flex', gap: 8, alignItems: 'center' },
                  children: [
                    jsx('span', {
                      style: {
                        width: 8,
                        height: 8,
                        borderRadius: 99,
                        background: fresh ? 'var(--ui-accent)' : 'var(--ui-text-quaternary)',
                        display: 'inline-block',
                      },
                    }),
                    jsx('span', {
                      style: { fontSize: 11, color: 'var(--ui-text-tertiary)' },
                      children: formatTime(failure.ts),
                    }),
                    failure.exit_code != null
                      ? jsxs('span', {
                          style: { fontSize: 11, color: 'var(--ui-text-tertiary)' },
                          children: ['exit ', String(failure.exit_code)],
                        })
                      : null,
                  ],
                }),
                jsx('div', {
                  style: {
                    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
                    fontSize: 12,
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                  },
                  children: failure.command || '(no command)',
                }),
                jsx('div', {
                  style: {
                    fontSize: 12,
                    color: 'var(--ui-text-secondary)',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    lineHeight: 1.45,
                  },
                  children:
                    failure.summary ||
                    (failure.lines && failure.lines.length
                      ? failure.lines.join('\n')
                      : 'No captured output.'),
                }),
                jsx('button', {
                  type: 'button',
                  disabled: mutate.isPending,
                  onClick: () => mutate.mutate(),
                  style: {
                    alignSelf: 'flex-start',
                    fontSize: 12,
                    padding: '4px 8px',
                    border: '1px solid var(--ui-stroke-secondary)',
                    background: 'transparent',
                    color: 'var(--ui-text-secondary)',
                    borderRadius: 4,
                    cursor: mutate.isPending ? 'wait' : 'pointer',
                  },
                  children: mutate.isPending ? 'Summarising…' : 'Refresh summary',
                }),
                mutate.data && mutate.data.error
                  ? jsx('div', {
                      style: { fontSize: 11, color: 'var(--ui-text-tertiary)' },
                      children: String(mutate.data.error),
                    })
                  : null,
                mutate.data && mutate.data.note
                  ? jsx('div', {
                      style: { fontSize: 11, color: 'var(--ui-text-tertiary)' },
                      children: String(mutate.data.note),
                    })
                  : null,
              ],
            })
          : jsx('div', {
              style: { color: 'var(--ui-text-tertiary)' },
              children: 'No failed terminal call captured yet.',
            }),
      }),
    ],
  })
}

function DeskChip({ ctx }) {
  const cwd = useValue(host.state.cwd) || ''
  const query = useQuery({
    queryKey: ['debug-desk', 'board', cwd],
    queryFn: () => ctx.rest('/board' + (cwd ? `?cwd=${encodeURIComponent(cwd)}` : '')),
    refetchInterval: 8000,
  })
  const failure = query.data && query.data.failure
  const fresh = Boolean((query.data && query.data.fresh) || isFresh(failure))
  const commits = query.data && query.data.git && query.data.git.ok ? query.data.git.commit_count : null

  return jsxs('button', {
    type: 'button',
    title: fresh && failure && failure.command ? failure.command : 'Debug Desk',
    onClick: () => {
      const msg = fresh
        ? 'Recent terminal failure captured — open the Debug Desk pane.'
        : 'Debug Desk is idle.'
      host.notify({ kind: fresh ? 'warning' : 'info', message: msg })
    },
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6,
      padding: '0 6px',
      fontSize: '0.6875rem',
      color: 'var(--ui-text-tertiary)',
      background: 'transparent',
      border: 'none',
      cursor: 'pointer',
    },
    children: [
      jsx('span', {
        style: {
          width: 7,
          height: 7,
          borderRadius: 99,
          background: fresh ? '#e5484d' : 'var(--ui-text-quaternary)',
          display: 'inline-block',
        },
      }),
      jsx('span', {
        children: commits == null ? 'desk' : `desk ${commits}`,
      }),
    ],
  })
}

export default {
  id: 'debug-desk',
  name: 'Debug Desk',
  defaultEnabled: false,
  register(ctx) {
    ctx.register({
      id: 'pane',
      area: 'panes',
      title: 'debug desk',
      data: { placement: 'right', width: '280px' },
      render: () => jsx(DeskPane, { ctx }),
    })
    ctx.register({
      id: 'chip',
      area: 'statusBar.right',
      order: 125,
      render: () => jsx(DeskChip, { ctx }),
    })
  },
}
