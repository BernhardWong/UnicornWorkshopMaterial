"""Step 4 -- a widget of your own: the alpha bar.

Since step 3: the level drives a bar instead of a scope. The node is
step 3's, imported unchanged -- this file is only the widget.

A widget is two things at once, and that is the whole idea:

* an ``INode``, so the pipeline can connect to it and hand it frames;
* a ``Widget``, so the application can put it on screen.

``step()`` runs on the pipeline thread and only stores what arrived.
``_update()`` runs on the Qt thread, ten times a second, and draws it.
Keeping those apart is what stops a slow repaint from stalling the
pipeline.

What you see: the alpha band, and a bar that follows how much of it
there is -- up on eyes closed, down on eyes open. `maximum` is the one
number to turn if the bar pins at the top or never leaves the bottom;
demo 2 measures it on the subject instead of asking you to type it.

Run it:
    ../.venv/Scripts/python.exe step4_your_own_widget.py
"""

import os
import sys

import gpype as gp
import numpy as np
from gpype.frontend.widgets.base.widget import Widget
from PySide6.QtWidgets import QApplication, QProgressBar, QWidget

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from step5_alpha_level import AlphaLevel  # noqa: E402

PORT_IN = gp.Constants.Defaults.PORT_IN

#: A QProgressBar counts in integers; 1000 steps slide, 100 tick.
STEPS = 1000


class AlphaBar(gp.INode, Widget):
    """A bar showing the newest level against a full-scale value.

    Args:
        maximum: Level in microvolts that fills the bar.
        name: The title Qt draws above the widget.
        **kwargs: Passed to :class:`INode`.
    """

    def __init__(self, maximum: float = 25.0, name: str = "Alpha", **kwargs):
        # Qt takes the process down, with no traceback, if a QWidget is
        # built before a QApplication exists. The container below is an
        # argument to Widget.__init__, so it is constructed before that
        # call can check anything -- hence the guard here.
        if QApplication.instance() is None:
            raise RuntimeError(
                "Build AlphaBar after gp.MainApp(), which creates the "
                "QApplication a QWidget needs."
            )

        self._maximum = float(maximum)
        self._level = None

        gp.INode.__init__(
            self, ports=[gp.IPort.Configuration(name=PORT_IN)], **kwargs
        )
        # `widget=` is the container the framework puts its titled box
        # in, so it is an empty QWidget; the bar goes into the box's
        # layout, which Widget.__init__ leaves in self._layout.
        Widget.__init__(self, widget=QWidget(), name=name)

        self._bar = QProgressBar()
        self._bar.setRange(0, STEPS)
        self._bar.setValue(0)
        self._bar.setMinimumHeight(60)
        self._layout.addWidget(self._bar)

    def step(self, data: dict) -> None:
        """Store the newest level. Runs on the pipeline thread.

        Args:
            data: One frame per input port, keyed by port name.
        """
        frame = data[PORT_IN]
        if frame is not None and len(frame):
            self._level = float(np.asarray(frame)[-1, 0])

    def _update(self) -> None:
        """Draw what step() last stored. Runs on the Qt thread."""
        if self._level is None:
            return
        fraction = min(1.0, self._level / self._maximum)
        self._bar.setValue(int(round(fraction * STEPS)))
        self._bar.setFormat(f"{self._level:.1f} uV")


if __name__ == "__main__":

    app = gp.MainApp(caption="Step 4 -- Your Own Widget")

    with gp.Pipeline() as p:

        source = gp.BCICore()

        # No amplifier on this machine? Swap in a synthetic signal:
        #     source = gp.Generator(signal_amplitude=15.0,
        #                           noise_amplitude=40.0)

        eeg_band = gp.Bandpass(f_lo=1, f_hi=40)
        notch50 = gp.Bandstop(f_lo=48, f_hi=52)
        notch60 = gp.Bandstop(f_lo=58, f_hi=62)
        alpha_band = gp.Bandpass(f_lo=8, f_hi=12)

        level = AlphaLevel(smoothing=1.0)

        alpha = gp.TimeSeriesScope(name="Alpha 8-12 Hz")
        bar = AlphaBar(maximum=25.0, name="Alpha level")

        p.connect(source, eeg_band)
        p.connect(eeg_band, notch50)
        p.connect(notch50, notch60)
        p.connect(notch60, alpha_band)

        p.connect(alpha_band, alpha)
        p.connect(alpha_band, level)
        p.connect(level, bar)

        app.add_widget(alpha)
        app.add_widget(bar)

        p.start()
        app.run()  # blocks until the window is closed
        p.stop()
