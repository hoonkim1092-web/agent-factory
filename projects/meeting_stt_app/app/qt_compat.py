"""Qt 호환 셰임 — PySide6 유무와 무관하게 동일한 인터페이스를 제공한다.

배포 머신(PySide6 설치)에서는 PySide6.QtCore의 실제 ``QObject``/``Signal``/
``QThread``를 그대로 재노출한다. PySide6가 없는 헤드리스 검증 환경에서는
같은 인터페이스를 가진 순수 파이썬 스텁으로 대체한다.

이 셰임의 목적은 scope 계약의 완료 게이트("전 모듈 import 성공(헤드리스)",
"헤드리스 셀프테스트로 배선 단선 차단")를 PySide6 미설치 환경에서도
통과시키는 것이다. DSP/큐/배선 로직은 numpy만으로 검증 가능해진다.

스텁은 의도적으로 최소 구현이며, 실제 Qt 이벤트 루프·스레드 친화성(thread
affinity)·메타오브젝트 기능은 제공하지 않는다. 실제 동시성 보장은 배포
머신의 PySide6 경로에서만 유효하다.
"""
from __future__ import annotations

import threading

try:
    from PySide6.QtCore import QObject, QThread, Signal  # noqa: F401

    HAS_QT = True
except Exception:  # pragma: no cover - 배포 머신에서는 이 분기로 가지 않는다
    HAS_QT = False

    class _BoundSignal:
        """인스턴스 단위로 바인딩되는 스텁 시그널."""

        def __init__(self) -> None:
            self._slots: list = []

        def connect(self, slot) -> None:
            self._slots.append(slot)

        def disconnect(self, slot=None) -> None:
            if slot is None:
                self._slots.clear()
            elif slot in self._slots:
                self._slots.remove(slot)

        def emit(self, *args) -> None:
            # 슬롯 실행 중 connect/disconnect가 일어나도 안전하도록 복사본 순회
            for slot in list(self._slots):
                slot(*args)

    class Signal:
        """PySide6 ``Signal``을 흉내 내는 디스크립터.

        클래스 속성으로 선언되며(``foo = Signal(float)``), 인스턴스별로 독립된
        ``_BoundSignal``을 lazily 생성한다.
        """

        def __init__(self, *types) -> None:
            self._types = types
            self._name = "signal"

        def __set_name__(self, owner, name) -> None:
            self._name = name

        def __get__(self, obj, objtype=None):
            if obj is None:
                return self
            attr = f"__stub_signal_{self._name}"
            sig = obj.__dict__.get(attr)
            if sig is None:
                sig = _BoundSignal()
                obj.__dict__[attr] = sig
            return sig

    class QObject:
        """PySide6 ``QObject``의 최소 스텁 (부모 인자 무시)."""

        def __init__(self, *args, **kwargs) -> None:
            pass

    class QThread(QObject):
        """``QThread``의 최소 스텁 — 표준 라이브러리 스레드로 ``run()``을 실행한다.

        실제 Qt 스레드 친화성은 없지만, ``start()`` 시 별도 스레드에서 ``run()``을
        호출하므로 헤드리스 셀프테스트에서 워커 스레드 동작을 검증할 수 있다.
        """

        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            self._thread: threading.Thread | None = None

        def start(self) -> None:
            self._thread = threading.Thread(target=self.run, daemon=True)
            self._thread.start()

        def run(self) -> None:  # 서브클래스에서 오버라이드
            pass

        def wait(self, timeout_ms: int | None = None) -> bool:
            if self._thread is None:
                return True
            self._thread.join(None if timeout_ms is None else timeout_ms / 1000.0)
            return not self._thread.is_alive()

        def quit(self) -> None:
            pass

        def isRunning(self) -> bool:
            return self._thread is not None and self._thread.is_alive()


__all__ = ["QObject", "QThread", "Signal", "HAS_QT"]
