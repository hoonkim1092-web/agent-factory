// components/CardList.js — 조합 카드 시각화 컴포넌트
// 문서 언어: ko-KR / 모듈: frontend_dev_module_3 (scope 문서 §인터페이스/§구현 순서)
// 공개 API(renderCardList)의 시그니처는 module_2 계약과 동일. 내부 구현만 실제 카드 UI로 치환한다.

/**
 * @typedef {{
 *   numbers: number[],
 *   score: number,
 *   odd_even_ratio: string,
 *   section_distribution: number[]
 * }} RecommendationCombo
 */

/**
 * 추천 조합 리스트를 카드 UI로 렌더한다.
 * @param {HTMLElement} el 마운트 지점
 * @param {RecommendationCombo[]} combos
 * @returns {void}
 */
export function renderCardList(el, combos) {
  if (!(el instanceof HTMLElement)) return;
  el.innerHTML = "";

  if (!Array.isArray(combos)) return;

  if (combos.length === 0) {
    const hint = document.createElement("p");
    hint.className = "empty-hint";
    hint.textContent = "추천 결과가 없습니다.";
    el.appendChild(hint);
    return;
  }

  const list = document.createElement("ol");
  list.className = "card-list";

  combos.forEach((combo, index) => {
    const item = document.createElement("li");
    item.className = "card-list__item";
    item.appendChild(buildCombo(combo, index));
    list.appendChild(item);
  });

  el.appendChild(list);
}

/**
 * 조합 1개에 대한 카드(button) 엘리먼트를 조립한다.
 * @param {RecommendationCombo} combo
 * @param {number} index
 * @returns {HTMLButtonElement}
 */
function buildCombo(combo, index) {
  const summaryId = `combo-card-summary-${index}`;
  const detailId = `combo-card-detail-${index}`;

  const button = document.createElement("button");
  button.type = "button";
  button.className = "combo-card";
  button.setAttribute("aria-expanded", "false");
  button.setAttribute("aria-controls", detailId);
  button.setAttribute("aria-labelledby", summaryId);

  const summary = document.createElement("span");
  summary.id = summaryId;
  summary.className = "combo-card__summary";
  summary.appendChild(renderBalls(combo?.numbers));
  summary.appendChild(renderScoreText(combo?.score));

  const detail = document.createElement("span");
  detail.id = detailId;
  detail.className = "combo-card__detail";
  detail.hidden = true;
  detail.appendChild(renderGauge(combo?.score));
  detail.appendChild(renderRatioBadge(combo?.odd_even_ratio));
  detail.appendChild(renderSections(combo?.section_distribution));

  button.appendChild(summary);
  button.appendChild(detail);
  button.addEventListener("click", () => toggleExpanded(button, detail));
  button.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      toggleExpanded(button, detail);
    }
  });

  return button;
}

/**
 * 접힘/펼침 상태를 aria-expanded 와 hidden 속성으로 동기화한다.
 * @param {HTMLButtonElement} button
 * @param {HTMLElement} detail
 */
function toggleExpanded(button, detail) {
  const expanded = button.getAttribute("aria-expanded") === "true";
  const next = !expanded;
  button.setAttribute("aria-expanded", next ? "true" : "false");
  detail.hidden = !next;
}

/**
 * 6개 번호를 번호 공(ball) 목록으로 렌더한다.
 * 비정상 입력(배열 아님/길이 상이)은 빈 목록으로 방어한다.
 * @param {unknown} numbers
 * @returns {HTMLUListElement}
 */
function renderBalls(numbers) {
  const ul = document.createElement("ul");
  ul.className = "combo-card__balls";
  ul.setAttribute("aria-label", "추천 번호");

  const list = Array.isArray(numbers)
    ? [...numbers].filter((n) => Number.isFinite(n)).sort((a, b) => a - b)
    : [];

  for (const n of list) {
    const li = document.createElement("li");
    li.className = `combo-card__ball combo-card__ball--${bucketOf(n)}`;
    li.textContent = String(Math.trunc(n));
    ul.appendChild(li);
  }

  return ul;
}

/**
 * 번호(1..45)를 색상 버킷(b1..b5)으로 매핑한다.
 * @param {number} n
 * @returns {"b1"|"b2"|"b3"|"b4"|"b5"|"unknown"}
 */
function bucketOf(n) {
  if (!Number.isFinite(n)) return "unknown";
  const v = Math.trunc(n);
  if (v >= 1 && v <= 10) return "b1";
  if (v >= 11 && v <= 20) return "b2";
  if (v >= 21 && v <= 30) return "b3";
  if (v >= 31 && v <= 40) return "b4";
  if (v >= 41 && v <= 45) return "b5";
  return "unknown";
}

/**
 * 요약 줄에 노출할 점수 텍스트를 만든다.
 * @param {unknown} score
 * @returns {HTMLSpanElement}
 */
function renderScoreText(score) {
  const span = document.createElement("span");
  span.className = "combo-card__score-text";
  span.textContent = `점수 ${formatScore(score)}`;
  return span;
}

/**
 * 0..1 범위 점수를 소수 두 자리 고정 문자열로 변환한다. 범위 밖이면 "--".
 * @param {unknown} score
 * @returns {string}
 */
function formatScore(score) {
  if (typeof score !== "number" || !Number.isFinite(score)) return "--";
  if (score < 0 || score > 1) return "--";
  return score.toFixed(2);
}

/**
 * 점수 게이지(role=meter)를 만든다. 잘못된 값은 0으로 클램프해 렌더한다.
 * @param {unknown} score
 * @returns {HTMLDivElement}
 */
function renderGauge(score) {
  const gauge = document.createElement("div");
  gauge.className = "combo-card__score-gauge";
  gauge.setAttribute("role", "meter");
  gauge.setAttribute("aria-valuemin", "0");
  gauge.setAttribute("aria-valuemax", "1");

  const safe = clamp01(score);
  gauge.setAttribute("aria-valuenow", safe.toFixed(2));

  const fill = document.createElement("span");
  fill.className = "combo-card__score-fill";
  fill.style.width = `${Math.round(safe * 100)}%`;
  gauge.appendChild(fill);
  return gauge;
}

/**
 * @param {unknown} value
 * @returns {number} 0..1 로 클램프된 값 (비수치는 0)
 */
function clamp01(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return 0;
  if (value < 0) return 0;
  if (value > 1) return 1;
  return value;
}

/**
 * 홀짝 비율 배지를 만든다. 잘못된 형식이어도 원문을 그대로 보여주며 배지 클래스만 적용한다.
 * @param {unknown} ratio
 * @returns {HTMLSpanElement}
 */
function renderRatioBadge(ratio) {
  const badge = document.createElement("span");
  badge.className = "combo-card__ratio";
  badge.setAttribute("aria-label", "홀짝 비율");
  badge.textContent = typeof ratio === "string" && ratio.length > 0 ? ratio : "--";
  return badge;
}

/**
 * 구간 분포 5칸을 히스토그램(높이/불투명도 매핑)으로 렌더한다.
 * 길이가 5가 아니면 누락 칸은 0으로 채우고, 초과분은 절삭한다.
 * @param {unknown} distribution
 * @returns {HTMLOListElement}
 */
function renderSections(distribution) {
  const ol = document.createElement("ol");
  ol.className = "combo-card__sections";
  ol.setAttribute("aria-label", "구간 분포");

  const raw = Array.isArray(distribution) ? distribution.slice(0, 5) : [];
  const cells = Array.from({ length: 5 }, (_, i) => {
    const v = raw[i];
    return typeof v === "number" && Number.isFinite(v) && v >= 0 ? Math.trunc(v) : 0;
  });
  const max = Math.max(1, ...cells);

  for (const v of cells) {
    const li = document.createElement("li");
    li.className = "combo-card__section";
    li.style.setProperty("--h", String(v / max));
    li.textContent = String(v);
    ol.appendChild(li);
  }

  return ol;
}
