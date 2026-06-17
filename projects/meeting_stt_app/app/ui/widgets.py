"""커스텀 위젯(M4) — 레벨 미터.

PySide6.QtWidgets가 없으면 모듈 import는 성공하되, 위젯 인스턴스화 시
명시적 오류를 낸다(헤드리스 기동 보장).
"""
from __future__ import annotations

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPainter
    from PySide6.QtWidgets import QWidget

    HAS_QT_WIDGETS = True
except Exception:  # pragma: no cover - 배포 머신에서는 이 분기로 가지 않는다
    HAS_QT_WIDGETS = False


# 레벨 미터 색 임계 (RMS 0~1)
_LEVEL_GREEN_MAX = 0.5
_LEVEL_YELLOW_MAX = 0.8


if HAS_QT_WIDGETS:

    class LevelMeter(QWidget):
        """마이크/시스템오디오 입력 RMS 레벨을 가로 막대로 표시하는 위젯."""

        def __init__(self, parent=None) -> None:
            super().__init__(parent)
            self._level = 0.0
            self.setMinimumHeight(18)

        def set_level(self, level: float) -> None:
            """0~1 RMS 레벨을 갱신하고 다시 그린다."""
            self._level = max(0.0, min(1.0, float(level)))
            self.update()

        def paintEvent(self, event) -> None:  # noqa: N802 - Qt 시그니처
            painter = QPainter(self)
            rect = self.rect()
            painter.fillRect(rect, QColor(40, 40, 40))
            width = int(rect.width() * self._level)
            if self._level < _LEVEL_GREEN_MAX:
                color = QColor(60, 200, 80)
            elif self._level < _LEVEL_YELLOW_MAX:
                color = QColor(220, 200, 60)
            else:
                color = QColor(220, 70, 60)
            painter.fillRect(0, 0, width, rect.height(), color)
            painter.end()

else:

    class LevelMeter:  # type: ignore[no-redef]
        """PySide6 미설치 환경용 플레이스홀더."""

        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError("LevelMeter는 PySide6 설치 환경에서만 사용할 수 있습니다.")
