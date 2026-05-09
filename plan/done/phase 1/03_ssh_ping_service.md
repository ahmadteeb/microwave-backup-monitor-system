# 03 — SSH Ping Service

## SSHService Integration

The provided `SSHService` class is used **as-is** — it is copied into `app/services/ssh_service.py` without modification. All ping operations call its `connect()`, `execCommand()`, and `disconnect()` methods.

The ping service (`app/services/ping_service.py`) is the orchestration layer that:
1. Retrieves the active JumpServer record from the database.
2. Creates an `SSHService` instance for the jump server and calls `connect()`.
3. For each link to be pinged, calls `execCommand()` with the appropriate ping command.
4. Parses the stdout output to extract reachability, latency, and packet loss.
5. Writes a `PingResult` row to the database for each link.
6. Calls `disconnect()` after the cycle completes.

The ping service does **not** create a second SSH hop to each MW device. The ping command runs **on the jump server itself**, which has IP reachability to the MW link IPs. The flow is: Flask → SSH to jump server → run `ping <mw_ip>` on jump server → capture stdout.

---

## Jump Server Connection Lifecycle

**Per scheduler cycle:**

1. Query `JumpServer` table for the row where `active=True`.
2. Decrypt the stored password using Fernet with the Flask `SECRET_KEY`.
3. Instantiate `SSHService(host, username, password, port)` — no `jumpClient` parameter because this **is** the jump server itself.
4. Call `connect()`. If it fails, log the error, mark the cycle as failed, and return early. Do not attempt to ping any links.
5. Iterate over all `Link` rows, executing a ping command for each.
6. After all pings are complete (or after an unrecoverable error), call `disconnect()`.

**Why connect-once-per-cycle:** Opening an SSH connection takes 1–3 seconds. With 142 links, reconnecting for each would add 3–7 minutes of overhead. A single connection reused for all pings keeps the cycle under 10 minutes even at scale.

---

## Ping Execution Strategy

For each link, the ping service executes:

```
ping -c <PING_COUNT> -W <PING_TIMEOUT> <mw_ip>
```

Default values: `PING_COUNT=3`, `PING_TIMEOUT=2`. This means each ping takes at most `3 × 2 = 6` seconds worst-case (all timeouts).

The command is sent via `SSHService.execCommand()`, which:
- Sends the command string + newline to the shell.
- Waits for output, handling `---- More ----` prompts.
- Returns the full stdout as a string.

**Important timing note:** The `execCommand()` method has a 1-second `time.sleep()` before reading. For ping commands that may take up to 6 seconds, additional read iterations may be needed. The ping service should add a brief sleep (2 seconds) after sending the command and before calling `execCommand()`, or the method should be called with an awareness that ping output arrives slowly. Alternatively, the ping service can issue the command and then poll `shell.recv_ready()` in a loop with a total timeout of `PING_COUNT * PING_TIMEOUT + 2` seconds.

---

## Ping Result Parsing Rules

The raw stdout from `ping` on a Linux jump server follows standard patterns:

**Success pattern (reachable):**
```
PING 10.0.5.22 (10.0.5.22) 56(84) bytes of data.
64 bytes from 10.0.5.22: icmp_seq=1 ttl=64 time=14.2 ms
64 bytes from 10.0.5.22: icmp_seq=2 ttl=64 time=13.8 ms
64 bytes from 10.0.5.22: icmp_seq=3 ttl=64 time=14.5 ms

--- 10.0.5.22 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2003ms
rtt min/avg/max/mdev = 13.8/14.1/14.5/0.3 ms
```

- **Reachable**: `True` — at least one `bytes from` line present.
- **Latency**: Parse the `avg` value from the `rtt min/avg/max/mdev` line using regex: `rtt .+ = [\d.]+/([\d.]+)/` → capture group 1 is avg latency in ms.
- **Packet loss**: Parse from `(\d+)% packet loss` → capture group 1.

**Timeout pattern (unreachable):**
```
PING 10.0.5.99 (10.0.5.99) 56(84) bytes of data.

--- 10.0.5.99 ping statistics ---
3 packets transmitted, 0 received, 100% packet loss, time 6007ms
```

- **Reachable**: `False` — no `bytes from` line, 100% packet loss.
- **Latency**: `None` — no RTT line present.
- **Packet loss**: `100.0`.

**Partial loss pattern (degraded):**
```
3 packets transmitted, 2 received, 33% packet loss
rtt min/avg/max/mdev = 13.8/14.1/14.5/0.3 ms
```

- **Reachable**: `True` — some packets returned.
- **Latency**: Parse avg RTT as above.
- **Packet loss**: `33.0`. The status badge shows `HIGH` or `PKT_LOSS` depending on the threshold.

**Network unreachable pattern:**
```
connect: Network is unreachable
```

- **Reachable**: `False`.
- **Latency**: `None`.
- **Packet loss**: `100.0`.

**Fallback**: If none of the patterns match (unexpected output), set `reachable=False`, `latency_ms=None`, `packet_loss=None`, and store the raw output for manual inspection.

---

## Concurrency Plan

**Recommendation: Sequential pings within a single SSH session.**

Justification:
- The `SSHService` uses `invoke_shell()` which creates a single interactive shell channel. Shell channels are inherently serial — sending a second command before the first completes will interleave output, making parsing impossible.
- To achieve parallel pings, you would need multiple SSH channels (one per ping), which adds complexity and may exceed the jump server's channel limit.
- Sequential execution with 142 links at ~6 seconds max per link = ~14 minutes worst case. In practice, most pings complete in 1–2 seconds, giving a realistic cycle time of 3–5 minutes.
- The 60-second default ping interval means the scheduler should detect if a cycle is still running and skip the next trigger rather than starting a concurrent cycle.

**Cycle overlap protection:** The scheduler job should acquire a threading lock (`threading.Lock`) before starting a cycle. If the lock is already held (previous cycle still running), log a warning and skip.

---

## Error Handling

| Scenario | Handling |
|---|---|
| **Jump server unreachable** | SSH `connect()` raises an exception. Catch it, log `ERROR: Jump server unreachable`, skip entire cycle. Set a flag so the dashboard can show "System Unhealthy" in the top bar. |
| **SSH authentication failure** | Paramiko raises `AuthenticationException`. Log the error, skip cycle. This usually means credentials were changed — the operator must update them via the Settings API. |
| **Individual link timeout** | The ping command itself returns 100% loss. This is a normal result (link is down), not an error. Store as a PingResult with `reachable=False`. |
| **execCommand hangs** | If the shell does not produce output within `PING_COUNT * PING_TIMEOUT + 5` seconds, consider the command timed out. Send a Ctrl+C (`\x03`) to the shell, read any remaining output, log a warning, store a PingResult with `reachable=False` and `raw_output` containing the partial output. |
| **SSH session drops mid-cycle** | Catch `socket.error` or `paramiko.SSHException` during `execCommand`. Log the error, attempt to reconnect once. If reconnection fails, abort the remaining pings in this cycle and record failures for the remaining links. |
| **Database write failure** | Catch SQLAlchemy exceptions when inserting PingResult. Log the error but continue pinging remaining links. Do not let a DB error halt the entire cycle. |

---

## APScheduler Job Plan

- **Scheduler type**: `BackgroundScheduler` from `apscheduler.schedulers.background`.
- **Job name**: `ping_cycle`
- **Trigger type**: `interval`
- **Default interval**: 60 seconds (configurable via `PING_INTERVAL_SECONDS` env var)
- **Max instances**: 1 — prevents concurrent cycles if a cycle takes longer than the interval.
- **Misfire grace time**: 30 seconds — if a trigger is missed by up to 30 seconds (e.g., due to a long previous cycle), still execute it. If more than 30 seconds late, skip.
- **Coalesce**: True — if multiple misfires accumulate, run only one catch-up cycle.

**Startup sequence:**
1. `create_app()` creates the scheduler.
2. The scheduler job is added with the configured interval.
3. The scheduler is started **after** `db.create_all()` so that models are available.
4. On app shutdown, `scheduler.shutdown(wait=False)` is called to cleanly stop the background thread.

**Interval reconfiguration:** Changing `PING_INTERVAL_SECONDS` requires restarting the app. A v2 enhancement could expose a `PUT /api/settings/ping-interval` route that reschedules the job dynamically.

---

## Manual Ping (API-Triggered)

When `POST /api/links/<id>/ping` is called:

1. The route handler creates a **new, separate** `SSHService` connection to the jump server. This is independent of the scheduler's connection.
2. It executes a single ping command for the specified link.
3. It parses the result using the same parsing logic as the scheduler.
4. It writes a PingResult row and returns the result in the HTTP response.
5. It disconnects the SSH session.

**Why a separate connection:** The scheduler's SSH session may be in the middle of a cycle, with pending output in the shell buffer. Reusing it would corrupt both the manual ping's output and the scheduler's current command. A fresh connection guarantees clean, isolated output.

**Latency consideration:** The manual ping blocks the HTTP request for up to ~8 seconds (SSH connect + ping execution). This is acceptable for an operator-initiated action. The frontend should show a spinner/loading state during this time.

---

## Open Questions

1. **Jump server OS** — The parsing rules assume a Linux jump server with standard `ping` output format. If the jump server runs a different OS or a non-standard ping utility, the regex patterns may need adjustment. Should we support multiple output formats?
2. **Ping command path** — Should the command be `/bin/ping` (absolute path) to avoid PATH issues on the jump server, or rely on the shell's PATH resolution?
3. **Rate limiting** — Should manual pings be rate-limited to prevent an operator from spamming pings and overwhelming the jump server? Suggested: max 1 manual ping per link per 10 seconds.
