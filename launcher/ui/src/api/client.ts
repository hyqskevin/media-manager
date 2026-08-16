/**
 * 启动器状态服务 API 客户端。
 *
 * baseUrl 从 window.location.search 的 statusPort 参数解析,
 * PyWebView 加载 file:///.../dist/index.html?statusPort=<port> 时传入。
 */

let baseUrl = 'http://127.0.0.1:8001'

export function setBaseUrl(url: string): void {
  baseUrl = url
}

export function getBaseUrl(): string {
  return baseUrl
}

/**
 * 从 window.location.search 解析 statusPort,初始化 baseUrl。
 * 在 main.ts 调用一次即可。
 */
export function initBaseUrlFromLocation(): void {
  if (typeof window === 'undefined') return
  const params = new URLSearchParams(window.location.search)
  const port = params.get('statusPort')
  if (port) {
    baseUrl = `http://127.0.0.1:${port}`
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = init ? await fetch(`${baseUrl}${path}`, init) : await fetch(`${baseUrl}${path}`)
  return resp.json() as Promise<T>
}

export interface ServiceState {
  state: 'running' | 'stopped' | 'crashed'
  pid: number | null
}

export interface StatusResponse {
  api: ServiceState
  worker: ServiceState
  beat: ServiceState
}

export function fetchStatus(): Promise<StatusResponse> {
  return request<StatusResponse>('/status')
}

export function restartService(name: string): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(`/service/${name}/restart`, { method: 'POST' })
}

export function stopAll(): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>('/service/all/stop', { method: 'POST' })
}

export interface OpencliTestResult {
  ok: boolean
  version: string
  reason: string
  message: string
}

export function testOpencli(): Promise<OpencliTestResult> {
  return request<OpencliTestResult>('/opencli/test')
}

export function getOpencliDownloadUrl(): Promise<{ url: string }> {
  return request<{ url: string }>('/opencli/download-url')
}

export interface OcrStatus {
  status: 'not_installed' | 'installing' | 'installed'
  version: string
}

export function getOcrStatus(): Promise<OcrStatus> {
  return request<OcrStatus>('/ocr/status')
}

export function installOcr(): Promise<{ ok: boolean; message: string }> {
  return request<{ ok: boolean; message: string }>('/ocr/install', { method: 'POST' })
}

export interface OcrInstallProgress {
  active: boolean
  percent: number
  message: string
  ok?: boolean
}

export function getOcrInstallProgress(): Promise<OcrInstallProgress> {
  return request<OcrInstallProgress>('/ocr/install-progress')
}

export interface OcrTestResult {
  ok: boolean
  reason?: string
  message?: string
  text?: string
  latency_ms?: number
}

export function testOcr(): Promise<OcrTestResult> {
  return request<OcrTestResult>('/ocr/test', { method: 'POST' })
}

export function getLogsTail(lines = 50): Promise<{ lines: string[] }> {
  return request<{ lines: string[] }>(`/logs/tail?lines=${lines}`)
}
