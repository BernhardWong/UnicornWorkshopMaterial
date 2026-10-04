"""Record a subject once, then change the analysis and run it again.

Run 1 -- record the amplifier and your keypresses::

    python step3_reprocess.py --save-as rest

Then EDIT this file, at the block marked RUN 2, and run it again on
what you just recorded. Run 1 prints that command when it ends,
stamp and all, so you never have to guess it::

    python step3_reprocess.py --load-from rest_<stamp>

No amplifier, no subject, no Bluetooth the second time: ``load_from``
replaces each source's core and nothing downstream can tell. Only the
sources are recorded. Everything after them is built fresh on every
run, which is exactly why editing the pipeline in between works.

Requires: a BCI Core-4/8 to record, and gpype[all]
"""
from pathlib import Path

import gpype as gp

if __name__ == "__main__":

    app = gp.MainApp()
    p = gp.Pipeline()

    # === SOURCES -- the only things that are recorded ===
    # Name them: the name is the file each is filed under, eeg.h5 and
    # keys.h5, and it is how the replay pairs them up again.
    source = gp.BCICore(name="eeg")
    keyboard = gp.Keyboard(name="keys")

    # === ANALYSIS -- rebuilt on every run, never recorded ===
    bandpass = gp.Bandpass(f_lo=1, f_hi=30)
    notch = gp.Bandstop(f_lo=48, f_hi=52)

    # --- RUN 2: uncomment these two lines to extract alpha ---
    # alpha = gp.Bandpass(f_lo=8, f_hi=12)
    # p.connect(notch, alpha)

    # 8 EEG channels + 1 key channel, so the markers land on channel 8.
    merger = gp.Router(input_channels=[gp.Router.ALL, gp.Router.ALL])

    mk = gp.TimeSeriesScope.Markers
    scope = gp.TimeSeriesScope(
        amplitude_limit=30,
        time_window=10,
        markers=[
            mk(color="r", label="up", channel=8, value=38),
            mk(color="g", label="right", channel=8, value=39),
            mk(color="b", label="down", channel=8, value=40),
            mk(color="k", label="left", channel=8, value=37),
        ],
    )

    p.connect(source, bandpass)
    p.connect(bandpass, notch)
    p.connect(notch, merger["in1"])
    # --- RUN 2: replace the line above with this one ---
    # p.connect(alpha, merger["in1"])
    p.connect(keyboard, merger["in2"])
    p.connect(merger, scope)

    app.add_widget(scope)

    p.start()
    app.run()
    p.stop()
    p.close()

    # The run directory carries a timestamp so a second recording
    # never overwrites the first -- which is exactly why the stamp
    # has to be looked up rather than guessed. Hand over the
    # command that replays what was just recorded.
    launch = gp.LaunchConfig.get()
    if launch.save_as:
        stem = Path(launch.save_as)
        runs = sorted(stem.parent.glob(stem.name + "_*"))
        if runs:
            print()
            print(f"Recorded to {runs[-1]}")
            print("Replay it with:")
            print(f"  python {Path(__file__).name} "
                  f"--load-from {runs[-1]}")
