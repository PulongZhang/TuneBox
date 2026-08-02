import type { LyricLine } from '../types'

const TIME_RE = /\[(\d+):(\d+(?:\.\d+)?)\](.*)/g

/** 解析 LRC 原文 + 翻译，合并为按时间排序的歌词行数组 */
export function parseLyric(lrc: string, tlrc: string): LyricLine[] {
  const orig = new Map<number, string>()
  const tran = new Map<number, string>()

  let m: RegExpExecArray | null
  TIME_RE.lastIndex = 0
  while ((m = TIME_RE.exec(lrc)) !== null) {
    const ms = Number(m[1]) * 60000 + Math.round(Number(m[2]) * 1000)
    const text = m[3].trim()
    if (text) orig.set(ms, text)
  }
  TIME_RE.lastIndex = 0
  while ((m = TIME_RE.exec(tlrc)) !== null) {
    const ms = Number(m[1]) * 60000 + Math.round(Number(m[2]) * 1000)
    const text = m[3].trim()
    if (text) tran.set(ms, text)
  }

  const all = new Set<number>([...orig.keys(), ...tran.keys()])
  return [...all]
    .sort((a, b) => a - b)
    .map((ms) => ({ ms, orig: orig.get(ms) || '', tran: tran.get(ms) || '' }))
}

/** 给定播放位置（毫秒），返回当前高亮行索引 */
export function currentLyricIndex(lines: LyricLine[], ms: number): number {
  let idx = -1
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].ms <= ms) idx = i
    else break
  }
  return idx
}
