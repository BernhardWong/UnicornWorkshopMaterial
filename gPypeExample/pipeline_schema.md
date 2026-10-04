# Pipeline Schema

```mermaid
flowchart LR
    subgraph Signal[Signal generation and filtering]
        amp[Generator<br/>250 Hz, 8 channels<br/>10 Hz sine, amplitude 15, noise 10] --> bandpass[Bandpass<br/>1-30 Hz]
        bandpass --> notch50[Bandstop<br/>48-52 Hz]
        notch50 --> notch60[Bandstop<br/>58-62 Hz]
    end

    subgraph Inputs[Trigger and keyboard inputs]
        trigReceiver[UDPReceiver<br/>trigger events]
        keyboard[Keyboard<br/>key events]
    end

    subgraph Merge[Data routing]
        routerScope[Router: scope<br/>in1 / in2 / in3]
        routerLsl[Router: LSL<br/>in1 / in2 / in3]
    end

    subgraph Outputs[Pipeline outputs]
        scope[TimeSeriesScope<br/>10 s window, amplitude +/-50]
        lsl["LSLSender<br/>stream: EEG"]
        trigger[Trigger<br/>EEG + trigger events<br/>pre: 0.2 s, post: 0.7 s]
        triggerScope["TriggerScope<br/>amplitude +/-25<br/>channel 1 only (index 0)"]
    end

    notch60 -->|in1| routerScope
    trigReceiver -->|in2| routerScope
    keyboard -->|in3| routerScope
    routerScope --> scope

    notch60 -->|in1| routerLsl
    trigReceiver -->|in2| routerLsl
    keyboard -->|in3| routerLsl
    routerLsl --> lsl

    notch60 -->|filtered EEG data| trigger
    trigReceiver -->|trigger input| trigger
    trigger -->|triggered EEG data| triggerScope

    subgraph UI[Application widgets]
        app[MainApp]
        presenter[ParadigmPresenter<br/>AEPSingleStim.xml]
    end
    app -. contains .-> presenter
    app -. contains .-> scope
    app -. contains .-> triggerScope
    presenter -. "runtime UDP trigger relationship<br/>(not a p.connect call)" .-> trigReceiver

    classDef source fill:#e8f1fa,stroke:#35658a,color:#172b3a
    classDef processing fill:#edf4e8,stroke:#5d7b45,color:#26351e
    classDef output fill:#fff2dc,stroke:#a87522,color:#49350e
    classDef ui fill:#f2eaf6,stroke:#79528d,color:#35233e

    class amp,trigReceiver,keyboard source
    class bandpass,notch50,notch60,routerScope,routerLsl,trigger processing
    class scope,lsl,triggerScope output
    class app,presenter ui
```

Solid arrows show the `p.connect(...)` signal paths. Both routers merge their three inputs: filtered EEG from `notch60`, UDP triggers, and keyboard events. The scope router feeds `TimeSeriesScope`; the LSL router feeds `LSLSender`. The trigger detector receives filtered EEG and UDP trigger events; its triggered EEG output feeds `TriggerScope`, which displays only channel index 0 (channel 1). The generator is configured for 250 Hz and 8 channels. Dotted arrows show application relationships, not pipeline connections.

The time-series scope uses a 10-second window with an amplitude limit of 50 and marks the stimulus on channel 8 and the M key on channel 9. `TriggerScope` uses an amplitude limit of 25. The trigger detector targets value 1 and captures 0.2 seconds before and 0.7 seconds after each trigger.
