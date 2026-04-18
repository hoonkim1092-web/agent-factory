from __future__ import annotations

import subprocess
from pathlib import Path


def run_node(script: str) -> str:
    result = subprocess.run(
        ["node", "--input-type=module", "--eval", script],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            "Node 기반 프론트 계약 검증이 실패했습니다.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    return result.stdout


def test_offline_cache_persists_and_restores_last_success() -> None:
    script = """
      class HTMLElementMock {
        constructor(tagName = "div", ownerDocument = null) {
          this.tagName = tagName.toUpperCase();
          this.ownerDocument = ownerDocument;
          this.hidden = false;
          this.textContent = "";
          this.dataset = {};
          this.children = [];
          this.attributes = new Map();
          this.className = "";
          this.classList = {
            add: (...names) => {
              const current = new Set(this.className.split(/\\s+/).filter(Boolean));
              for (const name of names) current.add(name);
              this.className = [...current].join(" ");
            },
            remove: (...names) => {
              const current = new Set(this.className.split(/\\s+/).filter(Boolean));
              for (const name of names) current.delete(name);
              this.className = [...current].join(" ");
            },
          };
        }
        setAttribute(name, value) { this.attributes.set(name, String(value)); }
        removeAttribute(name) { this.attributes.delete(name); }
        appendChild(child) { this.children.push(child); return child; }
        append(...nodes) { this.children.push(...nodes); }
        replaceChildren(...nodes) { this.children = [...nodes]; }
        contains(node) { return this.children.includes(node); }
        querySelector() { return null; }
      }

      class HTMLButtonElementMock extends HTMLElementMock {
        constructor(tagName = "button", ownerDocument = null) {
          super(tagName, ownerDocument);
          this.disabled = false;
          this.handlers = new Map();
        }
        addEventListener(type, handler) {
          this.handlers.set(type, handler);
        }
        click() {
          const handler = this.handlers.get("click");
          return handler ? handler() : undefined;
        }
      }

      class DocumentMock {
        constructor(root, button) {
          this.readyState = "loading";
          this.root = root;
          this.button = button;
        }
        getElementById(id) {
          return id === "app" ? this.root : null;
        }
        createElement(tag) {
          return new HTMLElementMock(tag, this);
        }
        addEventListener() {}
      }

      globalThis.HTMLElement = HTMLElementMock;
      globalThis.HTMLButtonElement = HTMLButtonElementMock;

      const sessionStatus = new HTMLElementMock("p");
      const offlineBannerRoot = new HTMLElementMock("div");
      const submitButton = new HTMLButtonElementMock("button");
      const root = new HTMLElementMock("div");
      root.dataset = { status: "idle" };
      root.querySelector = (selector) => ({
        "#session-status": sessionStatus,
        "#param-panel-root": null,
        "#card-list-root": null,
        "#offline-banner-root": offlineBannerRoot,
        "#submit-button": submitButton,
        "#empty-hint": null,
      })[selector] ?? null;

      const storage = new Map();
      const localStorage = {
        getItem(key) { return storage.has(key) ? storage.get(key) : null; },
        setItem(key, value) { storage.set(key, String(value)); },
      };

      globalThis.window = { localStorage };
      globalThis.document = new DocumentMock(root, submitButton);

      const recommendation = {
        generated_at: "2026-04-18T10:00:00Z",
        source: "api",
        status: "success",
        draws_used: 500,
        latest_draw_no: 1162,
        latest_draw_date: "2026-04-18",
        combos: [{ numbers: [1, 2, 3, 4, 5, 6], score: 0.8, odd_even_ratio: "3:3", section_distribution: [1, 1, 1, 1, 2] }],
      };

      const { mountApp } = await import("./web/js/app.js");
      const { OfflineError } = await import("./web/js/api.js");

      const app = mountApp({
        root,
        fetcher: async () => recommendation,
      });
      await submitButton.click();
      app.unmount();

      const app2 = mountApp({
        root,
        fetcher: async () => {
          throw new OfflineError("오프라인");
        },
      });
      await submitButton.click();
      app2.unmount();

      const stored = JSON.parse(storage.get("lotto:last-success-recommendation"));
      console.log(JSON.stringify({
        storedVersion: stored.version,
        storedSource: stored.result.source,
        restoredStatus: root.dataset.status,
        restoredMessage: offlineBannerRoot.dataset.message,
        restoredCachedAt: offlineBannerRoot.dataset.cachedAt ? "present" : "missing",
      }));
    """
    output = run_node(script)
    assert '"storedVersion":1' in output
    assert '"storedSource":"api"' in output
    assert '"restoredStatus":"offline"' in output
    assert '"restoredCachedAt":"present"' in output


def test_offline_banner_contract_accepts_cache_and_offline_sources() -> None:
    script = """
      class HTMLElementMock {
        constructor(tagName = "div", ownerDocument = null) {
          this.tagName = tagName.toUpperCase();
          this.ownerDocument = ownerDocument;
          this.hidden = false;
          this.textContent = "";
          this.dataset = {};
          this.children = [];
          this.attributes = new Map();
          this.className = "banner-slot";
        }
        setAttribute(name, value) { this.attributes.set(name, String(value)); }
        removeAttribute(name) { this.attributes.delete(name); }
        appendChild(child) { this.children.push(child); return child; }
        append(...nodes) { this.children.push(...nodes); }
        replaceChildren(...nodes) { this.children = [...nodes]; }
      }

      class DocumentMock {
        createElement(tag) {
          return new HTMLElementMock(tag, this);
        }
      }

      globalThis.HTMLElement = HTMLElementMock;
      globalThis.document = new DocumentMock();

      const { renderOfflineBanner } = await import("./web/js/components/OfflineBanner.js");

      const offlineEl = new HTMLElementMock("div", document);
      offlineEl.dataset = {
        source: "offline",
        hasResult: "true",
        message: "현재 네트워크가 불안정해 마지막 저장 결과를 보여주는 중입니다.",
        cachedAt: "2026-04-18T10:00:00Z",
        latestDrawNo: "1162",
        latestDrawDate: "2026-04-18",
      };
      renderOfflineBanner(offlineEl, "success");

      const cacheEl = new HTMLElementMock("div", document);
      cacheEl.dataset = {
        source: "cache",
        hasResult: "false",
        message: "저장된 추천 결과가 없어 오프라인으로는 보여줄 수 없습니다.",
      };
      renderOfflineBanner(cacheEl, "offline");

      const hiddenEl = new HTMLElementMock("div", document);
      hiddenEl.dataset = { source: "api", hasResult: "true" };
      renderOfflineBanner(hiddenEl, "success");

      console.log(JSON.stringify({
        offlineHidden: offlineEl.hidden,
        offlineChildren: offlineEl.children.length,
        cacheHidden: cacheEl.hidden,
        hiddenState: hiddenEl.hidden,
      }));
    """
    output = run_node(script)
    assert '"offlineHidden":false' in output
    assert '"offlineChildren":1' in output
    assert '"cacheHidden":false' in output
    assert '"hiddenState":true' in output
