// components/ParamPanel.js — 파라미터 슬라이더 컨트롤
// 문서 언어: ko-KR / 모듈: frontend_dev_module_4 (scope 문서 §인터페이스 정의)
// - 공개 API: renderParamPanel(el, store) (시그니처 유지, 내부 구현만 치환)
// - 사용자 → 스토어: input/change 이벤트에서 setState({ params: { [name]: number } })
// - 스토어 → DOM: store.subscribe(syncFromState)로 value/aria-valuetext/<output>/disabled만 갱신
// - 1회 마운트 + 속성 갱신 정책으로 드래그 중 DOM 재생성을 금지한다.

/** @typedef {{ name: 'n' | 'draws', min: number, max: number, step: number, label: string, unit: string }} SliderSpec */

/** @type {SliderSpec[]} */
const SLIDERS = [
  { name: "n", min: 1, max: 10, step: 1, label: "추천 조합 수", unit: "개" },
  { name: "draws", min: 100, max: 500, step: 50, label: "분석 회차", unit: "회" },
];

/**
 * 파라미터 슬라이더 컨트롤을 마운트한다.
 *
 * @param {HTMLElement} el 마운트 지점
 * @param {import('../state.js').Store | {
 *   getState: () => import('../state.js').AppState,
 *   setState: (patch: Partial<import('../state.js').AppState>) => unknown,
 *   subscribe: (fn: (s: import('../state.js').AppState) => void) => () => void
 * }} store
 */
export function renderParamPanel(el, store) {
  if (!(el instanceof HTMLElement)) return;
  if (!store || typeof store.getState !== "function" || typeof store.setState !== "function") {
    return;
  }

  const form = build(el);
  const inputs = /** @type {Record<string, HTMLInputElement>} */ ({});
  const outputs = /** @type {Record<string, HTMLOutputElement>} */ ({});

  for (const spec of SLIDERS) {
    const input = form.querySelector(`input[name="${spec.name}"]`);
    const output = form.querySelector(`output[for="param-${spec.name}"]`);
    if (input instanceof HTMLInputElement) inputs[spec.name] = input;
    if (output instanceof HTMLOutputElement) outputs[spec.name] = output;
  }

  const handleInput = (event) => {
    const target = event.target;
    if (!(target instanceof HTMLInputElement)) return;
    const spec = SLIDERS.find((s) => s.name === target.name);
    if (!spec) return;
    const value = clampToStep(Number(target.value), spec);
    if (!Number.isFinite(value)) return;
    store.setState({ params: { [spec.name]: value } });
  };

  form.addEventListener("input", handleInput);
  form.addEventListener("change", handleInput);

  const syncFromState = (state) => {
    const params = state?.params ?? {};
    const loading = state?.status === "loading";
    for (const spec of SLIDERS) {
      const input = inputs[spec.name];
      const output = outputs[spec.name];
      if (!input || !output) continue;
      const raw = Number(params[spec.name]);
      const value = Number.isFinite(raw) ? clampToStep(raw, spec) : spec.min;
      const valueText = `${value}${spec.unit}`;
      // 드래그 중 포커스가 끊기지 않도록 동일 값일 때는 value를 건드리지 않는다.
      if (Number(input.value) !== value) {
        input.value = String(value);
      }
      if (input.getAttribute("aria-valuetext") !== valueText) {
        input.setAttribute("aria-valuetext", valueText);
      }
      if (output.textContent !== valueText) {
        output.textContent = valueText;
      }
      if (input.disabled !== loading) {
        input.disabled = loading;
      }
    }
  };

  if (typeof store.subscribe === "function") {
    store.subscribe(syncFromState);
  }
  syncFromState(store.getState());
}

/**
 * 폼/슬라이더 DOM을 1회만 생성한다.
 * @param {HTMLElement} el
 * @returns {HTMLFormElement}
 */
function build(el) {
  el.innerHTML = "";
  el.classList.remove("param-panel--placeholder");

  const form = document.createElement("form");
  form.className = "param-panel";
  form.setAttribute("novalidate", "");
  // 엔터 키 등으로 실제 제출이 일어나지 않도록 방어한다.
  form.addEventListener("submit", (event) => event.preventDefault());

  for (const spec of SLIDERS) {
    form.appendChild(buildGroup(spec));
  }

  el.appendChild(form);
  return form;
}

/**
 * @param {SliderSpec} spec
 */
function buildGroup(spec) {
  const group = document.createElement("fieldset");
  group.className = "param-panel__group";
  group.dataset.param = spec.name;

  const label = document.createElement("label");
  label.className = "param-panel__label";
  label.htmlFor = `param-${spec.name}`;
  label.textContent = spec.label;

  const row = document.createElement("div");
  row.className = "param-panel__row";

  const input = document.createElement("input");
  input.className = "param-panel__slider";
  input.type = "range";
  input.id = `param-${spec.name}`;
  input.name = spec.name;
  input.min = String(spec.min);
  input.max = String(spec.max);
  input.step = String(spec.step);
  input.value = String(spec.min);
  input.setAttribute("aria-valuetext", `${spec.min}${spec.unit}`);

  const output = document.createElement("output");
  output.className = "param-panel__value";
  output.setAttribute("for", `param-${spec.name}`);
  output.textContent = `${spec.min}${spec.unit}`;

  row.append(input, output);
  group.append(label, row);
  return group;
}

/**
 * 값을 [min, max]에 클램프하고 step 배수로 정렬한다.
 * @param {number} value
 * @param {SliderSpec} spec
 */
function clampToStep(value, spec) {
  if (!Number.isFinite(value)) return spec.min;
  const clamped = Math.min(spec.max, Math.max(spec.min, value));
  const steps = Math.round((clamped - spec.min) / spec.step);
  const aligned = spec.min + steps * spec.step;
  return Math.min(spec.max, Math.max(spec.min, aligned));
}
