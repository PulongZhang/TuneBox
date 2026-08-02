/** 触发浏览器下载（append 到 DOM 再移除，兼容性更稳） */
export function downloadFile(url: string, filename: string) {
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
}
