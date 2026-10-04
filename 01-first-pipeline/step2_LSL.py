"""Receive a stream from an application that is not g.Pype.

The mirror of example_foreign_lsl_receive.py, which shows somebody
else's program reading a g.Pype stream. Here they publish one and
g.Pype reads it: another vendor's amplifier, MATLAB, a stimulus
program, a recording tool.

`foreign_source` below is that program, and nothing in it imports
gpype -- it is raw pylsl pushing random noise. It runs on a thread so
this one file is the whole demonstration; in a real session it is
somebody else's process, usually on somebody else's machine, and you
delete it and keep the rest.

Resolved by NAME rather than by type, because a workshop network
carries more than one stream of type EEG and resolving by type takes
whichever answers first.

What arrives this way is somebody else's data: LSL carries no
per-sample authentication, so a stream says what it is and cannot
prove it.

Files: this one, on its own. Nothing else to start and no second
    terminal -- unlike the example_basic_lsl_send.py /
    example_basic_lsl_receive.py pair, the publisher is inside this
    file. When the stream comes from a real instrument instead, delete
    `foreign_source` and the thread that starts it, and keep the rest.
Requires: gpype[all] (pylsl comes with the lsl extra)
Run: python example_foreign_lsl_send.py

The scope opens within a couple of seconds showing eight channels of
noise, labelled NOISE1..NOISE8 -- the labels the publisher put in the
stream description. LSL prints a wall of "Could not bind multicast
responder" warnings first on a machine with several network
interfaces; they are normal and nothing has failed.
"""
import threading
import time

import numpy as np
from pylsl import StreamInfo, StreamOutlet

import gpype as gp

STREAM_NAME = "NoiseAmp"  # what the foreign program calls itself
CHANNELS = 8
FS = 250  # Hz
BLOCK = 25  # samples per push, i.e. 10 pushes a second
AMPLITUDE = 20.0  # µV RMS


def foreign_source(stop: threading.Event) -> None:
    """The other vendor's program. No gpype below this line.

    Args:
        stop: set to end the stream.
    """
    info = StreamInfo(
        name=STREAM_NAME,
        type="EEG",
        channel_count=CHANNELS,
        nominal_srate=FS,
        channel_format="float32",
        source_id="gpype-example-noise",
    )
    # Channel labels travel in the stream description, so the receiver
    # shows names rather than CH1..CH8.
    channels = info.desc().append_child("channels")
    for index in range(CHANNELS):
        channels.append_child("channel").append_child_value(
            "label", f"NOISE{index + 1}"
        )

    outlet = StreamOutlet(info, chunk_size=BLOCK)
    rng = np.random.default_rng(7)

    # Paced against a running deadline rather than sleeping a fixed
    # interval, so the push rate does not drift away from FS.
    deadline = time.perf_counter()
    while not stop.is_set():
        chunk = rng.normal(0.0, AMPLITUDE, size=(BLOCK, CHANNELS))
        outlet.push_chunk(chunk.astype(np.float32).tolist())
        deadline += BLOCK / FS
        time.sleep(max(0.0, deadline - time.perf_counter()))


if __name__ == "__main__":

    # Start the foreign program first: LslReceiver resolves the stream
    # while it is being constructed and blocks until one appears.
    stop = threading.Event()
    threading.Thread(
        target=foreign_source, args=(stop,), daemon=True
    ).start()

    print(f"Publishing '{STREAM_NAME}' ... resolving it back into g.Pype.")

    app = gp.MainApp()
    p = gp.Pipeline()

    # channel_count and sampling_rate are read from the stream. Pass
    # them to state what you expect of it instead.
    source = gp.LslReceiver(stream_name=STREAM_NAME)

    scope = gp.TimeSeriesScope(amplitude_limit=100, time_window=10)

    p.connect(source, scope)
    app.add_widget(scope)

    p.start()
    app.run()
    p.stop()
    p.close()

    stop.set()
