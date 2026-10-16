// Gọi API cùng nguồn (`/v1/*`, Next chuyển tiếp sang FastAPI). Phiên là cookie HttpOnly `hc_guardian` do máy chủ đặt:
// mã web KHÔNG đọc, KHÔNG lưu token (không localStorage/sessionStorage) — spec 027 bất biến 5.
import type { components } from "@/lib/api/schema";

export type GuardianSession = components["schemas"]["GuardianSession"];
export type GuardianIncidentList = components["schemas"]["GuardianIncidentList"];
export type GuardianIncidentSummary = components["schemas"]["GuardianIncidentSummary"];
export type GuardianIncidentDetail = components["schemas"]["GuardianIncidentDetail"];
export type Decision = "safe" | "false_alarm" | "emergency_pause";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

const SERVER_BUSY = "Máy chủ đang bận. Anh/chị thử lại sau ít phút.";
const OFFLINE = "Không kết nối được. Anh/chị kiểm tra mạng rồi thử lại.";

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, {
      ...init,
      cache: "no-store",
      credentials: "same-origin",
      headers: init.body ? { "Content-Type": "application/json", ...init.headers } : init.headers,
    });
  } catch {
    throw new ApiError(0, OFFLINE);
  }
  if (res.status === 204) return undefined as T;
  if (!res.ok) throw new ApiError(res.status, res.status >= 500 ? SERVER_BUSY : "Chưa thực hiện được. Anh/chị tải lại trang, hoặc nhắn số 4 cho HỏiCon trên Zalo để lấy liên kết đăng nhập mới.");
  return (await res.json()) as T;
}

export const isUnauthorized = (error: unknown): boolean => error instanceof ApiError && error.status === 401;

export function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : OFFLINE;
}
