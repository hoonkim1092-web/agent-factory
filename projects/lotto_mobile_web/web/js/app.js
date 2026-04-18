// app.js — SPA 진입점, 마운트/이벤트 와이어링
// 문서 언어: ko-KR / 모듈: frontend_dev_module_2
// scope 문서 §구현 순서 8: 부트스트랩(마운트 + 이벤트 와이어링)

import { createStore, initialState } from "./state.js";
import { fetchRecommendation, OfflineError, ApiError } from "./api.js";
import { renderCardList } from "./components/CardList.js";
import { renderParamPanel } from "./components/ParamPanel.js";
import { renderOfflineBanner } from "./components/OfflineBanner.js";

const CACHE_KEY = "lotto:last-success-recommendation";
const CACHE_VERSION = 1;
const CACHE_TTL_MS = 24 * 60 * 60 * 1000;
const OFFLINE_STALE_MESSAGE =
  "현재 네트워크가 불안정해 마지막 저장 결과를 보여주는 중입니다.";
const OFFLINE_EMPTY_MESSAGE =
  "저장된 추천 결과가 없어 오프라인으로는 보여줄 수 없습니다.";

const STATUS_LABEL = {
  idle: "대기 중",
  loading: "조합을 생성하고 있습니다…",
  success: "추천 완료",
  error: "요청 오류",
  offline: "오프라인",
};

/**
 * 앱 전체를 마운트하고, 추천 버튼 클릭 흐름을 스토어에 연결한다.
 * scope 문서 §상태 전이 다이어그램을 그대로 구현한다.
 *
 * @param {{ root?: HTMLElement, fetcher?: typeof fetchRecommendation }} [options]
 */
export function mountApp(options = {}) {
  const root = options.root ?? document.getElementById("app");
  if (!(root instanceof HTMLElement)) {
    throw new Error("#app 루트 요소를 찾지 못했습니다.");
  }

  const fetcher = options.fetcher ?? fetchRecommendation;
  const store = createStore(initialState);

  const sessionStatusEl = root.querySelector("#session-status");
  const paramPanelRoot = root.querySelector("#param-panel-root");
  const cardListRoot = root.querySelector("#card-list-root");
  const offlineBannerRoot = root.querySelector("#offline-banner-root");
  const submitButton = root.querySelector("#submit-button");
  const emptyHint = root.querySelector("#empty-hint");

  if (paramPanelRoot instanceof HTMLElement) {
    renderParamPanel(paramPanelRoot, store);
  }

  // 스토어 변화 → DOM 반영 단일 진입점.
  const unsubscribe = store.subscribe((state) => {
    applyStateToDom(state);
  });
  applyStateToDom(store.getState());

  if (submitButton instanceof HTMLButtonElement) {
    submitButton.addEventListener("click", () => {
      void submitRecommendation();
    });
  }

  return { store, unmount };

  function unmount() {
    unsubscribe();
  }

  async function submitRecommendation() {
    const { params, status } = store.getState();
    if (status === "loading") return;

    store.setState({ status: "loading", lastError: null });

    try {
      const result = await fetcher(params);
      persistLastSuccess(params, result);
      store.setState({
        status: "success",
        result,
        lastError: null,
      });
    } catch (err) {
      if (err instanceof OfflineError) {
        const cachedResult = restoreLastSuccess();
        if (cachedResult) {
          store.setState({
            status: "offline",
            result: cachedResult,
            lastError: OFFLINE_STALE_MESSAGE,
          });
          return;
        }
        store.setState({
          status: "offline",
          result: null,
          lastError: OFFLINE_EMPTY_MESSAGE,
        });
        return;
      }
      if (err instanceof ApiError) {
        store.setState({
          status: "error",
          lastError: err.message,
        });
        return;
      }
      store.setState({
        status: "error",
        lastError:
          err && typeof err === "object" && "message" in err
            ? String(err.message)
            : "알 수 없는 오류가 발생했습니다.",
      });
    }
  }

  function applyStateToDom(state) {
    root.dataset.status = state.status;

    if (sessionStatusEl instanceof HTMLElement) {
      if (state.status === "error" && state.lastError) {
        sessionStatusEl.textContent = state.lastError;
      } else {
        sessionStatusEl.textContent = STATUS_LABEL[state.status] ?? "대기 중";
      }
    }

    if (submitButton instanceof HTMLButtonElement) {
      submitButton.disabled = state.status === "loading";
    }

    if (offlineBannerRoot instanceof HTMLElement) {
      syncOfflineBannerDataset(offlineBannerRoot, state);
      renderOfflineBanner(offlineBannerRoot, state.status);
    }

    if (cardListRoot instanceof HTMLElement) {
      const combos = state.result?.combos;
      const hasResult = Array.isArray(combos) && combos.length > 0;

      if (emptyHint instanceof HTMLElement) {
        emptyHint.hidden = hasResult || state.status === "loading";
      }

      if (hasResult) {
        renderCardList(cardListRoot, combos);
        if (emptyHint instanceof HTMLElement && !cardListRoot.contains(emptyHint)) {
          // empty-hint는 초기 렌더 이후엔 카드 리스트가 책임지므로 그대로 둔다.
        }
      } else if (state.status === "idle") {
        // 초기 상태: empty-hint가 이미 DOM에 노출되도록 유지.
        if (emptyHint instanceof HTMLElement) {
          cardListRoot.innerHTML = "";
          cardListRoot.appendChild(emptyHint);
          emptyHint.hidden = false;
        }
      }
    }
  }
}

function persistLastSuccess(params, result) {
  const storage = getLocalStorage();
  if (!storage) return;

  const payload = {
    version: CACHE_VERSION,
    cached_at: new Date().toISOString(),
    params: {
      n: Number(params?.n),
      draws: Number(params?.draws),
      offline: Boolean(params?.offline),
    },
    result: sanitizeResult(result),
  };

  if (!payload.result) return;

  try {
    storage.setItem(CACHE_KEY, JSON.stringify(payload));
  } catch {
    // 저장소 접근 오류는 비치명으로 취급한다.
  }
}

function restoreLastSuccess() {
  const storage = getLocalStorage();
  if (!storage) return null;

  let raw;
  try {
    raw = storage.getItem(CACHE_KEY);
  } catch {
    return null;
  }
  if (!raw) return null;

  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }

  if (!isValidCacheRecord(parsed)) return null;

  return {
    ...parsed.result,
    cached_at: parsed.cached_at,
  };
}

function getLocalStorage() {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage ?? null;
  } catch {
    return null;
  }
}

function sanitizeResult(result) {
  if (!result || typeof result !== "object") return null;
  if (!Array.isArray(result.combos) || result.combos.length < 1) return null;

  return {
    generated_at: asString(result.generated_at),
    source: asString(result.source),
    status: asString(result.status),
    draws_used: Number(result.draws_used),
    latest_draw_no:
      result.latest_draw_no === undefined || result.latest_draw_no === null
        ? null
        : Number(result.latest_draw_no),
    latest_draw_date:
      result.latest_draw_date === undefined || result.latest_draw_date === null
        ? null
        : asString(result.latest_draw_date),
    combos: result.combos,
  };
}

function isValidCacheRecord(record) {
  if (!record || typeof record !== "object") return false;
  if (record.version !== CACHE_VERSION) return false;
  if (!isFreshTimestamp(record.cached_at)) return false;
  if (!record.params || typeof record.params !== "object") return false;
  if (!Number.isFinite(Number(record.params.n))) return false;
  if (!Number.isFinite(Number(record.params.draws))) return false;

  const result = sanitizeResult(record.result);
  return result !== null;
}

function isFreshTimestamp(value) {
  if (typeof value !== "string") return false;
  const time = Date.parse(value);
  if (Number.isNaN(time)) return false;
  return Date.now() - time <= CACHE_TTL_MS;
}

function syncOfflineBannerDataset(el, state) {
  const result = state.result && typeof state.result === "object" ? state.result : null;
  const source = result ? asString(result.source) : "";
  const shouldShowStale =
    state.status === "offline" || source === "cache" || source === "offline";

  if (!shouldShowStale) {
    clearOfflineBannerDataset(el);
    return;
  }

  const cachedAt =
    result && typeof result.cached_at === "string" ? result.cached_at : "";
  const latestDrawNo =
    result && result.latest_draw_no !== undefined && result.latest_draw_no !== null
      ? String(result.latest_draw_no)
      : "";
  const latestDrawDate =
    result && typeof result.latest_draw_date === "string" ? result.latest_draw_date : "";

  el.dataset.source = source;
  el.dataset.cachedAt = cachedAt;
  el.dataset.latestDrawNo = latestDrawNo;
  el.dataset.latestDrawDate = latestDrawDate;
  el.dataset.hasResult =
    result && Array.isArray(result.combos) && result.combos.length > 0 ? "true" : "false";
  el.dataset.message =
    el.dataset.hasResult === "true" ? OFFLINE_STALE_MESSAGE : OFFLINE_EMPTY_MESSAGE;
}

function clearOfflineBannerDataset(el) {
  delete el.dataset.source;
  delete el.dataset.cachedAt;
  delete el.dataset.latestDrawNo;
  delete el.dataset.latestDrawDate;
  delete el.dataset.hasResult;
  delete el.dataset.message;
}

function asString(value) {
  return typeof value === "string" ? value : "";
}

// 브라우저 환경에서만 자동 부트스트랩. 테스트/모듈 소비 시에는 수동 mountApp 사용.
if (typeof window !== "undefined" && typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => mountApp(), {
      once: true,
    });
  } else {
    mountApp();
  }
}
