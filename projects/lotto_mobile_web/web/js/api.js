// api.js — 백엔드 GET /api/recommend 소비 레이어
// 문서 언어: ko-KR / 모듈: frontend_dev_module_2
// 계약: docs/modules/frontend_dev_module_2_scope.md §백엔드 계약

const DEFAULT_ENDPOINT = "/api/recommend";
const DEFAULT_TIMEOUT_MS = 8000;

/**
 * 네트워크/오프라인 상황을 상위에 알리기 위한 에러 타입.
 * module_5(오프라인 폴백)가 이 타입을 instanceof로 감지해 캐시 응답으로 치환한다.
 */
export class OfflineError extends Error {
  constructor(message = "네트워크에 연결할 수 없어 추천 결과를 가져오지 못했습니다.", cause) {
    super(message);
    this.name = "OfflineError";
    if (cause !== undefined) this.cause = cause;
  }
}

/**
 * 백엔드 `{error:{code,message,details}}` 스키마를 래핑한다.
 * 4xx 응답에서 사용자에게 노출할 메시지를 일관되게 꺼낼 수 있다.
 */
export class ApiError extends Error {
  /**
   * @param {string} code
   * @param {string} message
   * @param {number} status
   * @param {Record<string, unknown>} [details]
   */
  constructor(code, message, status, details) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.details = details ?? null;
  }
}

/**
 * 추천 API 호출.
 * @param {{ n?: number, draws?: number, offline?: boolean }} [params]
 * @param {{ endpoint?: string, signal?: AbortSignal, fetchImpl?: typeof fetch, timeoutMs?: number }} [options]
 * @returns {Promise<import('./state.js').RecommendationResponse>}
 * @throws {ApiError} 4xx 파라미터 오류
 * @throws {OfflineError} 네트워크 실패 또는 5xx/timeout
 */
export async function fetchRecommendation(params = {}, options = {}) {
  const endpoint = options.endpoint ?? DEFAULT_ENDPOINT;
  const fetchImpl =
    options.fetchImpl ??
    (typeof fetch === "function" ? fetch.bind(globalThis) : null);
  if (!fetchImpl) {
    throw new OfflineError("이 환경에서는 fetch가 제공되지 않아 요청을 보낼 수 없습니다.");
  }

  const query = buildQuery(params);
  const url = query ? `${endpoint}?${query}` : endpoint;

  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const { signal, cancel } = composeSignal(options.signal, timeoutMs);

  let response;
  try {
    response = await fetchImpl(url, {
      method: "GET",
      headers: { Accept: "application/json" },
      signal,
    });
  } catch (err) {
    cancel();
    // AbortError(타임아웃/수동 취소), TypeError(네트워크) 모두 오프라인으로 승격.
    throw new OfflineError(
      "네트워크 요청이 실패했습니다. 오프라인 상태이거나 서버에 도달할 수 없습니다.",
      err,
    );
  }
  cancel();

  if (!response.ok) {
    // 5xx는 네트워크 성공이지만 오프라인 폴백 대상으로 승격(명세 §백엔드 계약).
    if (response.status >= 500) {
      throw new OfflineError(
        `서버 오류(${response.status})로 추천 결과를 가져오지 못했습니다.`,
      );
    }
    const errorPayload = await safeReadJson(response);
    const errorBody = errorPayload && errorPayload.error ? errorPayload.error : {};
    throw new ApiError(
      errorBody.code || "invalid_parameter",
      errorBody.message || `요청이 거절되었습니다 (HTTP ${response.status}).`,
      response.status,
      errorBody.details,
    );
  }

  const payload = await safeReadJson(response);
  if (!payload || typeof payload !== "object") {
    throw new OfflineError("서버 응답이 비어 있거나 JSON 형식이 아닙니다.");
  }
  return /** @type {import('./state.js').RecommendationResponse} */ (payload);
}

/**
 * 파라미터를 URLSearchParams 문자열로 안전하게 직렬화한다.
 * undefined/null 값은 제외한다.
 */
function buildQuery(params) {
  const out = new URLSearchParams();
  if (params.n !== undefined && params.n !== null) {
    out.set("n", String(params.n));
  }
  if (params.draws !== undefined && params.draws !== null) {
    out.set("draws", String(params.draws));
  }
  if (params.offline !== undefined && params.offline !== null) {
    out.set("offline", String(Boolean(params.offline)));
  }
  return out.toString();
}

/**
 * 외부 signal과 자체 타임아웃을 AND 결합한다.
 * 구형 브라우저 대응을 위해 AbortSignal.any는 쓰지 않는다.
 */
function composeSignal(external, timeoutMs) {
  if (typeof AbortController === "undefined") {
    return { signal: external, cancel: () => {} };
  }
  const controller = new AbortController();
  const timer =
    timeoutMs > 0
      ? setTimeout(() => controller.abort(new Error("timeout")), timeoutMs)
      : null;

  if (external) {
    if (external.aborted) {
      controller.abort(external.reason);
    } else {
      external.addEventListener(
        "abort",
        () => controller.abort(external.reason),
        { once: true },
      );
    }
  }

  return {
    signal: controller.signal,
    cancel: () => {
      if (timer) clearTimeout(timer);
    },
  };
}

async function safeReadJson(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}
