"""Step 3 -- a node of your own: how much alpha is there?

Since step 2: the alpha band feeds a node written in this file. It
squares the signal, smooths the result over a second and takes the root
-- alpha amplitude in microvolts, one channel instead of eight. Once
written it is an ordinary node: it connects the same way, it serialises
into a stored document, and nothing downstream can tell it apart from a
node that shipped with the library.

A node is one class and three things to fill in:

1. Parameters, declared in a ``Configuration.Keys`` holder. One that is
   not declared there is dropped when the pipeline is serialised.
2. ``setup()``, which is handed the input's rate, width and frame size
   and returns what the output looks like. This one narrows eight
   channels to one, so it has to say so.
3. ``step()``, the work, one frame at a time.

What you see: on top the alpha band. Below it a single lane that rises
when the subject closes their eyes. Set smoothing=0.1 and the level
gets twitchy; set 5.0 and it barely moves.

Run it:
    ../.venv/Scripts/python.exe step3_your_own_node.py
"""

import gpype as gp
import numpy as np

PORT_IN = gp.Constants.Defaults.PORT_IN
PORT_OUT = gp.Constants.Defaults.PORT_OUT
Keys = gp.Constants.Keys


class AlphaLevel(gp.IONode):
    """Alpha amplitude in microvolts, averaged over the channels."""

    class Configuration(gp.IONode.Configuration):
        """Parameters, declared so they survive serialisation."""

        class Keys(gp.IONode.Configuration.Keys):
            """Keys for AlphaLevel."""

            #: Smoothing time constant in seconds.
            SMOOTHING = "smoothing"

    def __init__(self, smoothing: float = 1.0, **kwargs):
        """Initialize the alpha level estimator.

        Args:
            smoothing: Time constant in seconds.
            **kwargs: Additional arguments for IONode.

        Raises:
            ValueError: If smoothing is not positive.
        """
        if smoothing <= 0:
            raise ValueError(f"smoothing must be positive, got {smoothing}")
        super().__init__(smoothing=smoothing, **kwargs)
        self._weight = 1.0
        self._power = 0.0

    def setup(self, data: dict, port_metadata_in: dict) -> dict:
        """Declare the one output channel and size the smoothing.

        Args:
            data: The first input frames.
            port_metadata_in: Context of every input port.

        Returns:
            dict: Context of every output port.
        """
        context = port_metadata_in[PORT_IN]

        # A frame is counted in samples, the time constant in seconds.
        # The sampling rate converts between them, and it is knowable
        # here and nowhere earlier.
        seconds_per_frame = (
            context[Keys.FRAME_SIZE] / context[Keys.SAMPLING_RATE]
        )
        smoothing = self.config[self.Configuration.Keys.SMOOTHING]

        # One-pole smoother: how far one frame moves the level towards
        # what it just measured. Capped at 1 so a frame longer than the
        # time constant follows the input instead of overshooting it.
        self._weight = min(1.0, seconds_per_frame / smoothing)
        self._power = 0.0

        # Eight channels in, one out: nothing downstream can guess
        # that, so the output context has to say it.
        metadata = super().setup(data, port_metadata_in)
        out = metadata[PORT_OUT]
        out[Keys.CHANNEL_COUNT] = 1
        out[Keys.CHANNEL_ROLES] = [gp.Constants.ChannelRoles.SIGNAL]
        out[Keys.CHANNEL_LABELS] = ["alpha"]
        out[Keys.CHANNEL_UNITS] = ["uV"]
        return metadata

    def step(self, data: dict) -> dict:
        """Fold one frame into the running level.

        Args:
            data: Input frames by port name.

        Returns:
            dict: Output frames by port name.
        """
        frame = data[PORT_IN]

        # Mean square over every sample and channel of the frame: the
        # power in the alpha band, one number for the whole frame.
        power = float(np.mean(np.square(frame)))

        # Fold that into the running power, self._weight of the way.
        # This one line is the smoothing, and the only state kept.
        self._power += self._weight * (power - self._power)

        # Root of power is amplitude, so the output is back in the
        # microvolts the input came in -- one value, held across the
        # frame, because the level is defined per frame, not per sample.
        return {
            PORT_OUT: np.full(
                (frame.shape[0], 1),
                np.sqrt(self._power),
                dtype=gp.Constants.DATA_TYPE,
            )
        }


if __name__ == "__main__":

    app = gp.MainApp(caption="Step 3 -- Your Own Node")

    with gp.Pipeline() as p:

        source = gp.BCICore()

        # No amplifier on this machine? Swap in a synthetic signal:
        #     source = gp.Generator(signal_amplitude=15.0,
        #                           noise_amplitude=40.0)

        eeg_band = gp.Bandpass(f_lo=1, f_hi=40)
        notch50 = gp.Bandstop(f_lo=48, f_hi=52)
        notch60 = gp.Bandstop(f_lo=58, f_hi=62)
        alpha_band = gp.Bandpass(f_lo=8, f_hi=12)

        # Your node, wired in exactly like a built-in one.
        level = AlphaLevel(smoothing=1.0)

        alpha = gp.TimeSeriesScope(name="Alpha 8-12 Hz")
        amount = gp.TimeSeriesScope(
            amplitude_limit=30, name="Alpha level (uV)"
        )

        p.connect(source, eeg_band)
        p.connect(eeg_band, notch50)
        p.connect(notch50, notch60)
        p.connect(notch60, alpha_band)

        p.connect(alpha_band, alpha)
        p.connect(alpha_band, level)
        p.connect(level, amount)

        app.add_widget(alpha)
        app.add_widget(amount)

        p.start()
        app.run()  # blocks until the window is closed
        p.stop()
