// components/OfflineBanner.js — 오프라인 캐시 폴백 배너
// 문서 언어: ko-KR / 모듈: frontend_dev_module_5

/**
 * @param {HTMLElement} el 마운트 지점(slot)
 * @param {import('../state.js').AppStatus} status
 */
export function renderOfflineBanner(el, status) {
  if (!(el instanceof HTMLElement)) return;

  const source = el.dataset.source ?? "";
  const hasResult = el.dataset.hasResult === "true";
  const shouldShow = status === "offline" || source === "cache" || source === "offline";

  if (!shouldShow) {
    el.hidden = true;
    el.removeAttribute("role");
    el.removeAttribute("aria-live");
    el.className = "banner-slot";
    el.textContent = "";
    return;
  }

  el.hidden = false;
  el.setAttribute("role", "status");
  el.setAttribute("aria-live", "polite");
  el.className = "banner-slot offline-banner offline-banner--visible";

  const message =
    el.dataset.message ??
    (hasResult
      ? "현재 네트워크가 불안정해 마지막 저장 결과를 보여주는 중입니다."
      : "저장된 추천 결과가 없어 오프라인으로는 보여줄 수 없습니다.");
  const cachedAt = formatCachedAt(el.dataset.cachedAt ?? "");
  const drawMeta = formatDrawMeta(el.dataset.latestDrawNo ?? "", el.dataset.latestDrawDate ?? "");

  el.replaceChildren(buildBannerBody(message, cachedAt, drawMeta));
}

function buildBannerBody(message, cachedAt, drawMeta) {
  const section = document.createElement("section");
  section.className = "offline-banner__body";

  const messageEl = document.createElement("p");
  messageEl.className = "offline-banner__message";
  messageEl.textContent = message;
  section.appendChild(messageEl);

  if (cachedAt || drawMeta) {
    const meta = document.createElement("dl");
    meta.className = "offline-banner__meta";

    if (cachedAt) {
      meta.appendChild(buildMetaRow("저장 시각", cachedAt));
    }

    if (drawMeta) {
      meta.appendChild(buildMetaRow("기준 회차", drawMeta));
    }

    section.appendChild(meta);
  }

  return section;
}

function buildMetaRow(label, value) {
  const row = document.createElement("div");
  const dt = document.createElement("dt");
  const dd = document.createElement("dd");
  dt.textContent = label;
  dd.textContent = value;
  row.append(dt, dd);
  return row;
}

function formatCachedAt(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";

  const year = String(date.getFullYear());
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${year}-${month}-${day} ${hours}:${minutes}`;
}

function formatDrawMeta(drawNo, drawDate) {
  if (!drawNo && !drawDate) return "";
  if (drawNo && drawDate) return `${drawNo}회 / ${drawDate}`;
  if (drawNo) return `${drawNo}회`;
  return drawDate;
}
