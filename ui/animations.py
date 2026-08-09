"""Lightweight UI animations: page fade-in, stat count-up, card shadows,
window fades, staggered entrances and error shakes.

All helpers are safe to call repeatedly (e.g. rapid page switches) — previous
animations are stopped and effect updates are guarded so a replaced/deleted
Qt object can never raise.
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QTimer, QVariantAnimation
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QWidget

_ANIMATION_CACHE = {}


def _guard(fn):
    """Wrap a slot so deleted C++ objects raise a harmless RuntimeError."""

    def wrapper(*args):
        try:
            fn(*args)
        except RuntimeError:
            pass

    return wrapper


def _stop_existing(widget):
    anim = _ANIMATION_CACHE.pop(id(widget), None)
    if anim is not None:
        try:
            anim.stop()
            anim.deleteLater()
        except RuntimeError:
            pass


def fade_in(widget: QWidget, duration: int = 300):
    """Fade a widget in from transparent to opaque.

    The opacity effect is removed once the animation finishes so the widget
    keeps its native look afterwards.
    """
    _stop_existing(widget)

    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)

    anim = QVariantAnimation(widget)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setDuration(duration)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.valueChanged.connect(_guard(effect.setOpacity))
    anim.finished.connect(_guard(lambda: _clear_effect(widget, effect)))
    anim.start()
    _ANIMATION_CACHE[id(widget)] = anim
    return anim


def fade_card(widget: QWidget, duration: int = 300):
    """Fade a stat card in and restore its drop shadow afterwards."""
    _stop_existing(widget)

    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)

    def done():
        _stop_existing(widget)
        try:
            widget.setGraphicsEffect(None)
            add_shadow(widget, blur=18, y_offset=3, alpha=40)
        except RuntimeError:
            pass

    anim = QVariantAnimation(widget)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setDuration(duration)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.valueChanged.connect(_guard(effect.setOpacity))
    anim.finished.connect(_guard(done))
    anim.start()
    _ANIMATION_CACHE[id(widget)] = anim
    return anim


def rise_in(widget: QWidget, duration: int = 420, distance: int = 22):
    """Fade a widget in while its content rises up into place.

    The motion uses ``contentsMargins`` (not geometry) so it never fights the
    layout manager and is rendered by Qt's own raster engine — it shows on
    every platform.
    """
    _stop_existing(widget)

    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)

    m = widget.contentsMargins()

    def step(v):
        try:
            effect.setOpacity(v)
            widget.setContentsMargins(m.left(), m.top() + int(distance * (1 - v)), m.right(), m.bottom())
        except RuntimeError:
            pass

    def done():
        _stop_existing(widget)
        try:
            widget.setGraphicsEffect(None)
            widget.setContentsMargins(m)
        except RuntimeError:
            pass

    anim = QVariantAnimation(widget)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setDuration(duration)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.valueChanged.connect(_guard(step))
    anim.finished.connect(_guard(done))
    anim.start()
    _ANIMATION_CACHE[id(widget)] = anim
    return anim


def rise_card(widget: QWidget, duration: int = 420, distance: int = 16):
    """Fade + rise a stat card and restore its drop shadow afterwards."""
    _stop_existing(widget)

    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)

    m = widget.contentsMargins()

    def step(v):
        try:
            effect.setOpacity(v)
            widget.setContentsMargins(m.left(), m.top() + int(distance * (1 - v)), m.right(), m.bottom())
        except RuntimeError:
            pass

    def done():
        _stop_existing(widget)
        try:
            widget.setGraphicsEffect(None)
            widget.setContentsMargins(m)
            add_shadow(widget, blur=18, y_offset=3, alpha=40)
        except RuntimeError:
            pass

    anim = QVariantAnimation(widget)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setDuration(duration)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.valueChanged.connect(_guard(step))
    anim.finished.connect(_guard(done))
    anim.start()
    _ANIMATION_CACHE[id(widget)] = anim
    return anim


def stagger_fade(items, duration: int = 300, step: int = 80, func=fade_in):
    """Fade a list of widgets in one after another (staggered entrance)."""
    for i, widget in enumerate(items):
        QTimer.singleShot(i * step, _guard(lambda w=widget: func(w, duration)))


def shake(widget: QWidget, distance: int = 10, duration: int = 350):
    """Shake a top-level window horizontally — used for failed logins."""
    _stop_existing(widget)
    start = widget.pos()
    points = [
        start,
        QPoint(start.x() - distance, start.y()),
        QPoint(start.x() + distance, start.y()),
        QPoint(start.x() - distance, start.y()),
        QPoint(start.x() + distance, start.y()),
        start,
    ]
    anim = QPropertyAnimation(widget, b"pos", widget)
    anim.setDuration(duration)
    anim.setEasingCurve(QEasingCurve.Type.InOutSine)
    total = len(points) - 1
    for i, pt in enumerate(points):
        anim.setKeyValueAt(i / total, pt)
    anim.finished.connect(_guard(lambda: widget.move(start)))
    anim.start()
    _ANIMATION_CACHE[id(widget)] = anim
    return anim


def _clear_effect(widget, effect):
    if widget.graphicsEffect() is effect:
        widget.setGraphicsEffect(None)
    _ANIMATION_CACHE.pop(id(widget), None)


def count_up(label, target: int, formatter, duration: int = 800):
    """Animate a label from 0 to ``target`` using ``formatter(int)``.

    ``formatter`` receives the current integer value and returns the text.
    """
    _stop_existing(label)

    anim = QVariantAnimation(label)
    anim.setStartValue(0)
    anim.setEndValue(target)
    anim.setDuration(duration)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.valueChanged.connect(_guard(lambda v: label.setText(formatter(int(v)))))
    anim.finished.connect(_guard(lambda: label.setText(formatter(target))))
    anim.start()
    _ANIMATION_CACHE[id(label)] = anim
    return anim


def add_shadow(widget: QWidget, blur: int = 18, y_offset: int = 3, alpha: int = 40):
    """Attach a soft drop shadow to a widget (used on stat cards)."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, y_offset)
    effect.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(effect)
    return effect


def slide_in(widget: QWidget, duration: int = 220, direction: str = "left"):
    """Slide a widget in from the given direction using its geometry."""
    parent_rect = widget.parentWidget().rect() if widget.parentWidget() else None
    if parent_rect is None:
        return fade_in(widget, duration)
    start = widget.geometry()
    end = widget.geometry()
    delta = parent_rect.width() // 25
    if direction == "left":
        start.moveLeft(start.left() + delta)
    else:
        start.moveLeft(start.left() - delta)
    anim = QPropertyAnimation(widget, b"geometry", widget)
    anim.setStartValue(start)
    anim.setEndValue(end)
    anim.setDuration(duration)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.start()
    return anim
