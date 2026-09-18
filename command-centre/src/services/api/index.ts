// Placeholder for future REST API client (FastAPI bridge)
export const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

export async function checkBackendHealth(): Promise<{ status: string }> {
  return { status: 'STANDBY_MOCK_ACTIVE' };
}
