# NIGHTWATCH Architecture

System architecture documentation with diagrams.

## System Overview

```mermaid
flowchart TB
    subgraph User["User Interface"]
        Voice["Voice Input"]
        Display["Status Display"]
    end

    subgraph VoicePipeline["Voice Pipeline"]
        STT["Whisper STT"]
        LLM["LLM Processor"]
        TTS["Piper TTS"]
    end

    subgraph Orchestrator["Orchestrator"]
        ToolExec["Tool Executor"]
        EventBus["Event Bus"]
        StateManager["State Manager"]
    end

    subgraph Services["Observatory Services"]
        Mount["Mount Control"]
        Weather["Weather Service"]
        Safety["Safety Monitor"]
        Catalog["Catalog Service"]
        Ephemeris["Ephemeris Service"]
        Camera["Camera Service"]
        Focus["Focus Service"]
        Guide["Guiding Service"]
    end

    subgraph Hardware["Hardware Layer"]
        OnStepX["OnStepX Mount"]
        Ecowitt["Ecowitt WS90"]
        ZWO["ZWO Camera"]
        PHD2["PHD2 Guider"]
    end

    Voice --> STT
    STT --> LLM
    LLM --> ToolExec
    ToolExec --> EventBus
    EventBus --> Services
    Services --> Hardware
    TTS --> Display
    ToolExec --> TTS
    Safety --> EventBus
```

## Voice Command Flow

```mermaid
sequenceDiagram
    participant User
    participant STT as Whisper STT
    participant LLM as LLM Processor
    participant Tools as Tool Executor
    participant Safety as Safety Monitor
    participant Mount as Mount Control
    participant TTS as Piper TTS

    User->>STT: "Slew to Andromeda"
    STT->>LLM: transcript
    LLM->>LLM: Parse intent
    LLM->>Tools: goto_object(Andromeda)
    Tools->>Safety: Check safety
    Safety-->>Tools: Safe to slew
    Tools->>Mount: slew_to_coordinates(ra, dec)
    Mount-->>Tools: Slewing started
    Tools->>TTS: "Slewing to Andromeda Galaxy"
    TTS->>User: Audio response
```

## Safety System Architecture

```mermaid
flowchart LR
    subgraph Inputs["Safety Inputs"]
        Weather["Weather Data"]
        Mount["Mount Status"]
        Enclosure["Enclosure Status"]
        Manual["Manual Override"]
    end

    subgraph SafetyMonitor["Safety Monitor"]
        Evaluator["Condition Evaluator"]
        Thresholds["Threshold Config"]
        Holdoffs["Holdoff Timers"]
        Vetoes["Veto Manager"]
    end

    subgraph Actions["Safety Actions"]
        Block["Block Commands"]
        Park["Emergency Park"]
        Close["Close Enclosure"]
        Alert["Send Alerts"]
    end

    Weather --> Evaluator
    Mount --> Evaluator
    Enclosure --> Evaluator
    Manual --> Evaluator
    Thresholds --> Evaluator
    Evaluator --> Holdoffs
    Evaluator --> Vetoes
    Vetoes --> Block
    Vetoes --> Park
    Vetoes --> Close
    Vetoes --> Alert
```

## Service Communication

```mermaid
flowchart TB
    subgraph Orchestrator
        EventBus["Event Bus"]
    end

    subgraph Services
        Mount["Mount Service"]
        Weather["Weather Service"]
        Safety["Safety Monitor"]
        Catalog["Catalog Service"]
    end

    Mount -->|mount.slewing| EventBus
    Mount -->|mount.parked| EventBus
    Weather -->|weather.update| EventBus
    Weather -->|weather.rain| EventBus
    Safety -->|safety.unsafe| EventBus
    Safety -->|safety.emergency| EventBus

    EventBus -->|Subscribe| Mount
    EventBus -->|Subscribe| Weather
    EventBus -->|Subscribe| Safety
    EventBus -->|Subscribe| Catalog
```

## Data Flow Architecture

```mermaid
flowchart LR
    subgraph External["External Data"]
        WeatherAPI["Weather Station"]
        MountAPI["Mount Controller"]
        CameraAPI["Camera"]
    end

    subgraph Services["Services Layer"]
        WeatherSvc["Weather Service"]
        MountSvc["Mount Service"]
        CameraSvc["Camera Service"]
    end

    subgraph Core["Core Layer"]
        SafetySvc["Safety Monitor"]
        Orchestrator["Orchestrator"]
    end

    subgraph Storage["Storage"]
        Config["Configuration"]
        Catalog["Catalog DB"]
        Logs["Log Files"]
    end

    WeatherAPI --> WeatherSvc
    MountAPI --> MountSvc
    CameraAPI --> CameraSvc

    WeatherSvc --> SafetySvc
    MountSvc --> Orchestrator
    CameraSvc --> Orchestrator
    SafetySvc --> Orchestrator

    Config --> Services
    Catalog --> Orchestrator
    Orchestrator --> Logs
```

## Emergency Response Flow

```mermaid
sequenceDiagram
    participant Weather as Weather Service
    participant Safety as Safety Monitor
    participant Mount as Mount Control
    participant Enclosure as Enclosure
    participant Alert as Alert System

    Weather->>Safety: Rain detected!
    Safety->>Safety: Evaluate: CRITICAL
    Safety->>Alert: Send emergency alert
    Safety->>Mount: Emergency park
    Mount-->>Safety: Parking...
    Mount-->>Safety: Parked
    Safety->>Enclosure: Emergency close
    Enclosure-->>Safety: Closing...
    Enclosure-->>Safety: Closed
    Safety->>Alert: Emergency complete
```

## Hardware Connectivity

```mermaid
flowchart TB
    subgraph RaspberryPi["NVIDIA DGX Spark / Pi"]
        NIGHTWATCH["NIGHTWATCH Software"]
    end

    subgraph Network["Network (TCP/IP)"]
        LAN["192.168.1.x"]
    end

    subgraph Devices["Hardware Devices"]
        OnStepX["OnStepX Controller<br/>TCP:9999 (LX200)"]
        Ecowitt["Ecowitt Gateway<br/>HTTP API"]
        PHD2["PHD2<br/>JSON-RPC:4400"]
        INDI["INDI Server<br/>TCP:7624"]
        Alpaca["Alpaca Server<br/>HTTP:11111"]
    end

    NIGHTWATCH --> LAN
    LAN --> OnStepX
    LAN --> Ecowitt
    LAN --> PHD2
    LAN --> INDI
    LAN --> Alpaca
```

## Catalog Lookup Flow

```mermaid
flowchart TB
    Query["User Query:<br/>'Andromeda'"]
    Cache["LRU Cache<br/>Check"]
    ExactMatch["Exact ID Match<br/>catalog_id = 'ANDROMEDA'"]
    NameMatch["Name Match<br/>name = 'ANDROMEDA'"]
    AliasMatch["Alias Match<br/>aliases table"]
    FuzzyMatch["Fuzzy Match<br/>Levenshtein distance"]
    Result["CatalogObject<br/>M31 / Andromeda Galaxy"]

    Query --> Cache
    Cache -->|Hit| Result
    Cache -->|Miss| ExactMatch
    ExactMatch -->|Found| Result
    ExactMatch -->|Not Found| NameMatch
    NameMatch -->|Found| Result
    NameMatch -->|Not Found| AliasMatch
    AliasMatch -->|Found| Result
    AliasMatch -->|Not Found| FuzzyMatch
    FuzzyMatch --> Result
```

## Deployment Architecture

```mermaid
flowchart TB
    subgraph Docker["Docker Environment"]
        subgraph Core["Core Services"]
            Orchestrator["Orchestrator"]
            Voice["Voice Pipeline"]
        end

        subgraph Simulators["Development Simulators"]
            AlpacaSim["Alpaca Simulator"]
            INDISim["INDI Simulator"]
            WeatherSim["Weather Simulator"]
        end
    end

    subgraph Volumes["Persistent Storage"]
        Config["./config"]
        Logs["./logs"]
        Data["./data"]
    end

    subgraph Network["Docker Network"]
        Bridge["nightwatch-net"]
    end

    Config --> Docker
    Logs --> Docker
    Data --> Docker
    Core --> Bridge
    Simulators --> Bridge
```

## State Machine: Mount Operations

```mermaid
stateDiagram-v2
    [*] --> Disconnected
    Disconnected --> Connected: connect()
    Connected --> Disconnected: disconnect()

    Connected --> Parked: Initial state
    Parked --> Unparked: unpark()
    Unparked --> Parked: park()

    Unparked --> Tracking: set_tracking(true)
    Tracking --> Unparked: set_tracking(false)

    Tracking --> Slewing: slew_to()
    Slewing --> Tracking: slew complete
    Slewing --> Tracking: abort_slew()

    Tracking --> Parked: park()
    Slewing --> Parked: park()

    Parked --> [*]: disconnect()
```

## Module Dependencies

```mermaid
flowchart BT
    subgraph Core["Core Modules"]
        Config["nightwatch.config"]
        Logging["nightwatch.logging"]
        Utils["nightwatch.utils"]
    end

    subgraph Services["Service Modules"]
        Mount["services.mount_control"]
        Weather["services.weather"]
        Safety["services.safety_monitor"]
        Catalog["services.catalog"]
        Ephemeris["services.ephemeris"]
    end

    subgraph Voice["Voice Modules"]
        STT["voice.stt"]
        TTS["voice.tts"]
        Tools["voice.tools"]
        Pipeline["voice.pipeline"]
    end

    Mount --> Config
    Mount --> Logging
    Weather --> Config
    Weather --> Logging
    Safety --> Config
    Safety --> Weather
    Catalog --> Config
    Ephemeris --> Config

    STT --> Config
    TTS --> Config
    Tools --> Mount
    Tools --> Safety
    Tools --> Catalog
    Pipeline --> STT
    Pipeline --> TTS
    Pipeline --> Tools
```

---

## Component Descriptions

### Voice Pipeline
- **Whisper STT**: OpenAI's speech-to-text model (faster-whisper implementation)
- **LLM Processor**: Local LLM for intent parsing and tool selection
- **Piper TTS**: Neural text-to-speech for natural responses

### Observatory Services
- **Mount Control**: OnStepX communication via LX200 protocol
- **Weather Service**: Ecowitt integration for environmental monitoring
- **Safety Monitor**: Rule-based safety evaluation with vetoes
- **Catalog Service**: SQLite-based astronomical object database
- **Ephemeris Service**: Skyfield-based celestial calculations

### Hardware Interfaces
- **OnStepX**: TCP/IP socket with LX200/extended commands
- **Ecowitt**: HTTP REST API on local gateway
- **Alpaca**: ASCOM Alpaca REST API standard
- **INDI**: XML-based telescope control protocol
