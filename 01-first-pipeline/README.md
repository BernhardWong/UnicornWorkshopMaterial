# Demo 1 — Your first pipeline

Four scripts that build one alpha neurofeedback loop, from two nodes up
to a node and a widget you wrote yourself.

## Purpose

Everything in this demo goes after the same thing: how much alpha is
there right now. Step 1 is a standard BCI Core-8 recording -- the shape
every g.Pype program has, with the filtering that makes EEG visible at
all. Step 2 narrows to the alpha band, step 3 measures how big it is,
and step 4 puts it on a bar. Each step adds one idea and leaves
everything around it alone, so what changed is always visible.

Demo 2 is step 4 with the library's own nodes doing what you wrote here,
and with the calibration that turns microvolts into a percentage for one
particular person.

**Twenty minutes.** The budget per step is in the table below; steps 3
and 4 are where it should go.

## How to run it

A paired g.tec BCI Core-8, switched on. No network, no runtime server.
Each step opens a Qt window; close the window to end the step and return
to the prompt.

Run these from `01-first-pipeline/`, one at a time, in order:

```
..\.venv\Scripts\python.exe step1_hello_world.py
..\.venv\Scripts\python.exe step2_filtering.py
..\.venv\Scripts\python.exe step3_your_own_node.py
..\.venv\Scripts\python.exe step4_your_own_widget.py
```

To check all four without an amplifier and without opening a window:

```
..\.venv\Scripts\python.exe verify_offscreen.py
```

## What to expect

| step | min | the one new idea | on screen |
|---|---|---|---|
| 1 | 4 | the whole shape of a g.Pype program, and the filters every recording needs | one scope, eight channels of clean EEG, ±50 µV, ten seconds wide. Blinks swing the frontal channels |
| 2 | 4 | one output feeding two inputs | two scopes. Top: the EEG from step 1. Bottom: the alpha band alone, growing on eyes closed |
| 3 | 6 | a node you wrote, in the same file | two scopes. Top: the alpha band. Bottom: one lane, the alpha level in µV, rising on eyes closed |
| 4 | 6 | a widget you wrote | the alpha band, and a bar following it — up on eyes closed, down on eyes open |

**Eyes closed, then open, is the demo.** Give it five seconds each way;
the level is smoothed over a second, so it lags the eyelid slightly.
The first second of every step is the filters settling -- four cascaded
IIR filters by step 3, each with a startup transient.

Three edits to make live: in step 2 set `f_lo=15, f_hi=25` and the lower
scope stops responding, because alpha is no longer in the passband; in
step 3 set `smoothing=0.1` and the level turns twitchy, `5.0` and it
barely moves; in step 4 set `maximum=15.0` and the same signal fills
more of the bar — which is the shortcut demo 2 exists to remove.

`verify_offscreen.py` prints a line per scope and widget, and ends
with `ALL STEPS OK`.

The likeliest failure is no device found, which means the amplifier is
off or not paired. The next is `ModuleNotFoundError: No module named
'gpype'`, which means the wrong interpreter. Everything else is in
[../docs/TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md).

## Key takeaways

- Every g.Pype program is the same four moves — build the nodes,
  `p.connect(...)`, `p.start()`, `app.run()` — and `connect` is also what
  adds a node to the pipeline; there is no separate add call.
- Almost nothing has to be configured. `gp.BCICore()` takes the first
  device it finds, eight channels at 250 Hz, and the montage Fz C3 Cz C4
  Pz PO7 POz PO8; every argument in these four scripts is there because
  it differs from a default.
- Raw EEG is not worth looking at. A bandpass and the two mains notches
  are the minimum between an amplifier and a screen, and they are the
  same three in every g.tec example.
- `gp.MainApp()` must exist before any widget is built: a widget from the
  library raises a `RuntimeError` naming the fix, but a hand-written one
  that constructs its own `QWidget` first still kills the process with
  exit code 127 and no traceback.
- One output can feed several inputs, which is how steps 2 to 4 get the
  conditioned EEG and what was made of it onto the screen together.
- A custom node is one class — declare the parameters in a
  `Configuration.Keys` holder so they survive serialisation, return the
  output context from `setup()`, do the work one frame at a time in
  `step()`. `AlphaLevel` narrows eight channels to one, so its `setup()`
  has to say so; a node that changes nothing returns the input context.
- A custom widget is an `INode` and a `Widget` at once: `step()` runs on
  the pipeline thread and only stores the newest value, `_update()` draws
  it on the Qt thread at its own rate — 10 Hz for a plain widget, 20 Hz
  for a scope.

## Details

### The chain, by the end of step 4

```
   BCICore
     ▼
   Bandpass  1–40 Hz    ┐
     ▼                  │  step 1: these three, then a scope
   Bandstop 48–52 Hz    │
     ▼                  │
   Bandstop 58–62 Hz    ┘
     ▼
   Bandpass  8–12 Hz ──┬──► TimeSeriesScope    the rhythm      step 2
                       │
                       └──► AlphaLevel ──► AlphaBar         steps 3, 4
                            square,        how much
                            smooth, root   of it
```

The three conditioning filters are step 1's, and every later step keeps
them, so each script is a complete Core-8 program rather than a fragment.
They are what makes the data visible: the raw signal carries a DC offset
and a drift far larger than the EEG, plus whatever the mains is doing.
1–40 Hz keeps the brain rhythms, and the two notches cover a 50 Hz supply
and a 60 Hz one, so the same script travels. `common/alpha_pipeline.py`
uses the same three, which is why demo 2's top scope looks familiar —
and the alpha band sits inside 1–40, so the two scopes in step 2 are one
signal at two zoom levels.

`AlphaLevel` is the one arithmetic idea in the demo: alpha power is the
signal squared, and a level is that averaged over a second and rooted
back into microvolts. Demo 2 spells the same thing with library nodes —
`Equation x**2`, `MovingAverage`, two `Decimator`s — and then adds
`AlphaPercent`, which maps microvolts onto 0–100 % against a range
measured on the subject. Step 4's bar has a fixed full scale instead.

### Running without an amplifier

Each step carries the replacement as a commented-out line beside
`gp.BCICore()`:

```python
source = gp.Generator(signal_amplitude=15.0, noise_amplitude=40.0)
```

Nothing downstream changes. The bar then sits around 52 % and wanders
between 48 and 56 %, because band-limited noise has a moving envelope —
measured over 15 s on 2026-09-13, with the level at 13.1 µV. It does not
respond to anybody's eyes, which is the whole reason the steps open an
amplifier by default.

`verify_offscreen.py` substitutes exactly that source, so the check
exercises the pipelines and the two classes you wrote and never the
hardware.

### All eight channels, not three

`AlphaLevel` averages whatever arrives, and these steps hand it all
eight. Alpha is largest over the occipital cortex — PO7, POz and PO8 —
so putting

```python
select = gp.ChannelSelector(labels=["PO7", "POz", "PO8"])
```

between the alpha bandpass and `AlphaLevel` makes the bar respond more
sharply. It is left out here to keep each step to one idea; demo 2 has
it, as tick boxes you can change while the pipeline runs.

### What the headless check covers

`verify_offscreen.py` runs all four steps in child processes with Qt on
its offscreen platform and `MainApp.run` replaced by a 1.5 s Qt event
pump, so each pipeline really starts, moves frames and stops. It then
asks every scope and widget for `get_counter()`; a count above zero is
the evidence that data arrived, rather than that the script constructed
without raising. Step 3's `AlphaLevel` is checked separately as plain
arithmetic, with no Qt and no pipeline: ten seconds of a 20 µV sine must
come out at 20/√2 = 14.14 µV.

### More to show, without more code

Four scripts from g.Pype's own example library. None needs an amplifier,
and each shows a capability the four steps never touch.

| example | what it shows |
|---|---|
| `example_basic_trigger.py` | markers: arrow keys raise trigger codes and a `TriggerScope` overlays the epochs around each one, live |
| `example_basic_lsl_send.py` | an LSL outlet any LSL-aware application on the network can discover. Console, not Qt — it waits on Enter, so give it a real terminal |
| `example_paradigm_presenter.py` | a stimulus sequence defined in XML, presented on screen, with its markers on the scope beside it |
| `example_paradigm_aep_oddball.py` | an auditory oddball end to end: paradigm, UDP markers, bandpass and notches, epochs averaging up live |

They ship with neither this repository nor the installed package —
`pip install gpype` includes no examples. They live in the `gpype-dev`
checkout:

```
cd <your gpype-dev checkout>\examples
<your gpype-demos clone>\.venv\Scripts\python.exe example_basic_trigger.py
```

One to leave alone on stage: `example_paradigm_checkerboard_face.py`
opens a live amplifier — `amp = gp.BCICore()`, uncommented, at line 23 —
which will fail if another demo already holds the device. The two
`example_paradigm_aep_*.py` files look similar and are not: their
amplifier lines are commented out and a `Generator` takes over. Anything
matching `example_devices_*.py` needs its amplifier by definition.
