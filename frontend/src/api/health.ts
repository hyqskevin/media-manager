import { http } from './http'

export interface HealthStatus {
  status: string
  database: string
}

interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export async function getHealth(): Promise<HealthStatus> {
  const response = await http.get<ApiResponse<HealthStatus>>('/health')
  return response.data.data
}
