# WebSocket V2 Data Flow Diagram

## System Architecture Visualization

### High-Level Data Flow

```mermaid
flowchart TB
    subgraph "Kraken Exchange"
        KWS[WebSocket V2 Server<br/>wss://ws-auth.kraken.com/v2]
        KREST[REST API Server<br/>https://api.kraken.com]
    end
    
    subgraph "Data Layer"
        WSM[Enhanced WebSocket Manager<br/>- Multiple Connections<br/>- Channel Priority<br/>- Auto Reconnect]
        RESTC[Strategic REST Client<br/>- Circuit Breaker<br/>- Rate Limiting<br/>- Minimal Usage]
        UDF[Unified Data Feed<br/>- Source Selection<br/>- Caching<br/>- Failover Logic]
    end
    
    subgraph "Processing Layer"
        MP[Message Processor<br/>- Format Conversion<br/>- Validation<br/>- Batching]
        SM[State Manager<br/>- Balance Tracking<br/>- Order State<br/>- Position State]
        PM[Performance Monitor<br/>- Latency Tracking<br/>- Health Checks<br/>- Metrics]
    end
    
    subgraph "Application Layer"
        BM[Balance Manager]
        STR[Strategy Manager]
        TE[Trade Executor]
        RM[Risk Manager]
    end
    
    KWS -.->|Real-time Stream| WSM
    KREST -.->|On-demand/Fallback| RESTC
    
    WSM --> MP
    RESTC --> MP
    MP --> SM
    SM --> UDF
    
    UDF --> BM
    UDF --> STR
    UDF --> TE
    UDF --> RM
    
    PM -.-> WSM
    PM -.-> RESTC
    PM -.-> UDF
    
    style KWS fill:#2ecc71,stroke:#27ae60,stroke-width:3px
    style UDF fill:#3498db,stroke:#2980b9,stroke-width:3px
    style WSM fill:#e74c3c,stroke:#c0392b,stroke-width:2px
```

### Detailed WebSocket V2 Message Flow

```mermaid
sequenceDiagram
    participant K as Kraken WS V2
    participant WM as WebSocket Manager
    participant Q as Message Queue
    participant P as Message Processor
    participant S as State Manager
    participant C as Callbacks
    
    Note over K,C: Connection & Authentication
    WM->>K: Connect to wss://ws-auth.kraken.com/v2
    K-->>WM: Connection Established
    WM->>K: Authenticate with Token
    K-->>WM: Authentication Success
    
    Note over K,C: Channel Subscriptions (Priority Order)
    WM->>K: Subscribe: balances (CRITICAL)
    K-->>WM: Subscription Confirmed
    WM->>K: Subscribe: executions (CRITICAL)
    K-->>WM: Subscription Confirmed
    WM->>K: Subscribe: ticker (HIGH)
    K-->>WM: Subscription Confirmed
    WM->>K: Subscribe: book (MEDIUM)
    K-->>WM: Subscription Confirmed
    
    Note over K,C: Real-time Data Flow
    loop Continuous Stream
        K->>WM: Balance Update Message
        WM->>Q: Queue Message
        Q->>P: Process Balance Update
        P->>S: Update Balance State
        S->>C: Trigger Balance Callbacks
        
        K->>WM: Ticker Update Message
        WM->>Q: Queue Message
        Q->>P: Process Ticker
        P->>S: Update Ticker State
        S->>C: Trigger Ticker Callbacks
        
        K->>WM: Execution Message
        WM->>Q: Queue Message
        Q->>P: Process Execution
        P->>S: Update Order State
        S->>C: Trigger Execution Callbacks
    end
    
    Note over K,C: Heartbeat & Health
    loop Every 30s
        K->>WM: Heartbeat
        WM-->>K: Pong
    end
```

### REST API Fallback Flow

```mermaid
flowchart LR
    subgraph "Normal Operation"
        A[Data Request] --> B{Source Check}
        B -->|Primary| C[WebSocket Data]
        C --> D[Return Data]
    end
    
    subgraph "Fallback Operation"
        E[Data Request] --> F{Source Check}
        F -->|WS Failed| G{Circuit Breaker}
        G -->|Open| H[Return Cached/Error]
        G -->|Closed| I[REST API Call]
        I --> J{Rate Limit Check}
        J -->|OK| K[Execute REST]
        J -->|Limited| L[Queue/Delay]
        K --> M[Cache Result]
        M --> N[Return Data]
    end
    
    style C fill:#2ecc71
    style K fill:#e74c3c
```

### Data Priority and Channel Management

```mermaid
graph TD
    subgraph "Channel Priority System"
        CP1[CRITICAL Priority 1<br/>- balances<br/>- executions]
        CP2[HIGH Priority 2<br/>- ticker<br/>- orders]
        CP3[MEDIUM Priority 3<br/>- orderbook]
        CP4[LOW Priority 4<br/>- ohlc<br/>- trades]
    end
    
    subgraph "Connection Allocation"
        CONN1[Connection 1<br/>Primary]
        CONN2[Connection 2<br/>Backup]
    end
    
    subgraph "Load Distribution"
        LD1[Critical Channels<br/>Always on Primary]
        LD2[High Priority<br/>Load Balanced]
        LD3[Medium/Low<br/>Best Effort]
    end
    
    CP1 --> CONN1
    CP1 --> CONN2
    CP2 --> LD2
    CP3 --> LD3
    CP4 --> LD3
    
    LD1 --> CONN1
    LD2 --> CONN1
    LD2 -.-> CONN2
    LD3 -.-> CONN2
    
    style CP1 fill:#e74c3c,color:#fff
    style CP2 fill:#f39c12,color:#fff
    style CP3 fill:#3498db,color:#fff
    style CP4 fill:#95a5a6,color:#fff
```

### Balance Update Flow (Critical Path)

```mermaid
flowchart TB
    subgraph "WebSocket V2 Balance Stream"
        WS[WebSocket Message<br/>[{asset: MANA, balance: 163.94}]]
        PARSE[Parse Message]
        VALIDATE[Validate Format]
        CONVERT[Convert to Internal Format]
    end
    
    subgraph "Balance Manager Integration"
        UPDATE[Update Balance State]
        CACHE[Update Cache]
        HISTORY[Record History]
        NOTIFY[Notify Subscribers]
    end
    
    subgraph "Circuit Breaker Reset"
        CHECK{Circuit Breaker<br/>Active?}
        RESET[Reset Circuit Breaker<br/>Clear Failure Count]
    end
    
    subgraph "Trading Bot Actions"
        STRATEGY[Update Strategy<br/>Available Capital]
        RISK[Update Risk<br/>Calculations]
        UI[Update UI/Logs]
    end
    
    WS --> PARSE
    PARSE --> VALIDATE
    VALIDATE --> CONVERT
    CONVERT --> UPDATE
    
    UPDATE --> CHECK
    CHECK -->|Yes| RESET
    CHECK -->|No| CACHE
    RESET --> CACHE
    
    CACHE --> HISTORY
    HISTORY --> NOTIFY
    
    NOTIFY --> STRATEGY
    NOTIFY --> RISK
    NOTIFY --> UI
    
    style WS fill:#2ecc71
    style UPDATE fill:#e74c3c
    style RESET fill:#f39c12
```

### Order Execution Flow

```mermaid
sequenceDiagram
    participant TB as Trading Bot
    participant UDF as Unified Data Feed
    participant WSM as WebSocket Manager
    participant REST as REST Client
    participant K as Kraken
    
    Note over TB,K: Order Placement Decision
    TB->>UDF: Get Current Market Data
    UDF->>WSM: Check Ticker/Orderbook
    WSM-->>UDF: Return Fresh Data
    UDF-->>TB: Market Data
    
    TB->>TB: Calculate Order Parameters
    
    Note over TB,K: Order Execution (WebSocket Priority)
    TB->>WSM: Place Order via WebSocket
    WSM->>K: add_order message
    
    alt Success
        K-->>WSM: Order Confirmation
        WSM-->>TB: Order ID & Status
        TB->>TB: Update Position
    else WebSocket Failure
        K-->>WSM: Error/Timeout
        WSM-->>TB: Failure Response
        
        Note over TB,K: Fallback to REST
        TB->>REST: Place Order via REST
        REST->>K: POST /AddOrder
        K-->>REST: Order Response
        REST-->>TB: Order Details
    end
    
    Note over TB,K: Order Monitoring
    loop Until Filled
        K->>WSM: Execution Updates
        WSM->>TB: Order Status
        TB->>TB: Update State
    end
```

### Performance Monitoring Dashboard

```mermaid
graph TB
    subgraph "Real-time Metrics"
        M1[Message Rate<br/>msgs/sec]
        M2[Latency<br/>avg ms]
        M3[Cache Hit Rate<br/>%]
        M4[Failover Count]
    end
    
    subgraph "Health Indicators"
        H1[WebSocket Status<br/>🟢 Connected]
        H2[REST API Status<br/>🟡 Limited]
        H3[Circuit Breaker<br/>🟢 Closed]
        H4[Data Freshness<br/>🟢 < 1s]
    end
    
    subgraph "Channel Statistics"
        C1[Balances: 1,234 msgs]
        C2[Ticker: 45,678 msgs]
        C3[Orderbook: 23,456 msgs]
        C4[Executions: 123 msgs]
    end
    
    subgraph "Resource Usage"
        R1[Queue Size: 234/10000]
        R2[Memory: 156 MB]
        R3[Connections: 2/2]
        R4[CPU: 12%]
    end
    
    style H1 fill:#2ecc71
    style H2 fill:#f39c12
    style H3 fill:#2ecc71
    style H4 fill:#2ecc71
```

### Error Handling and Recovery

```mermaid
flowchart TB
    subgraph "Error Detection"
        E1[Connection Lost]
        E2[Auth Failure]
        E3[Rate Limit]
        E4[Invalid Data]
    end
    
    subgraph "Recovery Actions"
        R1[Exponential Backoff<br/>Reconnect]
        R2[Token Refresh<br/>Re-authenticate]
        R3[Circuit Breaker<br/>REST Fallback]
        R4[Data Validation<br/>Skip & Log]
    end
    
    subgraph "Monitoring"
        M1[Log Error]
        M2[Update Metrics]
        M3[Alert if Critical]
    end
    
    E1 --> R1
    E2 --> R2
    E3 --> R3
    E4 --> R4
    
    R1 --> M1
    R2 --> M1
    R3 --> M2
    R4 --> M2
    
    M1 --> M3
    M2 --> M3
    
    style E1 fill:#e74c3c
    style E2 fill:#e74c3c
    style E3 fill:#f39c12
    style E4 fill:#f39c12
```

## Implementation Timeline

```mermaid
gantt
    title WebSocket V2 Implementation Timeline
    dateFormat  YYYY-MM-DD
    section Phase 1
    Enhanced WS Manager     :a1, 2025-01-15, 3d
    Message Processing      :a2, after a1, 2d
    State Management       :a3, after a2, 2d
    
    section Phase 2
    REST Client Strategy   :b1, after a1, 3d
    Circuit Breaker       :b2, after b1, 2d
    Rate Limiting         :b3, after b2, 1d
    
    section Phase 3
    Unified Data Feed     :c1, after a3, 3d
    Failover Logic        :c2, after c1, 2d
    Performance Monitor   :c3, after c2, 2d
    
    section Phase 4
    Integration Testing   :d1, after c3, 3d
    Migration Scripts     :d2, after d1, 2d
    Production Deploy     :d3, after d2, 1d
```

## Key Benefits

1. **Ultra-Low Latency**: Direct WebSocket V2 streaming eliminates polling delays
2. **High Reliability**: Automatic failover ensures continuous operation
3. **Minimal API Usage**: REST calls reduced by 95%+ 
4. **Real-time Accuracy**: Live balance and order updates
5. **Scalable Architecture**: Handles high-frequency trading loads

## Summary

This architecture maximizes the benefits of Kraken's WebSocket V2 API while maintaining robustness through strategic REST API fallback. The visual diagrams show how data flows through the system, ensuring optimal performance for crypto trading operations.