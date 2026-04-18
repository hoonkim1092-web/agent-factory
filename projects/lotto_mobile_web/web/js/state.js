// state.js — 단일 스토어(subscribe/publish)
// 문서 언어: ko-KR / 모듈: frontend_dev_module_2
// 상태 스키마: { params, result, status, lastError }

/**
 * @typedef {{ n: number, draws: number, offline: boolean }} RecommendationRequest
 * @typedef {{
 *   generated_at: string,
 *   source: 'live' | 'offline' | 'cache',
 *   draws_used: number,
 *   combos: Array<{
 *     numbers: number[],
 *     score: number,
 *     odd_even_ratio: string,
 *     section_distribution: number[]
 *   }>
 * }} RecommendationResponse
 * @typedef {'idle' | 'loading' | 'success' | 'error' | 'offline'} AppStatus
 * @typedef {{
 *   params: RecommendationRequest,
 *   result: RecommendationResponse | null,
 *   status: AppStatus,
 *   lastError: string | null
 * }} AppState
 */

/**
 * scope 문서(§상태 스키마) 기준 기본값.
 * - n=5, draws=500은 기능 명세의 기본값을 따른다.
 * - offline=false로 시작해 module_5가 네트워크 상황에 따라 승격한다.
 */
export const initialState = Object.freeze({
  params: Object.freeze({ n: 5, draws: 500, offline: false }),
  result: null,
  status: "idle",
  lastError: null,
});

/**
 * 프레임워크 없이 쓰는 얇은 Pub/Sub 스토어.
 * setState는 부분 갱신(얕은 merge)을 허용해, 각 하위 모듈이
 * 관심 있는 키만 넘겨도 된다.
 *
 * @param {AppState} [initial]
 * @returns {{
 *   getState: () => AppState,
 *   setState: (patch: Partial<AppState> | ((prev: AppState) => Partial<AppState>)) => AppState,
 *   subscribe: (listener: (state: AppState) => void) => () => void
 * }}
 */
export function createStore(initial = initialState) {
  let state = freezeState(normalizeInitial(initial));
  const listeners = new Set();

  function getState() {
    return state;
  }

  function setState(patch) {
    const resolvedPatch =
      typeof patch === "function" ? patch(state) : patch;
    if (!resolvedPatch || typeof resolvedPatch !== "object") {
      return state;
    }
    const next = { ...state, ...resolvedPatch };
    // params는 객체이므로 얕은 병합을 한 단계 더 적용한다.
    if (resolvedPatch.params && typeof resolvedPatch.params === "object") {
      next.params = { ...state.params, ...resolvedPatch.params };
    }
    if (shallowEqual(state, next)) {
      return state;
    }
    state = freezeState(next);
    for (const listener of listeners) {
      try {
        listener(state);
      } catch (err) {
        // 구독자의 오류가 다른 구독자 알림을 막지 않도록 격리한다.
        // eslint-disable-next-line no-console
        console.error("[state] 구독자 콜백 오류:", err);
      }
    }
    return state;
  }

  function subscribe(listener) {
    if (typeof listener !== "function") {
      throw new TypeError("subscribe(listener): listener는 함수여야 한다.");
    }
    listeners.add(listener);
    return () => listeners.delete(listener);
  }

  return { getState, setState, subscribe };
}

function normalizeInitial(value) {
  if (!value || typeof value !== "object") return { ...initialState };
  return {
    params: { ...initialState.params, ...(value.params || {}) },
    result: value.result ?? null,
    status: value.status ?? "idle",
    lastError: value.lastError ?? null,
  };
}

function freezeState(value) {
  return Object.freeze({
    ...value,
    params: Object.freeze({ ...value.params }),
  });
}

function shallowEqual(a, b) {
  if (a === b) return true;
  const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
  for (const k of keys) {
    if (k === "params") {
      const pa = a.params || {};
      const pb = b.params || {};
      const pk = new Set([...Object.keys(pa), ...Object.keys(pb)]);
      for (const sub of pk) {
        if (pa[sub] !== pb[sub]) return false;
      }
      continue;
    }
    if (a[k] !== b[k]) return false;
  }
  return true;
}
