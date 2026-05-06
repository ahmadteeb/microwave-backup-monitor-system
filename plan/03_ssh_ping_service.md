# 03 — SSH Ping Service

## 1. SSHService Integration Strategy

The application leverages the pre-existing, custom `SSHService` class built on top of `paramiko` to tunnel all remote diagnostic actions through the secure Jump Server. This class must be utilized exactly as provided, without any code modifications.

### 1.1 `SSHService` Class Definition

```python
class SSHService:
    def __init__(self, host, port, username, password, jump_host=None,
                 jump_port=22, jump_username=None, jump_password=None):
        """
        Initializes the SSH client configuration.
        If jump_host is provided, connection handshakes are automatically 
        tunnelled through the intermediate jump server gateway.
        """
        pass
        
    def connect(self) -> None:
        """
        Establishes the raw TCP connection and SSH transport handshakes.
        If tunnel options are active, creates a direct TCP port forward channel.
        """
        pass
        
    def disconnect(self) -> None:
        """
        Gracefully releases remote channel terminals, transports, and client sockets.
        """
        pass
        
    def execCommand(self, command: str) -> str:
        """
        Spawns a shell, streams the input command string to the remote machine, 
        buffers terminal responses, handles '---- More ----' pagination blocks, 
        and returns the consolidated string block.
        """
        pass
```

---

## 2. Ping Execution Sequence

The ping diagnostic execution sequence runs as follows for each microwave link target:

1.  **Retrieve Jump Server Credentials**: Load the single active gateway config row from the `JumpServer` table. Passwords/private keys must be decrypted at rest using the `CryptoService` Fernet decryption method.
2.  **Instantiate Client**: Initialize `SSHService`. Because the microwave link target IPs are isolated, the target microwave IP address `mw_ip` acts as the primary destination endpoint, while the decrypted `JumpServer` parameters are provided inside the `jump_` fields:
    -   `host`: target microwave IP `mw_ip`
    -   `port`: destination device SSH port (usually `22`)
    -   `username`: destination device username
    -   `password`: destination device password
    -   `jump_host`: gateway IP `JumpServer.host`
    -   `jump_port`: gateway port `JumpServer.port`
    -   `jump_username`: gateway username `JumpServer.username`
    -   `jump_password`: decrypted gateway password `JumpServer.password`
3.  ** handshakes (Connect)**: Execute `connect()`. Ensure this call is wrapped inside a `try-except-finally` block.
4.  **Execute Check**: Call `execCommand("ping -c 4 <mw_ip>")` (or appropriate equipment-specific ping command matching target terminal syntax).
5.  **Clean Close**: Call `disconnect()` inside the `finally` block to prevent terminal session leakage or socket lockouts.
6.  **Insert Log Entry**: Parse the resulting output, save a new `PingResult` record, and update the matching `LinkStatus` materialized cache.

---

## 3. Parsing Rules and Regular Expressions

The raw response output returned by `execCommand` is analyzed using the regular expression patterns detailed below to extract latency metrics.

### 3.1 Successful Ping Detection

If the remote console output contains indicators of returned packets, the device is logged as **Reachable**.

-   **Success Pattern (Linux Standard)**: Matches `64 bytes from ...` or `time=... ms`.
-   **Regex Pattern**:
    ```regex
    (\d+(?:\.\d+)?)\s*ms
    ```
-   **Parsing Logic**:
    -   Search the output string for the term `bytes from`.
    -   If found, parse all matching instances of the regex pattern to extract the numeric delay.
    -   Calculate the mathematical average of the captured delays.
    -   Save `is_reachable = True` and set `latency_ms` to the calculated average.

### 3.2 Packet Loss and Timeout Detection

If the terminal response reports severe packet loss, or if the connection fails to yield packet details, the target is logged as **Unreachable**.

-   **Timeout Patterns**: Searches for the phrases `100% packet loss`, `Destination Host Unreachable`, or the complete absence of `bytes from` indicator blocks.
-   **Parsing Logic**:
    -   Set `is_reachable = False` and `latency_ms = None`.
    -   Extract packet loss percentage if present using pattern:
        ```regex
        (\d+)%\s*packet\s*loss
        ```

### 3.3 SSH Connection Failure Handling

If an operational execution block throws an exception (e.g., `TimeoutError`, `SocketError`, or `AuthenticationException`), it is logged as **Unreachable**.

-   **Exception Handlers**:
    -   Set `is_reachable = False` and `latency_ms = None`.
    -   Write the detailed stack trace message into `PingResult.raw_output` for audit inspection.
    -   Log an error entry inside `SystemLog` using the `scheduler` category.

---

## 4. Metric Collection Stub Interface

Traffic metrics (utilization rates, capacity limits, and peak throughput timestamps) are harvested from the routers using equipment terminal commands. Since different target hardware platforms (e.g., ATN 910-C, ATN 950-C, X8 Router) employ distinct CLI platforms, the collection interface is designed as an extensible parser system.

### 4.1 Parser Interface (`MetricParserBase`)

```python
class MetricParserBase:
    def get_query_command(self) -> str:
        """Returns the specific CLI command needed to print port metrics."""
        raise NotImplementedError()
        
    def parse_metrics(self, raw_output: str) -> dict:
        """
        Parses console text and returns a structured dictionary containing:
        - fiber_util_mbps (float)
        - fiber_util_pct (float)
        - fiber_capacity_mbps (float)
        - mw_util_mbps (float)
        - mw_util_pct (float)
        - mw_capacity_mbps (float)
        """
        raise NotImplementedError()
```

### 4.2 Huawei ATN 910-C Parser Stub Implementation

For ATN platforms, the command `display interface GigabitEthernet 0/0/1` returns interface statistics:

```python
class HuaweiAtnParser(MetricParserBase):
    def get_query_command(self) -> str:
        return "display interface GigabitEthernet 0/0/1"
        
    def parse_metrics(self, raw_output: str) -> dict:
        # Mock parsing logic returning dummy variables for development.
        # In production, parse actual regex matches for:
        # "Input bandwidth utilization  :  23.4%" and "Output bandwidth utilization : 12.1%"
        import random
        fiber_cap = 1000.0 # 1 Gbps physical capacity
        mw_cap = 150.0     # 150 Mbps microwave backup capacity
        
        # Simulating operational trends: High primary utilization forces traffic to backup microwave
        fiber_util = random.uniform(300.0, 950.0)
        fiber_pct = (fiber_util / fiber_cap) * 100.0
        
        mw_util = 0.0
        if fiber_pct > 90.0:
            mw_util = random.uniform(40.0, 140.0)
            
        mw_pct = (mw_util / mw_cap) * 100.0
        
        return {
            "fiber_util_mbps": fiber_util,
            "fiber_util_pct": fiber_pct,
            "fiber_capacity_mbps": fiber_cap,
            "mw_util_mbps": mw_util,
            "mw_util_pct": mw_pct,
            "mw_capacity_mbps": mw_cap
        }
```

---

## 5. Background Scheduler

The background scheduling thread is integrated using the `APScheduler` library's `BackgroundScheduler` instance. It is instantiated inside the Flask application factory.

-   **Scheduler Startup**: Launched on application startup, utilizing background system threads.
-   **Locking Mechanism**: Uses an operational concurrency lock (`threading.Lock`) to prevent overlapping cycles. If a ping cycle is still active when the next interval triggers, the system logs a system warning and skips the execution sweep.
-   **Job Routine (`ping_cycle`)**:
    -   Loads the latest application parameters from `AppSettings` to determine execution delays (`ping_interval_seconds`).
    -   Loads all active monitored links where `is_active` is `True`.
    -   **Sequential Execution**: Performs ping runs sequentially (one link at a time) using a single background thread. This sequential pattern minimizes simultaneous load on the intermediate Jump Server gateway.
    -   On cycle completion, updates the corresponding `LinkStatus` rows and analyzes the results to trigger any necessary alerts or email notifications.

---

## 6. Manual Diagnostics Flow

Manual diagnostic requests bypass the scheduler queue and execute immediately in the request thread to provide instantaneous feedback to the operator.

-   **Thread Execution**: Executes directly inside the active WSGI request thread.
-   **Isolation**: Opens a dedicated socket channel through the Jump Server, ensuring that user diagnostics are fully isolated from the background scheduling thread.
-   **Audit Logging**: The resulting `PingResult` is saved with `triggered_by = manual`, capturing the operator's user ID inside the record.
-   **UI Delivery**: Returns the raw console output string in the JSON API response, allowing the operator to view the terminal response directly on their screen.
