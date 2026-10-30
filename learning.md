# Fluid Framework — Developer Learning Guide

> Captured from deep codebase exploration session.  
> All file paths are relative to the repository root unless stated otherwise.  
> Line numbers are approximate and may shift with code changes.

---

## Table of Contents

1. [Repository Layout](#1-repository-layout)
2. [FF-OCE On-Call Agent](#2-ff-oce-on-call-agent)
3. [Routerlicious Server Architecture](#3-routerlicious-server-architecture)
4. [Op Flow End-to-End](#4-op-flow-end-to-end)
5. [Kafka Messaging, Backpressure, and Scaling](#5-kafka-messaging-backpressure-and-scaling)
6. [Scriptorium vs Scribe](#6-scriptorium-vs-scribe)
7. [Total Order Broadcast (ToB)](#7-total-order-broadcast-tob)
8. [Why Git for Snapshots](#8-why-git-for-snapshots)
9. [How a New User Joins an Existing Session](#9-how-a-new-user-joins-an-existing-session)
10. [Observability Architecture](#10-observability-architecture)
11. [DDS Architecture](#11-dds-architecture)
12. [Collaborative Editing — Sequence Numbers Walkthrough](#12-collaborative-editing--sequence-numbers-walkthrough)
13. [Data Corruption Scenarios](#13-data-corruption-scenarios)
14. [Op Batching, Compression, and Chunking](#14-op-batching-compression-and-chunking)
15. [Summarizer Client Election](#15-summarizer-client-election)
16. [Incremental Summaries](#16-incremental-summaries)
17. [Document-Router — Per-Document Partitioning in Deli](#17-document-router--per-document-partitioning-in-deli)
18. [Signals vs Ops](#18-signals-vs-ops)
19. [NoOp Messages and MSN Advancement](#19-noop-messages-and-msn-advancement)
20. [Container Lifecycle — Detached → Attaching → Attached](#20-container-lifecycle--detached--attaching--attached)
21. [Garbage Collection Lifecycle](#21-garbage-collection-lifecycle)
22. [Auth and Token Flow (Riddler)](#22-auth-and-token-flow-riddler)
23. [Local Development — Tinylicious and Docker Compose](#23-local-development--tinylicious-and-docker-compose)
24. [Recent Upstream Fluid 2.x Architecture & API Evolution](#24-recent-upstream-fluid-2x-architecture--api-evolution)
25. [1-Hour Deep-Dive Technical Interview Script (Director & Distinguished Engineer)](#25-1-hour-deep-dive-technical-interview-script-director--distinguished-engineer)

---

## 1. Repository Layout

```
FluidFramework/
├── packages/
│   ├── common/          # Core interfaces, protocol definitions
│   ├── dds/             # All Distributed Data Structures
│   │   ├── shared-object-base/   # Base class for every DDS
│   │   ├── map/                  # SharedMap, SharedDirectory
│   │   ├── sequence/             # SharedString (uses merge-tree)
│   │   ├── merge-tree/           # MergeTree CRDT for sequences
│   │   ├── tree/                 # SharedTree (schema-aware, rebase-based)
│   │   ├── counter/              # SharedCounter
│   │   ├── cell/                 # SharedCell
│   │   └── matrix/               # SharedMatrix
│   ├── loader/          # ContainerLoader, DeltaManager
│   ├── runtime/
│   │   ├── container-runtime/    # ContainerRuntime, GC, summaries, batching
│   │   ├── datastore/            # FluidDataStoreRuntime
│   │   ├── id-compressor/        # Distributed ID generation
│   │   └── runtime-definitions/  # Core runtime interfaces
│   └── drivers/         # Service drivers (ODSP, Routerlicious, etc.)
├── server/
│   └── routerlicious/   # The ordering service
│       └── packages/
│           ├── routerlicious/          # Main entry + all service runners
│           ├── routerlicious-base/     # Base HTTP factories
│           ├── lambdas/                # Deli, Scribe, Scriptorium, Broadcaster, Nexus
│           ├── lambdas-driver/         # Kafka consumer framework
│           ├── services/               # Tenant, storage, Redis, MongoDB clients
│           ├── services-core/          # Core interfaces
│           ├── services-telemetry/     # Lumberjack telemetry
│           ├── services-utils/         # HTTP middleware, correlation IDs
│           └── tinylicious/            # Lightweight all-in-one test server
├── common/
│   └── lib/protocol-definitions/  # IDocumentMessage, ISequencedDocumentMessage, etc.
└── .agency/plugins/ff-oce/        # FF On-Call Engineer agent
```

---

## 2. FF-OCE On-Call Agent

### What it is

A Claude agent that assists engineers on the Fluid Framework Client on-call rotation.  
**Location:** `.agency/plugins/ff-oce/`

```
.agency/plugins/ff-oce/
├── .claude-plugin/plugin.json          # Plugin registration
├── agents/ff-oce.md                    # Core agent persona + knowledge base
└── skills/
    ├── ff-oce-dashboard/SKILL.md       # Shift status dashboard skill
    └── ff-oce-kusto/
        ├── SKILL.md                    # Kusto query skill
        └── references/kusto-query-reference.md   # Full query cookbook
```

### Architecture layers

| Layer | File | Purpose |
|---|---|---|
| Plugin | `.claude-plugin/plugin.json` | Registers name/version with Claude Code |
| Agent | `agents/ff-oce.md` | Identity, hardcoded IDs, task procedures, behavioral rules |
| Dashboard skill | `skills/ff-oce-dashboard/SKILL.md` | Launches 6 parallel background agents |
| Kusto skill | `skills/ff-oce-kusto/SKILL.md` | Telemetry cluster config + query cookbook |
| Reference | `references/kusto-query-reference.md` | ~1500-line cookbook loaded on demand |

### Key hardcoded values

| Resource | Value |
|---|---|
| Service Tree ID | `3841020f-2a95-498a-9b5a-934676b350a9` |
| IcM: FF Hot | `98481` |
| IcM: Fluid Framework Client | `149377` |
| IcM: Azure Fluid Relay Client | `98313` |
| ADO Pipeline: Build | def `12` / `fluidframework` org |
| ADO Pipeline: E2E Real Service | def `56` / `fluidframework` org |
| ADO Pipeline: Service Clients E2E | def `80` / `fluidframework` org |
| ADO Pipeline: Stress | def `63` / `fluidframework` org |
| ADO Pipeline: Loop-FF Integration | def `29163` / `office` org → use `ado-office` MCP |
| Kusto cluster | `https://kusto.aria.microsoft.com` |
| Kusto DB ID | `6a8929bcfc6d44e9b13fee392ada9cf0` |
| FF Client OCE Teams channel | `19:25dabf309c5c42a7abe4647c7c1b7990@thread.skype` |

### Shift dashboard — parallel agent design

When asked to "generate shift dashboard", the skill spawns **6 background agents simultaneously** with a 90-second timeout:

```
Agent 1 → IcM (3 teams: 98481, 149377, 98313)
Agent 2 → ADO pipelines 12, 56, 63 (fluidframework org)
Agent 3 → ADO pipeline 29163 (office org, ado-office MCP)
Agent 4 → Kusto error rates (last 1h)
Agent 5 → Teams channel alerts (with expand: "replies")
Agent 6 → WorkIQ pending items
         ↓ (90s hard cutoff)
Consolidated markdown dashboard
```

**Critical:** Sub-agents don't inherit parent context — every prompt must be self-contained with all IDs and parameters.

---

## 3. Routerlicious Server Architecture

### Overview

Routerlicious is a distributed microservices server implementing Total Order Broadcast for Fluid documents. It receives, sequences, and broadcasts delta operations.

### End-to-End System Topology (High-Level Design)

```
                       ┌────────────────────────────────────────────────────────┐
                       │               ROUTERLICIOUS CORE BACKEND               │
                       └────────────────────────────────────────────────────────┘

 [ CLIENTS ]                     [ EDGE INGEST ]                  [ ORDERING LOG ]
 
┌───────────┐  WebSocket (submitOp)
│ Client A  ├────────────────────────┐
└───────────┘                        ▼
                               ┌───────────┐   producer.send()     ┌──────────────────────┐
                               │   NEXUS   ├──────────────────────►│  Kafka: [rawdeltas]  │
┌───────────┐   HTTP (REST)    └───────────┘   Key: tenant/docId   │ (Unsequenced Ops)    │
│ Client B  ├────────────────────────┬                             └──────────┬───────────┘
└───────────┘                        ▼                                        │
                               ┌───────────┐                                  │ partition consumer
                               │  ALFRED   ├──────────────────────────────────┘ (concurrency = 1)
                               └───────────┘                                  ▼
                                                                   ┌──────────────────────┐
                                                                   │     DELI LAMBDA      │
                                                                   │  * seq = ++seqNumber │
                                                                   │  * tracks MSN        │
                                                                   └──────────┬───────────┘
                                                                              │
                                                                              ▼
                                                                   ┌──────────────────────┐
                                                                   │   Kafka: [deltas]    │
                                                                   │  (TOTAL ORDER LOG)   │
                                                                   └──────────┬───────────┘
                         ┌────────────────────────────────────────────────────┼──────────────────────────────┐
                         │                                                    │                              │
                         ▼                                                    ▼                              ▼
                 [ LIVE BROADCAST ]                                  [ BULK DURABILITY ]             [ STATE & SNAPSHOTS ]
               ┌────────────────────┐                              ┌────────────────────┐          ┌─────────────────────┐
               │    BROADCASTER     │                              │    SCRIPTORIUM     │          │    SCRIBE LAMBDA    │
               │ (Kafka deltas sub) │                              │ (Stateless Logger) │          │ (Protocol Machine)  │
               └─────────┬──────────┘                              └─────────┬──────────┘          └──────────┬──────────┘
                         │                                                   │                                │
                         ▼ redis.publish()                                   ▼ insertMany(batch)              ▼ writeTree()
               ┌────────────────────┐                              ┌────────────────────┐          ┌─────────────────────┐
               │  REDIS PUB/SUB     │                              │      MONGODB       │          │  HISTORIAN / GIT    │
               │ (Channel: docId)   │                              │ (deltas collection)│          │ (Git Commit/Tree/Blob)
               └─────────┬──────────┘                              └─────────┬──────────┘          └──────────┬──────────┘
                         │                                                   ▲                                ▲
                         ▼ socket.emit("op")                                 │                                │
               ┌────────────────────┐                                        │                                │
               │   NEXUS SERVERS    │                                        │ Fetch deltas                   │ Fetch snapshot
               │ (Socket.io rooms)  │                                        │ (seq 101 to live)              │ (snapshot at seq 100)
               └─────────┬──────────┘                                        │                                │
                         │                                                   │                                │
                         ▼                                         ┌─────────┴────────────────────────────────┴──────────┐
                 [ ALL CONNECTED ]                                 │                 CLIENT C (NEW JOINER)                │
                     CLIENTS                                       │        Snapshot first -> Replay gaps -> Go live      │
                                                                   └──────────────────────────────────────────────────────┘
```

### Service map

| Service | Type | Port | Role |
|---|---|---|---|
| **Alfred** | HTTP + REST | 3003 (via nginx) | Op ingestion, document management, delta retrieval |
| **Nexus** | WebSocket | 3002 (via nginx) | Real-time client connections, live op delivery |
| **Riddler** | HTTP | 5000 | JWT authentication, tenant management |
| **Deli** | Kafka lambda | — | Sequence number assignment |
| **Scriptorium** | Kafka lambda | — | Persists sequenced ops to MongoDB |
| **Scribe** | Kafka lambda | — | Handles summaries, writes to Historian/Git |
| **Copier** | Kafka lambda | — | Archives raw ops |
| **Broadcaster** | Kafka lambda | — | Pushes sequenced ops to clients via Redis |
| **Historian** | HTTP | 3001 (via nginx) | Git-based snapshot storage |
| **GitRest** | HTTP | — | Git REST API wrapper |

### Infrastructure dependencies

| Service | Purpose | Config |
|---|---|---|
| Kafka | Ordered message queue | 8 partitions, `rawdeltas` + `deltas` topics, rdkafka |
| Zookeeper | Kafka coordination | |
| MongoDB | Persistent storage | deltas, documents, checkpoints, tenants |
| Redis (×4 logical) | Pub/sub, cache, throttle, tenant cache | All on `redis:6379` |
| Nginx | Reverse proxy | Routes ports 3001/3002/3003 |
| Git | Snapshot backend | Via GitRest + Historian |

### Key architectural patterns

1. **Kafka partitioning by document** — all ops for a given document are keyed to the same partition. Deli processes one message at a time per partition (queue concurrency=1), ensuring strict ordering.
2. **Stateless services** — all state lives in Kafka, MongoDB, Redis. Any service instance can crash and restart without data loss.
3. **Event sourcing** — the `deltas` Kafka topic is the source of truth. Scriptorium, Broadcaster, Scribe all derive from it independently.
4. **Factory/DI pattern** — `ResourcesFactory` + `RunnerFactory` wire dependencies at startup.

### Package responsibilities

| Package | Key role |
|---|---|
| `routerlicious` | Service entry points (`alfred/www.ts`, `nexus/www.ts`, `deli/index.ts`, etc.) |
| `routerlicious-base` | Base HTTP server + route factories |
| `lambdas` | Deli, Scribe, Scriptorium, Copier, Broadcaster, Nexus logic |
| `lambdas-driver` | Kafka consumer loop (`PartitionManager`, `Partition`, `CheckpointManager`) |
| `services` | MongoDB, Redis, Kafka producer/consumer implementations |
| `services-telemetry` | Lumberjack — structured telemetry engine |
| `services-utils` | HTTP middleware, Morgan logging, correlation ID propagation |

---

## 4. Op Flow End-to-End

### High-level flow

```
Client
  │ socket.io "submitOp"  OR  HTTP POST /deltas
  ▼
Nexus / Alfred
  │ producer.send() to Kafka [rawdeltas]
  ▼
Deli (lambdas/src/deli/lambda.ts)
  │ assigns sequenceNumber = ++this.sequenceNumber
  │ producer.send() to Kafka [deltas]
  ▼
  ├──► Scriptorium → MongoDB (persist)
  ├──► Scribe → Historian/Git (snapshots)
  ├──► Copier → MongoDB rawdeltas (archive)
  └──► Broadcaster → Redis pub/sub → Nexus → clients
```

### Exact code path with line numbers

| Step | File | Line | Action |
|---|---|---|---|
| WS op received | `lambdas/src/nexus/index.ts` | ~424 | `socket.on("submitOp", ...)` |
| WS sends to orderer | `lambdas/src/nexus/index.ts` | ~529 | `connection.order(sanitized)` |
| HTTP op received | `routerlicious-base/src/alfred/routes/api/api.ts` | 266 | `sendOp()` |
| Writes to rawdeltas | `routerlicious-base/src/alfred/routes/api/api.ts` | 284 | `producer.send([opMessage], tenantId, documentId)` |
| Kafka dispatch | `lambdas-driver/src/kafka-service/partition.ts` | 65 | `this.lambda!.handler(message)` |
| Deli handler | `lambdas/src/deli/lambda.ts` | 433 | `DeliLambda.handler()` |
| Sequence assignment | `lambdas/src/deli/lambda.ts` | 1693 | `return ++this.sequenceNumber` |
| Deli output | `lambdas/src/deli/lambda.ts` | 753 | `producer.send([message], tenantId, documentId)` |
| Scriptorium persist | `lambdas/src/scriptorium/lambda.ts` | 383 | `this.opCollection.insertMany(dbOps, false)` |
| Broadcaster emit | `lambdas/src/broadcaster/lambda.ts` | 238 | `this.publisher.emit(topic, "op", documentId, messages)` |
| Client room join | `lambdas/src/nexus/connect.ts` | 439 | `socket.join(getRoomId(room))` |

### Room ID format

`getRoomId(room)` → `"${tenantId}/${documentId}"`

This is both the Kafka routing key (all ops for a document go to the same partition) and the Socket.io room name (all subscribers to a document are in the same room).

### The Two Sequence Counters: clientSequenceNumber vs sequenceNumber

Every operation in Fluid carries two distinct sequence numbers with different lifetimes and scopes:

| Counter | Scope & Lifetime | Who Generates It? | Reset Behavior |
| :--- | :--- | :--- | :--- |
| **`clientSequenceNumber`** | **Per-Client, Per-Connection** | Client Browser Runtime | **Resets to `1`** every time a tab reconnects or opens. |
| **`sequenceNumber`** | **Global Document Lifetime** | Deli Server | **Never resets!** Monotonically counts $1 \dots \infty$ across all users. |

#### Why a New User Typing for the First Time Gets Assigned a Higher Sequence Number (e.g. 51 or 3):
1. **Existing Document:** If 50 ops were already created previously, the document counter in MongoDB is at `50`. When you type `'H'` for the first time in your session (`clientSequenceNumber = 1`), Deli advances the global counter from `50` to `51`.
2. **Brand-New Empty Document:** Even on a fresh document, your first edit will be Op #3:
   - Op #1: Document creation / summary attach op.
   - Op #2: Your `ClientJoin` protocol op (sequenced by Deli when your WebSocket connects).
   - Op #3: Your typed `'H'` (`clientSequenceNumber: 1` $\rightarrow$ global `sequenceNumber: 3`).

### Client Deduplication Algorithm in Deli (`checkOrder`)

When raw ops arrive from Kafka `rawdeltas`, Deli checks the incoming message against its in-memory `ClientSequenceNumberManager` (`clientSeqManager.ts`):

```typescript
// lambdas/src/deli/lambda.ts:1405-1424
const expectedClientSequenceNumber = client.clientSequenceNumber + 1;

if (clientSequenceNumber === expectedClientSequenceNumber) {
    return IncomingMessageOrder.ConsecutiveOrSystem; // VALID -> Mint sequenceNumber = ++this.sequenceNumber
} else if (clientSequenceNumber > expectedClientSequenceNumber) {
    return IncomingMessageOrder.Gap; // GAP -> Send NACK(400) to client to resend
} else {
    return IncomingMessageOrder.Duplicate; // DUPLICATE -> Silently drop! (line 905: return)
}
```
* **Guarantees:** If Alfred or a client network retry produces the same raw op twice, Deli discards the second copy **before** any global sequence number can be assigned.

### What is a Boxcar? (Kafka Op Batching & Coalescing)

**File:** `server/routerlicious/packages/services-core/src/messages.ts:199`

In Fluid Framework, a **Boxcar** (`IBoxcarMessage`) is the **batch envelope** used by the server to bundle multiple operations for a document into a single Kafka message payload.

#### The Real-World Analogy
Instead of sending 1 train locomotive down the track for every single letter you type, the train station puts all the letters inside **one train freight car (a "boxcar")** and sends them together down the tracks.

```
Individual Keystrokes:   ['H']   ['e']   ['l']   ['l']   ['o']
                           │       │       │       │       │
                           ▼       ▼       ▼       ▼       ▼
                     ┌───────────────────────────────────────────┐
Boxcar Envelope:     │            IBoxcarMessage                 │
                     │  documentId: "doc-101"                    │
                     │  contents: [ 'H', 'e', 'l', 'l', 'o' ]    │
                     └─────────────────────┬─────────────────────┘
                                           │
                                           ▼ (1 single Kafka message)
                                    [Kafka Broker]
```

#### The Data Structure (`messages.ts:199`)

```json
{
  "type": "boxcar",
  "tenantId": "my-tenant",
  "documentId": "doc-101",
  "contents": [
    { "clientId": "user-A", "clientSequenceNumber": 1, "contents": "H" },
    { "clientId": "user-A", "clientSequenceNumber": 2, "contents": "e" },
    { "clientId": "user-B", "clientSequenceNumber": 1, "contents": "l" }
  ]
}
```

#### The 4 Critical Reasons Boxcars Exist:
1. **Kafka Performance (10x–50x Speedup):** Writing 100 individual keystrokes to Kafka creates 100 TCP roundtrips, 100 partition index entries, and 100 disk commits. A Boxcar turns all 100 keystrokes into **1 single Kafka write, 1 partition offset, and 1 disk commit**.
2. **Event-Loop Micro-Batching (`setImmediate` in `rdkafkaProducer.ts:302`):** When multiple ops arrive during the same Node.js event-loop tick, `rdkafkaProducer` coalesces them into one pending Boxcar before flushing to Kafka.
3. **Guaranteed Atomic Arrival:** Because the envelope contains `documentId` at the root, Kafka hashes `murmur2(documentId)` and routes the entire bundle to the exact same partition at the exact same millisecond.
4. **Downstream Bulk Processing (`scriptorium/lambda.ts:383`):** Consumers unpack the boxcar via `extractBoxcar(message)`. Scriptorium executes a single high-speed `opCollection.insertMany(boxcar.contents, false)` bulk write into MongoDB rather than 100 individual database roundtrips.

---

## 5. Kafka Messaging, Backpressure, and Scaling

### Two-topic pipeline

```
[rawdeltas]  →  Deli (sole writer per partition)  →  [deltas]
                                                        │
                              ┌──────────────────────────┤
                              ▼                          ▼
                         Scriptorium              Broadcaster
                         Scribe                   Copier
```

**`rawdeltas`** = unsequenced ops submitted by clients  
**`deltas`** = sequenced ops with global sequence numbers — the total order

### Partition assignment

Ops are keyed by `tenantId/documentId`. All ops for the same document always land on the same Kafka partition. This is mandatory: Deli must be the sole writer for a partition to guarantee sequence number monotonicity.

### Backpressure when a consumer is slow

### Backpressure & Concurrency Architecture (Deli & Scriptorium)

```
══════════════════════════════════════════════════════════════════════════════════════════════════
 1. DELI BACKPRESSURE & STRICT MONOTONICITY (lambdas-driver / Partition.ts)
══════════════════════════════════════════════════════════════════════════════════════════════════

 Kafka [rawdeltas] Partition (Key: tenantId/documentId)
 ────────────────────────────────────────────────────────────
  [ Op 5 ]  [ Op 4 ]  [ Op 3 ]  [ Op 2 ]  [ Op 1 ]  ──► (Consumer Offset)
 ────────────────────────────────────────────────────────────
                                 │
                                 ▼ partition.ts
             ┌───────────────────────────────────────────────┐
             │       IN-MEMORY QUEUE (concurrency = 1)       │  <── Guarantees NO two ops for
             │  this.q = queue(lambda.handler, 1)            │      the same doc execute in parallel
             └───────────────────────┬───────────────────────┘
                                     │
                                     ▼
             ┌───────────────────────────────────────────────┐
             │                  DELI LAMBDA                  │
             │   1. Assigns sequenceNumber = ++seq           │
             │   2. Validates: refSeq <= seqNumber           │
             │   3. Advances MSN (watermark)                 │
             │   4. Emits to Kafka [deltas]                  │
             └───────────────────────┬───────────────────────┘
                                     │
                                     ▼ CheckpointManager.ts
             ┌───────────────────────────────────────────────┐
             │             CHECKPOINT COALESCING             │  <── If Kafka commit in-flight:
             │  `pendingCheckpoint` Deferred queues up       │      prevents commit storms to broker
             └───────────────────────────────────────────────┘

             ┌────────────────── ERROR / SLOW WORKER RECOVERY ──────────────────┐
             │  1. Deli fails / slow -> Context.emit("pause")                   │
             │  2. this.q.pause() & this.q.remove(() => true) (FLUSH QUEUE)     │
             │  3. On recover: re-read uncommitted messages from LAST CHECKPOINT│
             └──────────────────────────────────────────────────────────────────┘

══════════════════════════════════════════════════════════════════════════════════════════════════
 2. SCRIPTORIUM BACKPRESSURE & DOUBLE-BUFFERING (lambdas/src/scriptorium/lambda.ts)
══════════════════════════════════════════════════════════════════════════════════════════════════

 Kafka [deltas] Topic
 ────────────────────────────────────────────────────────────
  [ Seq 12 ]  [ Seq 11 ]  [ Seq 10 ]  [ Seq 9 ]  [ Seq 8 ]
 ────────────────────────────────────────────────────────────
                              │
                              ▼
        ┌───────────────────────────────────────────────────────────┐
        │                 DOUBLE-BUFFER MEMORY PATTERN              │
        │                                                           │
        │   [ PENDING BUFFER ]             [ CURRENT BUFFER ]       │
        │   Incoming ops accumulate        Being written to Mongo   │
        │   here asynchronously:           in a single bulk write:  │
        │   [ Seq 11, Seq 12, ... ]        [ Seq 8, Seq 9, Seq 10 ] │
        │               │                                │          │
        │               │         Buffer Swap            │          │
        │               └────────◄──────────►────────────┘          │
        │               (Swaps when current write finishes)         │
        └────────────────────────────────┬──────────────────────────┘
                                         │
                                         ▼
        ┌───────────────────────────────────────────────────────────┐
        │               CIRCUIT BREAKER FOR MONGODB                 │
        │                                                           │
        │   Writes batch via:                                       │
        │   `opCollection.insertMany(dbOps, { ordered: false })`    │
        │   * Tolerates duplicate key errors (code 11000 on replay) │
        │                                                           │
        │   FAIL-SAFE MONGO THRESHOLD:                              │
        │   If error rate > `errorThresholdPercentage`:             │
        │      1. Opens Circuit Breaker                             │
        │      2. Calls context.pause(lastSuccessOffset + 1)        │
        │      3. Kafka partition paused -> broker retains ops      │
        │      4. After `resetTimeout` ms -> auto-resumes partition │
        └────────────────────────────────┬──────────────────────────┘
                                         │
                                         ▼
                            ┌────────────────────────┐
                            │    MONGODB STORAGE     │
                            │  (Durable deltas log)  │
                            └────────────────────────┘
```

**File:** `lambdas-driver/src/kafka-service/partition.ts`

Each `Partition` has an async queue with **concurrency=1** (line 76):
```ts
this.q = queue((message, callback) => {
    this.lambda!.handler(message)?.then(callback).catch(callback);
}, 1);
```

When a consumer is slow:
1. Messages accumulate in the in-memory `QueueObject` — no automatic backpressure to Kafka broker
2. Kafka consumer lag grows (consumer offset falls behind broker head)
3. On error: `Context.emit("pause")` → `Partition.pause()` (line 156)
   - `this.q.pause()` — stops draining
   - `this.q.remove(() => true)` — **flushes all queued messages** (they'll be re-read from last checkpoint on resume)
4. On recovery: `Partition.resume()` → Kafka re-reads from last committed offset

**Checkpoint coalescing** (`checkpointManager.ts:62`): If checkpoint is already in-flight, new requests create a `pendingCheckpoint` Deferred that fires after the in-flight completes — prevents checkpoint storms.

**At-least-once delivery**: On crash, the service replays from last committed Kafka offset. DDSes must be idempotent (Scriptorium uses `insertMany` with duplicate-key tolerance: error code 11000).

### Circuit breaker (Scriptorium)

Scriptorium has a circuit breaker for MongoDB (`lambda.ts:90`):
- Opens when MongoDB error rate crosses threshold (`errorThresholdPercentage`)
- On open: calls `context.pause(lastSuccessfulOffset + 1, error)` — pauses the partition
- Resets after `resetTimeout` ms — resumes automatically

### Scaling

| Component | Scale unit | Maximum parallelism |
|---|---|---|
| Deli | 1 instance per Kafka partition | = number of partitions (8 by default) |
| Scriptorium | N instances (idempotent) | Unlimited |
| Broadcaster | N instances (Redis deduplicates) | Unlimited |
| Alfred | N stateless HTTP instances | Unlimited (behind Nginx) |
| Nexus | N instances with sticky sessions | Unlimited (Redis Socket.IO adapter) |

To scale beyond 8 Deli workers, increase Kafka partition count — but this requires topic reconfiguration.

### Rebalancing

When a consumer instance joins or leaves, Kafka triggers a rebalance (`partitionManager.ts:185`):
1. `rebalancing()` — closes all existing `Partition` objects
2. `rebalanced()` — creates new `Partition` objects for newly assigned partitions
3. Messages during rebalance are ignored (line 158: `if (this.isRebalancing) return`)

### Deli Container Replica Architecture

```
+===================================================================================================+
|                                KAFKA TOPIC: "rawdeltas" (8 Partitions)                            |
+===================================================================================================+
|  [Part 0]  |  [Part 1]  |  [Part 2]  |  [Part 3]  |  [Part 4]  |  [Part 5]  |  [Part 6]  |  [Part 7]  |
+-----+----------+------------+------------+------------+------------+------------+----------+------+
      |          |            |            |            |            |            |          |
      \----------/            \------------/            \------------/            \----------/
           |                        |                         |                        |
           v                        v                         v                        v
+----------------------+  +----------------------+  +----------------------+  +----------------------+
|  Deli Pod Replica 1  |  |  Deli Pod Replica 2  |  |  Deli Pod Replica 3  |  |  Deli Pod Replica 4  |
| Assigned: [P0, P1]   |  | Assigned: [P2, P3]   |  | Assigned: [P4, P5]   |  | Assigned: [P6, P7]   |
+----------+-----------+  +----------+-----------+  +----------+-----------+  +----------+-----------+
           |                         |                         |                         |
           v                         v                         v                         v
+----------------------------------------------------------------------------------------------------+
|                                    PERSISTENCE & DURABILITY LAYER                                  |
|  • MongoDB ("documents" collection): Periodically stores checkpoint sequence numbers & roster     |
|  • Kafka ("deltas" topic): Receives strictly ordered, sequenced ops from all active replicas       |
+----------------------------------------------------------------------------------------------------+
```

#### The 3 Operational Replica Scenarios:
1. **$R = P$ (8 Pods, 8 Partitions) — 1:1 Dedicated**: Each container sequences exactly 1 partition. Dedicated CPU core isolation, no contention between active documents on different partitions.
2. **$R < P$ (4 Pods, 8 Partitions) — 1:Many Multi-Tenancy**: Each pod instantiates multiple `Partition` objects in `PartitionManager`. Concurrency is shared within the Node.js event loop.
3. **$R > P$ (12 Pods, 8 Partitions) — Idle Warm Standbys**: Kafka assigns 0 partitions to the extra 4 pods. They sit idle as warm standbys ready to instantly claim partitions during node failure or rolling upgrade.

#### Inside a Single Deli Container Replica
- **Kafka Consumer**: Subscribed to group `deli`.
- **PartitionManager (`partitionManager.ts`)**: Routes incoming messages to `this.partitions.get(message.partition)`.
- **Partition (`partition.ts`)**: Runs an in-memory queue with `concurrency = 1`.
- **DocumentLambda (`documentLambda.ts`)**: Demuxes messages by `${tenantId}/${documentId}` to individual `DocumentPartition` instances.
- **Inactivity Eviction (`inactivityCheck`)**: Evicts idle documents (>10m) from memory to MongoDB to prevent Node.js OOM.
- **Soft-State Resilience**: No Persistent Volume Claims (PVC) needed. State is re-hydrated on demand from MongoDB checkpoints + Kafka offsets.

#### Failover Lifecycle Timeline:
```
T0: Pod 2 runs Partition 1 (SeqNo: 502) -> Checkpoints to MongoDB
T1: Pod 2 crashes (OOM / Node hardware failure) -> Heartbeat fails (session.timeout.ms)
T2: Kafka Group Coordinator triggers cooperative rebalance -> assigns Partition 1 to Pod 1
T3: Pod 1 instantiates new Partition(1) -> fetches checkpoint from MongoDB (#502)
T4: Pod 1 seeks Kafka consumer to offset 503 -> replays uncommitted rawdeltas
T5: Sequencing resumes (#503, #504...) with zero data loss and no split-brain risk
```

---

## 6. Scriptorium vs Scribe

### Scriptorium — Dumb Log Writer

**Files:** `lambdas/src/scriptorium/lambda.ts`

- Reads from Kafka `deltas` topic
- Writes sequenced ops to **MongoDB** `deltas` collection
- Stateless — knows nothing about document structure or protocol
- Double-buffer pattern: swaps `pending` ↔ `current` so new messages accumulate while the current batch is being written (line 235)
- Circuit breaker for MongoDB failures

```
Kafka [deltas] → ScriptoriumLambda → MongoDB.deltas
```

**Purpose:** Move ops from ephemeral Kafka storage to durable MongoDB before Kafka's retention window expires.

### Scribe — Protocol State Machine + Snapshot Coordinator

**Files:** `lambdas/src/scribe/lambda.ts`, `summaryWriter.ts`

- Reads from Kafka `deltas` topic
- Tracks per-document protocol state (sequence numbers, quorum, client joins/leaves)
- Handles summary ops: validates, builds Git tree, writes to **Historian**
- Produces `SummaryAck` or `SummaryNack` ops back to the `deltas` topic
- Generates **service summaries** autonomously when no clients are summarizing

```
Kafka [deltas] → ScribeLambda → SummaryWriter → Historian/Git
                             → SummaryAck/Nack → Deli → [deltas]
```

### Side-by-side comparison

| | Scriptorium | Scribe |
|---|---|---|
| Stateful per document? | No | Yes |
| Writes to | MongoDB `deltas` | Historian/Git |
| Handles all ops? | Yes (all `SequencedOperationType`) | Only summary ops + protocol tracking |
| Output | MongoDB records | Git commits + Ack/Nack ops |
| Failure mode | Circuit breaker → pause | Nack the summary, client retries |

### Why service summaries exist (from `scribe/README.md`)

> "The service must write a summary because op storage is not guaranteed to be persistent. The service summary, initiated by scribe, moves data from short term op storage to long term summary storage. While there are typically clients available to write the summary, there are many scenarios where there are no clients available. For example, there may be no clients to write a summary when there's an unexpected network outage or the only connected client suddenly disconnects due to low battery."

### MongoDB Storage Map Across Services

MongoDB serves as the durable system of record for Routerlicious, while Kafka acts as the ephemeral streaming log.

| Service | MongoDB Collection(s) | Key Fields / Document Schema | Architectural Purpose |
| :--- | :--- | :--- | :--- |
| **Scriptorium** | **`deltas`** | `tenantId`, `documentId`, `sequenceNumber`, `operation`, `clientId`, `timestamp` | **Durable Op Log.** Permanent append-only history of all sequenced ops. Powers client catch-up API (`GET /deltas`). Enforces compound unique index `{ tenantId: 1, documentId: 1, sequenceNumber: 1 }` to guarantee idempotent replay. |
| **Deli** | **`documents`** (`document.deli`) & **`checkpoints`** | `sequenceNumber`, `logOffset` (Kafka raw offset), `clients` (roster + clientSeqNo), `durableSequenceNumber`, `lastSentMSN` | **Sequencer Soft-State Recovery.** Enables replacement Deli pods to rehydrate monotonic sequence counters and resume Kafka consumption without missing or repeating ops. |
| **Scribe** | **`documents`** (`document.scribe`), **`scribeDeltas`** | `logOffset` (Kafka deltas offset), `sequenceNumber`, `protocolState` (quorum members, MSN), `lastSummary` (Git commit SHA) | **Snapshot Tracking & Quorum.** Tracks which Git commit SHA represents the latest snapshot. Enables Scribe restart without re-summarizing. |
| **Riddler** | **`tenants`** | `tenantId`, `secret` (symmetric key for JWT verification), `ordererUrl` (Kafka cluster endpoint), `historianUrl` | **Multi-Tenant Auth & Sharding.** Validates JWT tokens on client connection and routes tenants to specific physical clusters. |
| **Alfred / Nexus** | **`documents`**, **`reservations`**, **`nodes`** | Document metadata (`createTime`, `isEphemeralContainer`), active `document.session` cluster location, socket affinity | **Session Lifecycle & Sticky Routing.** Prevents multi-cluster session collisions. |
| **Copier** *(Optional)* | **`rawdeltas`** | `tenantId`, `documentId`, `index`, raw unsequenced ops | **Raw Audit Archival.** Archival log of raw inbound ops before Deli sequencing for compliance or debugging. |

---

## 7. Total Order Broadcast (ToB)

### What ToB is

Total Order Broadcast guarantees:
1. Every participant receives every message
2. All participants receive messages **in the same order**

In Fluid: Kafka + Deli together implement ToB for document ops.

### Why ToB instead of OT (Operational Transform)

OT requires a transformation function for every pair of concurrent operation types:
- Transform functions grow O(N²) with operation types
- Correctness proofs are notoriously subtle (original OT papers had bugs found ~20 years later)
- Hard to implement correctly (Google Docs' OT took years)

With ToB, every client sees ops in the same `sequenceNumber` order, so no pairwise transforms are needed.

### Why ToB instead of pure CRDTs

CRDTs are designed for peer-to-peer, no-central-authority settings. The cost:
- Metadata overhead: tombstones, vector clocks, per-element unique IDs
- Memory/payload size: RGA/Yjs-style sequence CRDTs encode position per-character
- No global snapshot point: without total order, "summarizing" state is harder
- Long-lived documents accumulate tombstone debt that is hard to GC

ToB gives Fluid:
- Cheap snapshots at any sequence number N
- Trivial GC: once all clients ack seq N, anything older can be collapsed
- Smaller op payloads: no replica IDs or vector clocks needed
- Simpler DDS implementations

**The tradeoff:** Fluid requires the relay service to make progress (no offline-first). Microsoft's target (Office, Teams, Loop) is cloud-connected, making this acceptable.

### How ToB maps to code

```
Client A submits op → Alfred → Kafka [rawdeltas]  ←  Client B also
                                      │
                                    Deli (sole writer per partition)
                                    seq = ++this.sequenceNumber  // line 1693
                                      │
                               Kafka [deltas, seq=N]
                                      │
             ┌────────────────────────┼──────────────────┐
             ▼                        ▼                   ▼
        Broadcaster              Scriptorium           Scribe
        (all clients)            (MongoDB)             (snapshots)
```

The `deltas` topic IS the total order. All consumers read it in sequence-number order.

### Distributed Eventing Patterns in Fluid Framework

Beyond Total Order Broadcast, Routerlicious combines four recognized distributed systems patterns:

1. **Total Order Broadcast (ToB) / Atomic Broadcast**: Deli acts as the single sequencing authority over Kafka `rawdeltas`, guaranteeing that all clients and backend replicas receive events in the exact same sequence.
2. **Event Sourcing + Log Compaction (Snapshots)**: The source of truth is an immutable log of delta ops. The document's state is $f(\text{Snapshot}, \sum \text{Deltas})$. Summaries stored in GitRest truncate the log to avoid replaying millions of historical ops.
3. **CQRS (Command Query Responsibility Segregation)**:
   - **Command Path (Write)**: High-throughput Kafka pipeline (`rawdeltas` $\rightarrow$ Deli $\rightarrow$ `deltas`). Never performs database queries.
   - **Query Path (Read)**: Catch-up queries hit MongoDB `deltas` and GitRest snapshots directly. Never touches Kafka.
4. **Three-Tier Publish-Subscribe (Pub/Sub) with Fan-out**:
   - *Tier 1 (Kafka)*: Persistent broker log for cluster durability.
   - *Tier 2 (Redis)*: In-memory document channels for cross-pod gateway distribution.
   - *Tier 3 (Socket.io WebSockets)*: Edge broadcast to active browsers.
5. **Ephemeral Fire-and-Forget Signals (`ISignalMessageBase`)**: Non-stateful real-time presence (cursor tracking, selection highlights, typing indicators) completely bypasses Kafka, Deli, Mongo, and GitRest, streaming directly over Socket.io rooms.

### Choreography vs. Orchestration: How Services Coordinate

Fluid uses a hybrid architectural pattern: **Event-Driven Choreography for the real-time op streaming path**, and **Localized Orchestration for the snapshotting workflow**:

```
1. REAL-TIME OP STREAM: PURE CHOREOGRAPHY (Decentralized Event Bus)
─────────────────────────────────────────────────────────────────────────────
[Alfred] ──► Kafka: [rawdeltas] ──► [Deli] ──► Kafka: [deltas]
                                                    │
                               ┌────────────────────┼────────────────────┐
                               ▼                    ▼                    ▼
                        [Broadcaster]         [Scriptorium]           [Scribe]
                       (Pushes to Redis)    (Writes to Mongo)      (Quorum update)

• No master coordinator commands Scriptorium or Broadcaster.
• Services independently react to Kafka events.
• High throughput, zero single-coordinator bottleneck, fault-isolated.


2. SNAPSHOT PIPELINE: LOCALIZED ORCHESTRATION (Scribe & Client Summarizer)
─────────────────────────────────────────────────────────────────────────────
                     [Scribe Snapshot Orchestrator]
                                   │
      ┌────────────────────────────┼────────────────────────────┐
      ▼                            ▼                            ▼
  Step 1: Check Quorum     Step 2: Historian/GitRest    Step 3: summaryAck
 (Validates parent SHA)     (Commits Git blobs/trees)   (Emits to Kafka deltas)

• Strict multi-step transactional coordination.
• Scribe acts as an in-service orchestrator managing storage commit, ack emission, and Mongo checkpoints.
```

| Dimension | Op Pipeline (Choreography) | Summary Pipeline (Orchestration) |
| :--- | :--- | :--- |
| **Control Model** | Decentralized, event-driven | Centralized controller (`Scribe` / Summarizer) |
| **Communication** | Asynchronous Kafka topics (`rawdeltas`, `deltas`) | Synchronous RPC / REST (Scribe $\rightarrow$ Historian $\rightarrow$ GitRest) |
| **Coupling** | Zero (services operate autonomously) | Tightly coupled across protocol state and Git storage |
| **Optimization** | Sub-millisecond latency, massive fan-out | Strict consistency, durable snapshot integrity |

---

## 8. Why Git for Snapshots

**Files:** `lambdas/src/scribe/summaryWriter.ts`

### Reasons

**1. Content-addressable storage**  
Every Git blob/tree is identified by SHA-1 of its content. Unchanged subtrees between summaries share the same SHA — zero bytes stored. A service summary that only updates `.logTail` reuses `.app` and `.protocol` handles from the previous commit.

```ts
// summaryWriter.ts:880 — service summary reuses existing subtrees
".app": { type: SummaryType.Handle, handle: ".app", handleType: SummaryType.Tree }
```

**2. Immutable history**  
Each summary is a Git commit with a parent pointer. Full snapshot history for free — useful for debugging and rollback.

**3. Hierarchical tree maps to Fluid's container structure**  
A Fluid container has a natural tree:
- `.app` — data channels (DDS state)
- `.protocol` — quorum state (members, proposals, values)
- `.logTail` — ops since last summary
- `.serviceProtocol` — Deli + Scribe checkpoint state

Git trees are exactly nested directories of content.

**4. Hot/warm/cold storage separation**

| Storage | Lifetime | Where |
|---|---|---|
| Kafka `deltas` | Short (retention period) | Broker |
| MongoDB `deltas` | Medium (Scriptorium writes here) | Database |
| Git via Historian | Permanent | Object store |

### Two summary upload modes

| Mode | API | When |
|---|---|---|
| WholeSummary | `WholeSummaryUploadManager.writeSummaryTree()` | Production (single API call) |
| Incremental | `createTree()` → `createGitTree()` → `createCommit()` → `upsertRef()` | Fallback (multiple round trips) |

### Client summary flow (`summaryWriter.ts:120`)

1. Validate parent ref matches last known summary SHA
2. Validate `referenceSequenceNumber >= checkpoint.protocolState.sequenceNumber`
3. Build `.logTail`: ops from last protocol head to summary seq (from memory + MongoDB gaps)
4. Build `.protocol`: quorum state from `getQuorumTreeEntries()`
5. Build `.serviceProtocol`: Deli + Scribe state JSON
6. Combine with client's `.app` handle
7. Write Git tree → commit → upsert ref
8. Produce `SummaryAck` op back to op stream

### GitRest Storage Engine (`server/gitrest`)

GitRest is the dedicated microservice that manages the low-level Git object database:
- **Interface:** Exposes REST endpoints (`/git/blobs`, `/git/trees`, `/git/commits`, `/summaries`) consumed by Historian.
- **Git Primitives:**
  - **Blobs:** Content-addressable raw bytes for DDS states and configurations.
  - **Trees:** Directory representations mapping container component namespaces (`.app`, `.protocol`, `.serviceProtocol`).
  - **Commits:** Uniquely identified by SHA-1/SHA-256, storing parent commit pointers and sequence number watermarks.
- **WholeSummary Optimization (`GitWholeSummaryManager` in `summaries.ts`):** Allows uploading an entire nested summary tree in a single API call instead of recursive multi-roundtrip HTTP requests, drastically reducing snapshot latency.

---

## 9. How a New User Joins an Existing Session

The system cannot replay all ops from the beginning (could be millions). Instead it uses **Snapshot + Delta Catchup**:

```
[New User: Bob Opens Document]
       │
       ├─► 1. Fetch Latest Snapshot ──► Alfred ──► GitRest ──► Returns Snapshot at Op #950
       │     (Hydrates local DDSes to state at Op 950)
       │
       ├─► 2. Connect WebSocket ──────► Nexus ──► Joins Room (refSeq = 950)
       │
       ├─► 3. Catch-Up Deltas ────────► Alfred ──► MongoDB (deltas) ──► Replays Ops 951..1000
       │     (Fast-forwards from 950 to 1000)
       │
       └─► 4. Live Stream ────────────► Nexus ──► Receives Op 1001, 1002... via WebSocket
```

### Step 1 — Fetch Snapshot from GitRest (via Historian)

When Bob opens a document where Alice has generated 1,000 ops and the latest snapshot is at Op 950:
- Bob's browser asks Alfred: `GET /{tenantId}/{documentId}/commits/latest`.
- Alfred forwards to **Historian $\rightarrow$ GitRest** (`summaries.ts`).
- GitRest returns the complete tree at commit SHA `a3f9e...` (representing `sequenceNumber: 950`).
- Bob's browser initializes the Fluid container in memory and hydrates all DDSes to their state at Op 950.

### Step 2 — Connect via Nexus WebSocket

- Bob opens a WebSocket connection to **Nexus**: `connect(referenceSequenceNumber: 950)`.
- Nexus authenticates Bob, assigns `clientId: "client-B"`, and registers him in the Socket.io room (`tenantId/documentId`).
- Nexus broadcasts a `ClientJoin` op so Alice sees Bob's presence.

### Step 3 — Fetch Catch-Up Ops from MongoDB (via Alfred)

- Bob is at Op 950, but the live session is at Op 1000.
- Bob's client runtime automatically queries Alfred's REST endpoint:
  ```http
  GET /deltas/{tenantId}/{documentId}?from=951&to=1000
  ```
- Alfred queries **MongoDB's `deltas` collection** (populated by Scriptorium).
- MongoDB returns ops 951 through 1000.
- Bob's `ContainerRuntime` replays ops 951..1000 into the in-memory DDSes, fast-forwarding state from 950 to 1000.

### Step 4 — Seamless Handover to Live Stream

- Bob is now fully synchronized with the room.
- Any subsequent ops (1001, 1002...) arrive live over the WebSocket via the Broadcaster/Redis pipeline.

### Why not replay from Kafka/MongoDB?

| Approach | Cost |
|---|---|
| Replay all ops from scratch | O(total ops) — could be millions |
| Snapshot + catchup | O(ops since last snapshot) — typically hundreds |

Scribe's service summaries cap the catchup gap — even without client summaries, the service summarizes periodically.

```
Timeline of ops:
────────────────────────────────────────────────────→
     snapshot@seq500          live@seq523
          │                       │
New user: │                       │
  1. fetch snapshot@500 ──────────┘
  2. fetch ops 500→523 ───────────────────────────→─┤
  3. subscribe to live ──────────────────────────→──┘
```

---

## 10. Observability Architecture

**Packages:** `server-services-telemetry`, `server-services-utils`

### Three pillars

| Pillar | Technology | Purpose |
|---|---|---|
| Structured telemetry | Lumberjack → Winston | All logs and metrics |
| HTTP request metrics | Morgan middleware | Per-request latency, status, path |
| Op-level latency | Telegraf (TCP) → InfluxDB | Per-hop timestamps on each op |

### Lumberjack — core telemetry engine

**Files:** `services-telemetry/src/lumberjack.ts`, `lumber.ts`, `resources.ts`

```
Lumberjack (singleton)
    ├── ILumberjackEngine[]    ← pluggable backends
    ├── ILumberjackSchemaValidator[]  ← property validation
    └── ILumberFormatter[]    ← sanitization/redaction
```

#### Two event types

| Type | Usage | Lifecycle |
|---|---|---|
| `Metric` | `Lumberjack.newLumberMetric(eventName)` | Open → accumulate properties → `success()` or `error()` |
| `Log` | `Lumberjack.info/warn/error(message)` | Fire-and-forget |

#### Lumber — telemetry event object

- `_startTime = performance.now()` at creation
- `durationInMs` auto-computed at `success()`/`error()` call
- `id = uuid()` — for cross-event correlation (e.g., linking Scribe metrics)
- Guard: re-completing a Lumber emits `LumberjackError`, doesn't crash

#### Named events (complete list from `lumberEventNames.ts`)

| Category | Events |
|---|---|
| Service lifecycle | `RunService`, `GracefulShutdown`, `AlfredRunner`, `NexusRunner`, `KafkaRunner` |
| Lambda handlers | `DeliHandler`, `ScribeHandler`, `ScriptoriumProcessBatch` |
| Summaries | `ClientSummary`, `ServiceSummary`, `SummaryReader` |
| Sessions | `NexusSessionStart`, `NexusSessionResult`, `ConnectDocument`, `DisconnectDocument` |
| HTTP | `HttpRequest`, `RestWrapper`, `SocketIoRequest`, `GetSession`, `VerifyStorageToken` |
| Reliability | `CircuitBreaker`, `RunWithRetry`, `RequestWithRetry`, `GlobalCheckpointError` |
| Health | `StartupProbe`, `LivenessProbe`, `ReadinessProbe`, `MongoMonitoring` |

### WinstonLumberjackEngine

**File:** `services-utils/src/winstonLumberjackEngine.ts`

Serializes every `Lumber` to a structured JSON object and calls `winston.log()`:
```json
{
  "eventName": "ScriptoriumProcessBatch",
  "id": "<uuid>",
  "properties": "{...all key-value pairs...}",
  "type": "Metric",
  "timestamp": "2026-05-15T...",
  "durationInMs": 42.3,
  "successful": true
}
```

### Schema validation

| Validator | Required fields |
|---|---|
| `BasePropertiesValidator` | `tenantId`, `documentId` |
| `LambdaSchemaValidator` | + `topic`, `partition`, `offset` |

Validation failure emits `LumberjackSchemaValidationFailure` — logged but doesn't throw.

### Sanitization / PII redaction

**File:** `services-telemetry/src/sanitizationLumberFormatter.ts`

`BaseSanitizationLumberFormatter` (always active):
- Redacts `Authorization` headers from Axios error objects
- Redacts `error.command.args`

`SanitizationLumberFormatter` (opt-in):
- Recursively walks exception objects
- Redacts keys matching: `cookie`, `password`, `secret`, `token`, `api_key`, `session_id`, `auth*`
- Records `detectedSensitiveKeys` property so you know what was redacted

### Distributed correlation — correlationId + AsyncLocalStorage

**Files:** `services-utils/src/asyncContext.ts`, `telemetryContext.ts`

```
HTTP Request arrives
    ↓
bindTelemetryContext(serviceName) middleware
    reads x-correlation-id header (or generates UUID)
    reads x-telemetry-context header (JSON: tenantId, documentId, correlationId)
    ↓
AsyncLocalStorageTelemetryContext.bindProperties({correlationId, tenantId, documentId})
    → Node.js AsyncLocalStorage — flows through all .then() / await chains
    ↓
Every Lumberjack call auto-merges getGlobalTelemetryContext().getProperties()
    → every log line carries correlationId, tenantId, documentId automatically
    ↓
Response sets: x-correlation-id: <id>  (for client-side correlation)
```

**Internal calls** set `x-telemetry-context` header with `requestSource: "server"` to distinguish from client calls.

### HTTP request metrics — Morgan middleware

**File:** `services-utils/src/morganLoggerMiddleware.ts`

`jsonMorganLoggerMiddleware()` emits a `LumberEventName.HttpRequest` metric per response with:
- `pathCategory` = `baseUrl + route.path` (grouped, avoids cardinality explosion from document IDs in URLs)
- `durationInMs` = server-only processing time (not wire time)
- `responsePrefinishToFinishLatencyMs` = OS buffer flush time
- `responseFinishToCloseLatencyMs` = wire delivery time
- `clientDisconnected` / `serverTimeout` distinction for 499 errors
- Optional `eventLoopLagMs` via `monitorEventLoopDelay()` from `perf_hooks` (disabled by default — has overhead)

### Telegraf — op latency metrics

**File:** `services/src/metricClient.ts`

Each op carries an `ITrace[]` array stamped at each service hop. `TelegrafClient` converts these to InfluxDB measurements via TCP.

```ts
row[`${trace.service}-${trace.action}`] = new Float(trace.timestamp)
```

Pipeline: Telegraf TCP → InfluxDB → Grafana dashboards.

---

## 11. DDS Architecture

### Where DDSes fit

```
Application code
    ↓ reads/writes data
DDS (SharedMap, SharedTree, SharedString...)
    ↓ submitLocalMessage() / processMessages()
FluidDataStoreRuntime  ← owns one or more DDS channels
    ↓
ContainerRuntime       ← owns one or more DataStores, handles batching + GC
    ↓
DeltaManager / Driver  ← sends/receives ops to/from Routerlicious
```

### Class hierarchy

```
EventEmitterWithErrorHandling
    │
SharedObjectCore<TEvent>          ← abstract base (sharedObject.ts)
    │   • op submission, delta handler attachment
    │   • processMessages() with pre-op/op events
    │   • resubmit on reconnect, stashed op replay
    │   • closeWithError() for error isolation
    │
SharedObject<TEvent>              ← adds synchronous summarization
    │   • summarize(), getAttachSummary()
    │   • getGCData() via GCHandleVisitor
    │
    ├── SharedMap / SharedDirectory   (dds/map/)
    ├── SharedCounter                 (dds/counter/)
    ├── SharedString (→ MergeTree)    (dds/sequence/, dds/merge-tree/)
    ├── SharedCell                    (dds/cell/)
    └── SharedObjectFromKernel        ← composition pattern (sharedObjectKernel.ts)
            └── SharedTree            (dds/tree/)
```

### Two DDS implementation patterns

**Legacy (inheritance):** Subclass `SharedObject`, implement abstract methods directly.

**Modern (composition — `SharedKernel`):**
```
SharedObjectFromKernel<TOut>
    ├── kernel: SharedKernel    ← processMessagesCore(), summarizeCore(), reSubmitCore()
    └── view: TOut              ← app-facing API
```
`mergeAPIs()` (line 327 in `sharedObjectKernel.ts`) grafts `view` properties onto the wrapper using `Object.defineProperty`. Used by SharedTree.

### IChannelFactory — DDS registration

Every DDS type is registered via `IChannelFactory`:
- `type: string` — unique type identifier (e.g., `"https://graph.microsoft.com/types/map"`)
- `create(runtime, id)` — creates a new DDS instance
- `load(runtime, id, services, attributes)` — loads a DDS from snapshot

`createSharedObjectKind(factory)` wraps a factory class into both `ISharedObjectKind` (encapsulated API) and `SharedObjectKind` (declarative API).

### DDS Lifecycle

```
1. Creation (local/detached)
   SharedMap.create(runtime, "id")
   → initializeLocal() → initializeLocalCore()
   → isAttached() = false, no ops sent

2. Binding to container
   map.bindToContext()
   → runtime.bindChannel(this)
   → runtime.once("attaching", () => didAttach())

3. Loading from snapshot
   factory.load(runtime, id, services, attributes)
   → loadCore(services.objectStorage)  ← reads snapshot blob
   → attachDeltaHandler()               ← registers IDeltaHandler
   → setConnectionState(connected)

4. Connected, receiving ops
   IDeltaHandler.processMessages(collection) is called by runtime
   → processMessages() → processMessagesCore()
```

### Op submission flow

```ts
// App code:
map.set("key", value);

// Inside SharedMap kernel:
this.submitLocalMessage({ type: "set", key, value }, localOpMetadata);

// SharedObjectCore.submitLocalMessage() (line 435):
const content = makeHandlesSerializable(op, this.serializer, this.handle);
this.services.deltaConnection.submit(content, localOpMetadata);
// → FluidDataStoreRuntime → ContainerRuntime → batch → Alfred → Deli
```

`localOpMetadata` is **never sent to the server**. It is stored locally and returned when the ack arrives, allowing the DDS to reconcile optimistic state with the now-official sequence number.

### Op processing flow

```
ISequencedDocumentMessage arrives from Routerlicious
    ↓
ContainerRuntime.processRemoteMessage()
    ↓ routes by dataStore address
FluidDataStoreRuntime.processMessage()
    ↓ routes by channel id
IDeltaHandler.processMessages(collection)
    ↓
SharedObjectCore.processMessages()     (sharedObject.ts:605)
    1. parseHandles(contents, serializer)   ← deserialize IFluidHandle refs
    2. emit("pre-op", message, local)
    3. processMessagesCore(decodedCollection)  ← DDS merge logic
    4. emit("op", message, local)
```

`sequenceDifference = sequenceNumber - referenceSequenceNumber` is sampled as telemetry. High values = high concurrent activity = more merge work per op.

### Reconnection — resubmit flow

On reconnect, runtime calls `reSubmit(content, localOpMetadata, squash)` for each pending unacked op:
- `squash=false` → `reSubmitCore()` → resubmit same op with current `referenceSequenceNumber`
- `squash=true` → `reSubmitSquashed()` → collapse redundant ops (e.g., multiple `map.set()` on same key → only last one)

**Stashed ops** (offline changes): `applyStashedOp(content)` replays pending changes against current state when rehydrating.

### Summarization

```
ContainerRuntime.summarize()
    → DataStore.summarize()
    → Channel.summarize()
    → SharedObject.summarize()           (sharedObject.ts:814)
    → this.summarizeCore(serializer)     ← DDS-specific JSON serialization
    → ISummaryTreeWithStats              ← tree of blobs with size stats
```

Blob count and size stats flow up to ContainerRuntime to decide incremental vs full summary.

**GC traversal** reuses summarization: `GCHandleVisitor` replaces the serializer — instead of writing bytes, it records which `IFluidHandle` paths were visited. Those paths become outbound GC references.

### Error isolation

If an event listener throws during `emit()`:

```ts
// sharedObject.ts:269
private eventListenerErrorHandler(event, e) {
    const error = DataProcessingError.wrapIfUnrecognized(e, "SharedObjectEventListenerException");
    this.closeWithError(error);   // DDS set to permanently closed state
    throw error;                  // propagates to container → container closes
}
```

Once `closeWithError()` is called, every subsequent `submitLocalMessage()` or `processMessages()` re-throws the original error via `verifyNotClosed()`. The DDS is dead and the container closes.

### Available DDSes

| DDS | Package | Data model | Conflict strategy |
|---|---|---|---|
| `SharedMap` | `dds/map` | Key→value | Last-write-wins per key |
| `SharedDirectory` | `dds/map` | Hierarchical key-value | LWW per path |
| `SharedCounter` | `dds/counter` | Integer | Commutative addition |
| `SharedString` | `dds/sequence` | Rich-text sequence | MergeTree CRDT |
| `SharedMatrix` | `dds/matrix` | 2D grid | Sparse grid + MergeTree |
| `SharedCell` | `dds/cell` | Single typed value | LWW |
| `SharedTree` | `dds/tree` | Typed schema tree | Rebase-based changesets |
| `TaskManager` | `dds/task-manager` | Distributed queue | Consensus quorum |
| `PactMap` | `dds/pact-map` | Consensus key-value | Quorum-based, not LWW |

---

## 12. Collaborative Editing — Sequence Numbers Walkthrough

### Protocol message fields

#### `IDocumentMessage` — what the client sends

| Field | Who sets it | Meaning |
|---|---|---|
| `clientSequenceNumber` | Client | Per-client monotonic counter. Used to match a returning ack to a pending local op. Resets on new connection. |
| `referenceSequenceNumber` | Client | "I was looking at this server state when I made this change." Used by DDS merge logic to rebase concurrent ops. |
| `type` | Client | `"op"` for user ops, `"summarize"` for summary requests |
| `contents` | Client | DDS-specific operation payload |

#### `ISequencedDocumentMessage` — what Deli produces

All fields above, plus:

| Field | Who sets it | Meaning |
|---|---|---|
| `sequenceNumber` | Deli | Global total order. The canonical identity of an op. Never changes. |
| `minimumSequenceNumber` (MSN) | Deli | Lowest `referenceSequenceNumber` among all connected clients. The GC floor — everything below is safe to compact. |
| `clientId` | Nexus (at connect) | Which client sent this op. New clientId on each reconnect. |
| `timestamp` | Deli | Server time when ticketed |

### Concrete example: two users editing simultaneously

**Starting state:** Document = `"Hello World"` at `sequenceNumber=10`.  
**Alice** (`clientId: "A"`): inserts `"!"` at position 11.  
**Bob** (`clientId: "B"`): inserts `" Everyone"` at position 5.  
Both are at `lastSequenceNumber=10` when they type.

#### What Alice sends

```json
{
  "clientSequenceNumber": 1,
  "referenceSequenceNumber": 10,
  "type": "op",
  "contents": { "pos1": 11, "seg": "!", "type": "insert" }
}
```

#### What Bob sends (simultaneously)

```json
{
  "clientSequenceNumber": 1,
  "referenceSequenceNumber": 10,
  "type": "op",
  "contents": { "pos1": 5, "seg": " Everyone", "type": "insert" }
}
```

#### After Deli sequences (Alice arrives 3ms first)

**seq=11 (Alice's op):**
```json
{
  "clientId": "A", "sequenceNumber": 11,
  "minimumSequenceNumber": 10,
  "clientSequenceNumber": 1,
  "referenceSequenceNumber": 10,
  "contents": { "pos1": 11, "seg": "!", "type": "insert" }
}
```

**seq=12 (Bob's op):**
```json
{
  "clientId": "B", "sequenceNumber": 12,
  "minimumSequenceNumber": 10,
  "clientSequenceNumber": 1,
  "referenceSequenceNumber": 10,
  "contents": { "pos1": 5, "seg": " Everyone", "type": "insert" }
}
```

`sequenceDifference`:
- Alice: `11 - 10 = 1` (1 op behind — her own)
- Bob: `12 - 10 = 2` (2 ops behind — Alice's and his own)

#### Both clients converge to: `"Hello Everyone World!"`

**How:** The MergeTree doesn't store positions as integers — it stores segments identified by `{clientId, clientSequenceNumber}`. When Bob says "pos=5 at refSeq=10", the MergeTree records "insert relative to the segment boundaries at refSeq=10". Alice's insert at pos=11 (end) doesn't affect Bob's insert at pos=5 (before "World") — they're in different segment ranges. Both inserts commute correctly.

### MSN as the GC watermark

After both ops are applied and both clients send their next op/NoOp with `referenceSequenceNumber=12`, Deli sets `minimumSequenceNumber=12` on the next op. The MergeTree can now **physically remove** any tombstoned segment deleted before seq=12 — no client needs to reference it for merge purposes anymore.

### What happens on Nack

If Bob submits with a `referenceSequenceNumber` too far in the past, Deli responds:

```json
{
  "operation": { ...Bob's op... },
  "sequenceNumber": 12,
  "content": {
    "code": 400,
    "type": "BadRequestError",
    "message": "Nack - reference sequence number too old"
  }
}
```

Bob must catch up to seq=12 before resubmitting.

### New client joining mid-session (Charlie at seq=12)

1. Fetches snapshot at seq=10 from Historian: `"Hello World"`
2. Fetches ops 11 and 12 from Alfred's delta endpoint
3. Applies op 11 (Alice's `!`) → `"Hello World!"`
4. Applies op 12 (Bob's `" Everyone"`) → `"Hello Everyone World!"`
5. Subscribes to live Nexus WebSocket from seq=13 onward

### Reconnection with stashed ops (Bob disconnects before ack)

1. Bob disconnects. His `clientSequenceNumber=1` op is stashed locally.
2. On reconnect: new `clientId: "B2"`, receives `initialMessages` with ops sequenced while offline.
3. Runtime calls `reSubmit(content, localOpMetadata)` for each stashed op.
4. Bob resubmits `" Everyone"` with updated `referenceSequenceNumber = currentSeq`.
5. Deli assigns new sequence number (e.g., seq=15).

---

## 13. Data Corruption Scenarios

Two error types used throughout:
- **`DataCorruptionError`** — structural violation. If persisted, document fails to load for **all** clients on every reload.
- **`DataProcessingError`** — processing failure. May be transient (service issue) or permanent (truly corrupted).

Both cause container closure.

### 1. Non-sequential sequence number

**File:** `packages/loader/container-loader/src/deltaManager.ts:1151`  
**Error:** `"Found a non-Sequential sequenceNumber"`

**Trigger:** Client receives seq=15 but last processed was seq=13 (gap) or receives seq=15 again (duplicate).  
**Why fatal:** Merges operate on wrong state. All future merges diverge from every other client permanently.

### 2. MSN moves backward

**File:** `deltaManager.ts:1127`  
**Error:** `"Invalid MinimumSequenceNumber from service - document may have been restored to previous state"`

**Trigger:** New op arrives with `minimumSequenceNumber` lower than previously seen. Usually means the service was restored from a backup.  
**Who fails:** Only clients that had processed past the restored MSN. Other clients can still connect.

### 3. MSN ≥ sequence number

**File:** `deltaManager.ts:1141`  
**Error:** `"MSN has to be lower than sequence #"`

**Trigger:** `minimumSequenceNumber >= sequenceNumber` for a client op. Mathematically impossible in a correct service. Always a service bug.

### 4. Missing clientId on client op

**File:** `deltaManager.ts:1090`  
**Error:** `"Mismatch in clientId"`

**Trigger:** A non-NoOp client message arrives without a `clientId`. Deli always stamps `clientId` from the connection. If it's missing, the op stream is malformed.

### 5. Non-increasing clientSequenceNumber

**File:** `deltaManager.ts:906`  
**Error:** `"Found two messages with non-increasing clientSequenceNumber for a given client. Likely to be a service issue"`

**Trigger:** Client B's op at seq=20 has `clientSequenceNumber=5` but its previous op already had `clientSequenceNumber=7`. Means service sequenced the same op twice or ops out of client-submission order.  
**Effect:** The `clientSequenceNumber` is used by receiving clients to match acks to pending ops. If it goes backward, pending op reconciliation breaks silently — local and remote state diverge.

### 6. Same sequence number, different payload

**File:** `deltaManager.ts:1046`  
**Error:** `"Found two messages with the same sequenceNumber but different payloads"`

**Trigger:** Two Deli instances both think they own the same document partition (split-brain). Both independently sequence different ops as seq=42. Any client that sees both is permanently corrupted.  
**From code comment:** "some clients could be submitting ops to two different service instances such that the same sequence number is reused for two different ops."

### 7. Incomplete batch (OpBatchIncomplete)

**File:** `packages/runtime/container-runtime/src/inboundBatchAggregator.ts:175`  
**Error:** `"OpBatchIncomplete"`

**Trigger:** Client A's batch was started but before the final op arrives, an op from client B interrupts. Batches must be contiguous and non-interleaved.  
**Why fatal:** Fluid guarantees batch atomicity — all ops in a batch apply together or none do. A partial batch leaves DDS state partially updated.

### 8. Duplicate batch

**File:** `containerRuntime.ts:3152`  
**Error:** `"Duplicate batch - The same batch was sequenced twice"`

**Trigger:** A batch with the same `batchId` appears twice in the op stream.  
**Effect:** `counter.increment(5)` applied twice increments by 10 instead of 5. Non-idempotent ops are permanently wrong.

### 9. Chunk ID mismatch

**File:** `packages/runtime/container-runtime/src/opLifecycle/opSplitter.ts:94`  
**Error:** `"Chunk Id mismatch"`

**Trigger:** Large ops are split into chunks. Chunk 3 arrives but only chunks 1 and 2 are assembled — the service dropped chunk 2 or reordered delivery.  
**Effect:** Reassembled blob is garbled → deserialization fails or produces wrong content.

### 10. Summary metadata mismatch

**File:** `containerRuntime.ts:1117`  
**Error:** `"Summary metadata mismatch"`

**Trigger:** On container load, the sequence number in the runtime summary blob doesn't match the sequence number in the `.protocol` blob. The snapshot was partially written (Scribe crashed mid-write).  
**Effect:** App state (`.app`) and quorum state (`.protocol`) are from different points in time. Every client loading this snapshot is immediately broken.

Configurable: `loadSequenceNumberVerification: "log"` to detect without closing (useful for diagnosis).

### 11. DataStore attach collision

**File:** `channelCollection.ts:522`  
**Error:** `DataCorruptionError` — duplicate DataStore ID in op stream

**Trigger:** Two `attach` ops with the same DataStore ID appear. Causes: service replayed an op, or client reattached an already-attached store.  
**Effect:** Second attach silently overwrites the factory registration — future ops go to the wrong DDS implementation.

### 12. Use of GC-deleted DataStore

**File:** `channelCollection.ts:988`  
**Behavior:** Op is silently dropped (logged as error)

**Two phases:**
1. **Tombstone**: DataStore is marked unreachable — access is logged but allowed temporarily
2. **Sweep/Delete**: DataStore physically removed. Ops to it are silently dropped — changes are **permanently lost** with no error to the sender.

**Trigger:** A client with stashed ops rehydrates; those ops target a DataStore that was deleted during the offline period.

### 13. DDS event listener exception

**File:** `packages/dds/shared-object-base/src/sharedObject.ts:269`  
**Error:** `DataProcessingError` — "SharedObjectEventListenerException"

**Trigger:** Application code in `map.on("valueChanged", ...)` throws an exception.  
**Effect:**
1. `closeWithError(error)` sets the DDS to permanently closed state
2. Every subsequent op or local change re-throws via `verifyNotClosed()`
3. Error propagates to container → container closes

**Why it corrupts:** The DDS's internal state was already mutated when the listener fired. If the listener throws, the app's view is inconsistent with the DDS's internal state — any further read returns wrong data.

### 14. Payload too large

**File:** `opCompressor.ts:94`  
**Error:** `"Payload too large"`

**Trigger:** After lz4 compression, batch still exceeds `maxMessageSize`.  
**Risk:** If undetected, the service Nacks the op. The client's pending queue has ops that can never be sent — local state diverges permanently from all other clients.

### Error propagation chain

```
DDS.processMessagesCore() throws
    ↓
DataProcessingError.wrapIfUnrecognized()
    ↓
DataStoreRuntime re-throws
    ↓
ContainerRuntime.processRemoteMessage() catches
    ↓
container.close(error)
    ↓
"closed" event emitted to application
    ↓
App must reload (if document is still healthy)
or show "document corrupted" if every reload fails at same seq
```

### Who fails — quick reference

| Corruption | Scope |
|---|---|
| Non-sequential seq# | Every client, every reload — permanent |
| MSN moves backward | Only clients that processed past the restored MSN |
| Same seq#, different payload | Every client that sees both copies |
| Incomplete/duplicate batch | Every client |
| Summary metadata mismatch | Every client loading from that summary |
| Chunk ID mismatch | Only the client with bad chunk stream |
| GC deleted node op | Silent drop — no crash, but op lost |
| Event listener exception | Only that client session |
| Payload too large | Only the sending client |

---

## Key File Index

### Server (Routerlicious)

| File | Purpose |
|---|---|
| `server/routerlicious/packages/routerlicious/src/alfred/www.ts` | Alfred entry point |
| `server/routerlicious/packages/routerlicious/src/nexus/www.ts` | Nexus entry point |
| `server/routerlicious/packages/routerlicious/src/deli/index.ts` | Deli lambda runner |
| `server/routerlicious/packages/routerlicious/src/scribe/index.ts` | Scribe lambda runner |
| `server/routerlicious/packages/routerlicious/src/scriptorium/index.ts` | Scriptorium lambda runner |
| `server/routerlicious/packages/lambdas/src/deli/lambda.ts` | Deli sequencer logic |
| `server/routerlicious/packages/lambdas/src/scribe/lambda.ts` | Scribe state machine |
| `server/routerlicious/packages/lambdas/src/scribe/summaryWriter.ts` | Git snapshot writer |
| `server/routerlicious/packages/lambdas/src/scriptorium/lambda.ts` | MongoDB op writer |
| `server/routerlicious/packages/lambdas/src/broadcaster/lambda.ts` | Redis publisher |
| `server/routerlicious/packages/lambdas/src/nexus/index.ts` | WebSocket handler |
| `server/routerlicious/packages/lambdas/src/nexus/connect.ts` | Document connect flow |
| `server/routerlicious/packages/lambdas-driver/src/kafka-service/partition.ts` | Per-partition async queue |
| `server/routerlicious/packages/lambdas-driver/src/kafka-service/partitionManager.ts` | Kafka consumer + rebalance |
| `server/routerlicious/packages/lambdas-driver/src/kafka-service/checkpointManager.ts` | Kafka offset checkpointing |
| `server/routerlicious/packages/routerlicious-base/src/alfred/routes/api/documents.ts` | Document create/get routes |
| `server/routerlicious/packages/routerlicious-base/src/alfred/routes/api/deltas.ts` | Delta fetch route |
| `server/routerlicious/packages/services-telemetry/src/lumberjack.ts` | Telemetry singleton |
| `server/routerlicious/packages/services-telemetry/src/lumber.ts` | Telemetry event object |
| `server/routerlicious/packages/services-telemetry/src/lumberEventNames.ts` | All named events |
| `server/routerlicious/packages/services-utils/src/telemetryContext.ts` | HTTP correlation middleware |
| `server/routerlicious/packages/services-utils/src/asyncContext.ts` | AsyncLocalStorage context |
| `server/routerlicious/packages/services-utils/src/morganLoggerMiddleware.ts` | HTTP request metrics |
| `server/routerlicious/packages/services/src/metricClient.ts` | Telegraf latency client |

### Client (DDSes + Runtime)

| File | Purpose |
|---|---|
| `packages/dds/shared-object-base/src/sharedObject.ts` | `SharedObjectCore` + `SharedObject` base classes |
| `packages/dds/shared-object-base/src/sharedObjectKernel.ts` | `SharedKernel` composition pattern |
| `packages/dds/map/src/mapKernel.ts` | SharedMap op handling |
| `packages/dds/merge-tree/src/mergeTree.ts` | MergeTree CRDT for sequences |
| `packages/runtime/container-runtime/src/containerRuntime.ts` | ContainerRuntime, batching, GC |
| `packages/runtime/container-runtime/src/inboundBatchAggregator.ts` | Batch integrity validation |
| `packages/runtime/container-runtime/src/pendingStateManager.ts` | Pending op queue + resubmit |
| `packages/runtime/container-runtime/src/opLifecycle/opSplitter.ts` | Large op chunking |
| `packages/runtime/container-runtime/src/opLifecycle/opCompressor.ts` | lz4 compression |
| `packages/runtime/container-runtime/src/gc/garbageCollection.ts` | GC tombstone + sweep |
| `packages/runtime/container-runtime/src/channelCollection.ts` | DataStore routing + GC guards |
| `packages/runtime/datastore/src/dataStoreRuntime.ts` | FluidDataStoreRuntime |
| `packages/loader/container-loader/src/deltaManager.ts` | Delta validation + sequence checks |
| `common/lib/protocol-definitions/src/protocol.ts` | `IDocumentMessage`, `ISequencedDocumentMessage` |
| `common/lib/protocol-definitions/src/sockets.ts` | `IConnect`, `IConnected` |

---

## 14. Op Batching, Compression, and Chunking

**File:** `packages/runtime/container-runtime/src/opLifecycle/README.md`

### The 1 MB limit problem

The Fluid relay service enforces a **1 MB payload limit** per message. The default max batch size is `716,800` bytes (lower than 1 MB to account for envelope overhead). Three features solve this: grouped batching, compression, and chunking — all enabled by default.

### FlushMode

Controlled by `IContainerRuntimeOptions.flushMode`:

| Mode | Behaviour |
|---|---|
| `TurnBased` (default) | Accumulates all ops in a single JS turn into one batch, sent at end of turn |
| `Immediate` (deprecated) | Each op sent immediately in its own payload |

`TurnBased` is preferred: fewer round trips, and all ops in a turn are applied atomically by every client.

### Outbound pipeline

```
DDS.submitLocalMessage()
    ↓
ContainerRuntime.submit()
    ↓
outbox.submit()  ← accumulates during JS turn
    ↓ (end of JS turn)
outbox.flush()
    ↓
opGroupingManager.groupBatch()    ← wraps N ops into one "groupedBatch" message
    ↓
opCompressor.compress()           ← lz4 compresses if > minimumBatchSizeInBytes
    ↓ (if still > chunkSizeInBytes after compression)
opSplitter.split()                ← splits compressed blob into chunks
    ↓
send over the wire
```

### Grouped batching

All ops in a batch are wrapped into a single `type: "groupedBatch"` message before sending. This single outer message gets one sequence number from Deli. On the receiving end, the runtime unpacks them and assigns:
- **Same `sequenceNumber`** (the outer message's seq)
- **Different `clientSequenceNumber`** (1, 2, 3… within the batch)

**Important implication:** If a DDS changes state inside an `"op"` event handler (op reentrancy), ops in that same JS turn get different `referenceSequenceNumber` values. The runtime **rebases** these ops to the same `referenceSequenceNumber` before sending. This is mandatory for the grouped batch contract: all ops in a batch must have the same reference sequence number.

### Compression

Only applied to single-message batches (grouped batching must be enabled). The op's contents are replaced with a lz4-compressed buffer. The `compression: "lz4"` field marks it for receivers. The server is completely unaware of compression — it's client-side only.

### Chunking

If the compressed payload still exceeds `chunkSizeInBytes`, it is split into N chunks:

```
Original compressed op (900 bytes) → chunk size 300 bytes

Chunk 1/3: seq=1 (sent alone)
Chunk 2/3: seq=2 (sent alone)
Chunk 3/3: seq=3 (sent as first op in the real batch, triggers reassembly)
```

The receiver accumulates chunks 1..N-1 in memory. When the final chunk arrives, the original op is rebuilt and processed as if it arrived normally.

### Inbound pipeline

```
ContainerRuntime.process()
    ↓
remoteMessageProcessor
    ├── is chunk? → accumulate, return nothing (until final chunk)
    ├── is compressed? → lz4 decompress
    ├── is grouped batch? → ungroup into individual ops
    └── return ops to ContainerRuntime.processCore()
```

### Op reentrancy — the rebase case

```
Alice submits op A at refSeq=10
    → inside "op" handler for op A, Alice submits op B (refSeq=11 at this point)
```

Ops A and B are in the same JS turn (same batch). But they have different `referenceSequenceNumber` (10 and 11). Before sending, the runtime rebases op B to refSeq=10 — the same as op A — so the batch contract holds.

---

## 15. Summarizer Client Election

**Files:** `packages/runtime/container-runtime/src/summary/orderedClientElection.ts`, `summarizerClientElection.ts`, `runningSummarizer.ts`

### Who creates summaries

Summaries can be generated by any **write-mode** client, but in practice they are generated by a dedicated **summarizer client** — a non-interactive client spawned specifically for this purpose. Using a separate client avoids accounting for local pending changes which complicate the summary process.

### Election flow

```
Connected write-mode clients participate in "summary client election"
    ↓
OrderedClientElection selects the "parent summarizer" — typically the OLDEST write client
    (oldest = joined at the lowest sequence number)
    ↓
Parent summarizer spawns a NEW, non-interactive summarizer client
    (separate WebSocket connection, separate ContainerRuntime instance)
    ↓
Summarizer client periodically generates summaries based on heuristics:
    - maxOps: too many ops since last summary
    - idleTime: document has been idle for N ms
    - maxTime: maximum wall-clock time since last summary
    ↓
If parent summarizer disconnects:
    → summarizer client also shuts down
    → election re-runs with new oldest client
```

`OrderedClientElection` (`orderedClientElection.ts:356`) maintains a sorted linked list of clients by join order. On every `ClientJoin`/`ClientLeave` op, it recomputes the elected parent.

### "Last summary" resiliency

If there are too many unsummarized ops and the parent keeps disconnecting, the summarizer client will perform a **"last summary"** before shutting down — even if the parent is gone. This prevents indefinite catchup debt for new joiners.

### Summary heuristics (from `DefaultSummaryConfiguration`)

| Heuristic | Default value | Meaning |
|---|---|---|
| `maxOps` | 1000 | Summarize after 1000 ops since last summary |
| `idleTime` | 5000 ms | Summarize after 5s of document inactivity |
| `maxTime` | 600,000 ms | Summarize at least once every 10 minutes |
| `maxAckWaitTime` | 600,000 ms | Timeout waiting for SummaryAck |

---

## 16. Incremental Summaries

**Files:** `packages/runtime/container-runtime/src/summary/summarizerNode/summarizerNode.ts`

### Problem

Re-serializing every DDS on every summary is expensive. A container with 1000 DDSes shouldn't re-serialize 999 of them if only one changed.

### Solution — `ISummaryHandle`

If an object (DDS, DataStore, GC data) hasn't changed since the last summary, it returns an `ISummaryHandle` — a path string pointing to its subtree in the **previous** snapshot. The storage service resolves the handle when assembling the new snapshot tree.

```
Container summary tree:
├── .gc           → ISummaryHandle (unchanged)
├── DataStore-1/
│   ├── channel-A → ISummaryHandle (unchanged)
│   └── channel-B → ISummaryTree (changed → re-serialized)
└── DataStore-2/  → ISummaryHandle (unchanged)
```

The runtime uploads this tree, and the service populates the handle references from the previous snapshot's SHA. Only the changed subtrees result in new Git blobs.

### How nodes decide to summarize vs handle

Each node tracks `lastSummarySeqNumber`. If `currentSeqNumber === lastSummarySeqNumber` (no ops since last summary), the node returns a handle. If it received any op, it re-summarizes.

**Critical invariant:** The last summary handle must be correct. The service validates it on upload — if the handle doesn't match the previous summary's SHA, the summary is rejected with a `SummaryNack`.

### Incremental summary tracking in the summary tree

The `SummarizerNode` (`summarizerNode.ts`) tracks:
- `referenceSequenceNumber` — the seq number of the last successful summary
- `latestSummary` — the handle path to the latest summary blob for this node

On every `SummaryAck`, all nodes update their `referenceSequenceNumber`. On every op, nodes mark themselves as dirty. At summarize time, dirty nodes re-serialize; clean nodes return handles.

---

## 17. Document-Router — Per-Document Partitioning in Deli

**Files:** `server/routerlicious/packages/lambdas-driver/src/document-router/`

### The problem Deli faces

A single Kafka partition may receive ops from many different documents. Deli needs to sequence each document's ops independently, maintaining per-document state (sequence number, client join/leave tracking, MSN computation). Processing all documents on one lambda would serialize all documents on that partition.

### What document-router does

The `document-router` is itself a `IPartitionLambda`. When Deli starts, it doesn't run directly on Kafka partitions — it uses document-router as an intermediary:

```
Kafka Partition (e.g., partition 3)
    ↓
document-router lambda (one per Kafka partition)
    ↓ routes by documentId
    ├── DocumentPartition for doc-A → Deli lambda instance for doc-A
    ├── DocumentPartition for doc-B → Deli lambda instance for doc-B
    └── DocumentPartition for doc-C → Deli lambda instance for doc-C
```

Each `DocumentPartition` (`documentPartition.ts`) has its own async queue (concurrency=1) and its own Deli lambda instance. Documents on the same Kafka partition are processed **concurrently** in different async queues — only ops for the same document are serialized.

### Checkpoint consolidation

Each `DocumentPartition` reports its own checkpoint offset (the last op it successfully processed). The `ContextManager` (`contextManager.ts`) aggregates these across all documents on the partition and computes the **minimum** — only that minimum is committed to Kafka as the partition checkpoint. This ensures no document's progress is lost when the partition checkpoints.

### Activity timeout

`DocumentPartition` has an `activityTimeout`. If a document receives no ops for `activityTimeout` ms, the partition is closed and its Deli lambda is destroyed, freeing memory. When the document becomes active again, a new lambda is created and initialized from its checkpoint.

### Corrupt document handling

If a document's lambda throws a fatal error (`DocumentPartition.markAsCorrupt()`), that document is marked corrupt (`this.corrupt = true`). Future ops for that document are silently dropped instead of crashing the whole partition — other documents on the same Kafka partition continue normally.

---

## 18. Signals vs Ops

### What signals are

**Signals** are unsequenced, fire-and-forget messages. They do NOT go through:
- Kafka (rawdeltas or deltas)
- Deli (no sequence number assigned)
- MongoDB (not persisted)
- Scribe (not summarized)

They go directly: client → Nexus → all clients in the room (via Socket.io room broadcast).

**Interface:** `ISignalMessage` / `ISentSignalMessage` (`common/lib/protocol-definitions/src/protocol.ts`)

```ts
interface ISignalMessageBase {
    content: unknown;
    type?: string;
    clientConnectionNumber?: number;       // sender's per-connection counter
    referenceSequenceNumber?: number;      // when the signal was created relative to delta stream
    targetClientId?: string;               // optional: unicast to specific client
}
```

### Key differences from ops

| Property | Op | Signal |
|---|---|---|
| Sequenced | Yes (Deli assigns seq#) | No |
| Persisted | Yes (MongoDB, Scribe) | No |
| Replayed for new joiners | Yes (from snapshot + catchup) | No |
| Delivery guarantee | At-least-once | Best-effort |
| Goes through Kafka | Yes | No |
| Latency | Higher (Kafka round trip) | Lower (direct Nexus) |

### What signals are used for

Ephemeral/transient state that doesn't need to survive a refresh:
- Cursor/caret positions
- User presence ("Alice is typing…")
- Collaboration pointers
- Mouse positions in whiteboard apps
- Any UI state that resets on page load

### Unicast signals

With `supportedFeatures['submit_signals_v2'] = true`, a signal can set `targetClientId` to send only to a specific connected client. Used for point-to-point ephemeral communication (e.g., requesting a specific client's cursor position).

### Processing path (server-side)

`configureWebSocketServices()` in `lambdas/src/nexus/index.ts` handles `socket.on("submitSignal", ...)` — it broadcasts directly to the room via Socket.io without touching Kafka or the ordering pipeline at all.

---

## 19. NoOp Messages and MSN Advancement

### What NoOp is

`MessageType.NoOp` (value: `"noop"`) is a sequenced message with no data payload. It is sent to advance the `minimumSequenceNumber` without carrying user data.

From the protocol definition:
> "Empty operation message. Used to send an updated reference sequence number. Relay service is free to coalesce these messages or fully drop them, if another message was used to update MSN to a number equal or higher than referenced sequence number in Noop."

### Why MSN gets stuck

MSN = lowest `referenceSequenceNumber` across all connected clients. If a client goes silent (stops sending ops), its `referenceSequenceNumber` is stuck at whatever it was when it last sent. All other clients' `referenceSequenceNumber` advances, but the silent client anchors the MSN — preventing MergeTree tombstone collection.

### How Deli sends NoOps

**File:** `server/routerlicious/packages/lambdas/src/deli/lambda.ts:1715`

Deli sends a NoOp back to Alfred under two conditions:
1. **Noop heartbeat timeout** (`noopEvent` at line 1756): if no client ops arrive within `noopTimeFrequency` ms, Deli self-generates a NoOp to keep the MSN moving
2. **After processing a client-submitted NoOp**: the client's `referenceSequenceNumber` is updated in Deli's client registry, which may allow MSN to advance

```ts
// deli/lambda.ts:1758
const noOpMessage = this.createOpMessage(MessageType.NoOp);
```

### NoOp sequence number handling

Deli does NOT increment `sequenceNumber` for every NoOp. From `lambda.ts:1037`:
```ts
// We don't increment sequence number for noops sent by client since they will
// be used to update MSN
if (message.operation.type !== MessageType.NoOp) {
    sequenceNumber = this.revSequenceNumber();
}
```

Client NoOps only update the client's reference sequence number in Deli's registry — they don't advance the global sequence counter.

### MSN advancement cascade

When MSN advances (because the slowest client finally catches up and sends an op), every connected client can:
1. Collect MergeTree tombstones below the new MSN
2. Truncate in-memory op buffers below the new MSN
3. Scribe can move forward its protocol state checkpoint

---

## 20. Container Lifecycle — Detached → Attaching → Attached

**Files:** `packages/loader/container-loader/src/container.ts`, `attachment.ts`

### Three states

`AttachState` enum (from `@fluidframework/container-definitions`):

| State | Meaning |
|---|---|
| `Detached` | Container exists only in memory. No connection to service. No document ID yet. |
| `Attaching` | `container.attach()` has been called. First summary is being uploaded. |
| `Attached` | Document exists on the service. Clients can connect and collaborate. |

### Detached state

When a container is created via `Loader.createDetachedContainer()`, it starts `Detached`:
- DDSes can be created and modified locally
- No ops are sent — all changes are buffered in-memory
- No `documentId` exists yet
- `submitLocalMessage()` is a no-op (ops are queued but not sent)

### The `attach()` call

`container.attach(request)` transitions through `Attaching → Attached`:

1. **Generate the initial summary** — the entire container state is serialized to `ISummaryTree` (this is the "attach summary" or "first summary")
2. **Upload to the service** — the summary tree is uploaded to Historian via Alfred's `POST /{tenantId}` endpoint. A `documentId` is returned.
3. **Create the document record** — Alfred writes the document entry to MongoDB
4. **Transition to Attached** — `attachmentData.state = AttachState.Attached` (line 1623)
5. **Flush pending ops** — any ops that were submitted while `Detached` are now sent to the service
6. **Connect to Nexus** — WebSocket connection is established

### `getAttachSummary()` vs `summarize()`

Two summarization entry points:

| Method | When used | Sync/Async |
|---|---|---|
| `getAttachSummary()` | First summary upload during `attach()` | Synchronous |
| `summarize()` | All subsequent summaries | Async (can do incremental) |

`getAttachSummary()` must be synchronous because it runs before any async service interaction. It cannot use incremental summary handles (there's no previous summary to reference).

### Container load path (existing document)

```
Loader.resolve(request)
    ↓
fetch document metadata from Alfred (GET /{tenantId}/{documentId})
    ↓
fetch latest snapshot from Historian
    ↓
ContainerRuntime.loadRuntime()
    ↓ for each DataStore in snapshot:
FluidDataStoreRuntime.load()
    ↓ for each channel in DataStore:
IChannelFactory.load()  ← DDS reads its snapshot blob
attachDeltaHandler()     ← DDS registers IDeltaHandler
    ↓
fetch and apply trailing ops (ops after snapshot seq#)
    ↓
connect to Nexus WebSocket
    ↓
container.attachState = Attached, connected = true
```

### Serializing a detached container

`container.serialize()` (line 1182) can snapshot a `Detached` container to a JSON string. This can be used to:
- Cache the initial state client-side
- Rehydrate via `Loader.rehydrateDetachedContainerFromSnapshot()` (line 400)
- Useful for offline-first patterns where you want to create a container and only attach later

---

## 21. Garbage Collection Lifecycle

**Files:** `packages/runtime/container-runtime/src/gc/`

### What GC tracks

GC tracks which DataStores and attachment blobs are **reachable** from the container root. Reachability is determined by `IFluidHandle` references — if no attached DDS holds a handle to a DataStore, that DataStore is unreachable.

### GC runs

GC runs are triggered as part of the summarization process. During `containerRuntime.summarize()`, GC is asked to collect `IGarbageCollectionData` from every node via `getGCData()`. This builds the **reference graph**: a directed graph where nodes are DataStores/blobs and edges are handle references.

`gcReferenceGraphAlgorithm.ts` runs a reachability sweep from the container root to compute which nodes are referenced.

### Four unreferenced states

**File:** `gc/gcDefinitions.ts:630`, `gc/gcUnreferencedStateTracker.ts`

```
Active → Inactive → TombstoneReady → SweepReady
```

| State | Meaning | Config |
|---|---|---|
| `Active` | Node is reachable — in use | — |
| `Inactive` | No `IFluidHandle` points to this node | `inactiveTimeoutMs` after unreferenced |
| `TombstoneReady` | Has been unreferenced long enough to tombstone | `tombstoneTimeoutMs` after unreferenced |
| `SweepReady` | Tombstone grace period has passed — safe to delete | `tombstoneTimeoutMs + sweepGracePeriodMs` |

The state transitions are tracked by `UnreferencedStateTracker` which uses timers. On every GC run, `refreshUnreferencedStateTracker()` is called to update states based on elapsed time since `unreferencedTimestampMs`.

### Tombstone phase

When a node reaches `TombstoneReady`:
- It is added to the `tombstones[]` list in the GC summary data
- Any access to it logs a `TombstonedDataStoreRequested` telemetry event
- The service responds to requests for tombstoned resources with a 404 + `TombstoneResponseHeaderKey` header
- Clients should treat this as a signal to stop using the handle

Tombstone is a **warning phase** — the data is still accessible but access is flagged.

### Sweep phase (deletion)

When a node reaches `SweepReady`:
- It is added to `deletedNodes` set
- `deleteSweepReadyNodes()` is called on the runtime — the DataStore/blob is physically removed from the summary tree
- Once removed from the summary, the data will not be present in any future snapshot
- Any op targeting the deleted node is silently dropped (see Section 13, GC corruption scenario)

The `deletedNodes` set is persisted across summaries in the GC summary data — it is never cleared, so nodes that have been swept are remembered forever.

### GC reference revival

A tombstoned node can be "revived" — if a new `IFluidHandle` to it is created and stored in an attached DDS, the node transitions back to `Active`. This is why `validParentSummaries` exists in Scribe: a service summary may have been written that the client doesn't know about, and the node references in that summary are still valid.

Once a node is `SweepReady` (past tombstone timeout), revival is no longer possible.

### GC summary data structure

GC state is written into the container summary at `.gc`:
```
.gc/
├── gcState         ← all node GC data (unreferencedTimestampMs per node)
├── tombstones      ← list of tombstoned node paths
└── deletedNodes    ← set of permanently deleted node paths
```

### Node types tracked by GC

| Type | Path format |
|---|---|
| `DataStore` | `/<datastoreId>` |
| `SubDataStore` (channel) | `/<datastoreId>/<channelId>` |
| `Blob` (attachment blob) | `/<blobManagerPath>/<blobId>` |

---

## 22. Auth and Token Flow (Riddler)

**Files:** `server/routerlicious/packages/routerlicious-base/src/riddler/`, `server-services-utils/src/auth.ts`

### What Riddler is

Riddler is the **tenant management and authentication service**. It stores tenant configurations (orderer URL, historian URL, storage settings) and the **tenant secret key** used to verify JWTs.

### Tenant configuration

Each tenant has:
- A unique `tenantId` string
- A secret key (used to sign/verify JWT tokens)
- Storage configuration (orderer URL, historian URL)
- Optional custom storage backend settings

Tenants are stored in MongoDB and cached in Redis (keyed by `tenantId`).

### JWT token structure

Fluid uses standard JWT tokens. The `ITokenClaims` payload contains:
```ts
{
    documentId: string,     // which document
    tenantId: string,       // which tenant
    scopes: ScopeType[],    // what operations are allowed
    user: IUser,            // user identity
    iat: number,            // issued at
    exp: number,            // expiry
}
```

### Scope types (`ScopeType` from `protocol-definitions`)

| Scope | Meaning |
|---|---|
| `doc:read` | Read document (connect read-only, fetch ops/snapshots) |
| `doc:write` | Write to document (submit ops, connect write mode) |
| `summary:write` | Upload summaries (used by summarizer client) |

### Token verification flow

`verifyStorageToken()` middleware (`services-utils/src/auth.ts:349`) is applied to every Alfred and Nexus route:

```
Client request with Authorization: Bearer <jwt>
    ↓
verifyStorageToken() middleware
    ↓
Extract tenantId from JWT claims (without verification)
    ↓
Fetch tenant key from Riddler (or Redis cache)
    GET http://riddler:5000/api/tenants/{tenantId}/key
    ↓
jwt.verify(token, tenantKey)  ← verifies signature
    ↓
Check scopes: does the token have the required ScopeType[]?
    ↓
Check token revocation (if ITokenRevocationManager is configured)
    ↓
Set res.locals.tenantId, documentId for downstream logging
```

Riddler caches tenant keys in Redis with a configurable TTL (`redisForTenantCache`). This avoids hitting Riddler on every request.

### Token revocation

Alfred supports explicit token revocation via `POST /{tenantId}/document/{documentId}/revokeToken`. Revoked token IDs (`jti` claim) are stored in Redis. `verifyStorageToken` checks against this list before accepting a connection.

### Client token flow

```
Application → fetch JWT token from your token endpoint
                (you implement this — Fluid doesn't provide token issuance)
    ↓
Pass JWT to IFluidTokenProvider → driver sends it in connect request
    ↓
Nexus receives IConnect.token
    ↓
verifyStorageToken() validates against Riddler
    ↓
Nexus assigns clientId, sends IConnected back
```

The token endpoint is application-specific — you call Riddler's key API (or implement your own HMAC signing using the tenant secret key) to generate tokens.

### Multi-Tenant Scaling Architecture & Noisy-Neighbor Protection

Fluid Framework / Routerlicious implements a 4-tier scaling architecture per tenant:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ TIER 1: MULTI-CLUSTER TENANT SHARDING & GEO-ROUTING (Riddler)                         │
│ • Tenant A (Enterprise VIP) ──► Dedicated Cluster 1 (Dedicated Kafka, Deli, Mongo)    │
│ • Tenant B & C (Pooled)     ──► Shared Cluster 2 (Multi-tenant shared pool)           │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
┌───────────────────────────────────────────▼────────────────────────────────────────────┐
│ TIER 2: WITHIN-TENANT DOCUMENT SHARDING (Kafka & Deli)                                 │
│ • Tenant A's 100,000 documents are NOT locked to 1 node.                               │
│ • Keyed by murmur2(documentId) % N ──► Dispersed across ALL Kafka partitions & pods   │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
┌───────────────────────────────────────────▼────────────────────────────────────────────┐
│ TIER 3: NOISY NEIGHBOR PROTECTION (Multi-Dimensional Token-Bucket Throttling)          │
│ • connectionsPerTenant  • submitOpsPerTenant  • submitSignalsPerTenant                 │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
┌───────────────────────────────────────────▼────────────────────────────────────────────┐
│ TIER 4: STORAGE TIER SHARDING (MongoDB & GitRest / Blob BYOK)                          │
│ • MongoDB sharded compound key: { tenantId: 1, documentId: 1 }                         │
│ • GitRest / Historian namespace: /repos/{tenantId}/{documentId}                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

#### 1. Tier 1: Multi-Cluster Tenant Sharding (Riddler `ITenantConfig`)
Riddler maintains `orderer.url` and `storage.historianUrl` per tenant (`tenant.ts:15`):
- **VIP Isolation:** Massive enterprise tenants run on dedicated Routerlicious/Kafka/Mongo clusters to eliminate noisy neighbor contention. Standard tenants share a pooled multi-tenant cluster.
- **Data Sovereignty & GDPR:** European tenants route to `eu-central` clusters with EU-based storage; US tenants route to `us-east`.

#### 2. Tier 2: Within-Tenant Document Sharding across Kafka
Within a cluster, Kafka partitions on **`documentId`**, not `tenantId` (`rdkafkaProducer.ts:367`):
$$\text{Partition} = \text{murmur2}(\text{documentId}) \pmod N$$
If a single tenant opens 100,000 documents simultaneously, they are evenly distributed across all 64 or 128 Kafka partitions and processed in parallel across all Deli worker pods.

#### 3. Tier 3: Noisy-Neighbor Protection (Multi-Axis Throttling)
Alfred and Nexus enforce four independent Redis token-bucket rate limiters (`nexus/index.ts`):
- **`connectionsPerTenant`**: Maximum concurrent WebSocket connections per tenant.
- **`submitOps`**: Maximum submitted ops/sec per tenant.
- **`submitSignals`**: Maximum unsequenced signals/sec per tenant.
- **`maxMessageSize`**: Hard limit on op byte length (e.g. 1MB) to prevent large payload attacks.

#### 4. Tier 4: Storage Scaling per Tenant
- **MongoDB Sharding**: The `deltas` collection uses compound shard keys `{ tenantId: 1, documentId: 1 }`, distributing tenant op logs across different MongoDB replica set shards.
- **GitRest / Blob Isolation**: Snapshots are namespace-isolated (`/repos/{tenantId}/{documentId}`) and support Customer-Managed Keys (BYOK) on dedicated cloud blob accounts (Azure Blob / AWS S3).

#### 5. The Single-Document Constraint
While a tenant scales horizontally across unlimited documents, **a single document within that tenant cannot be parallelized across multiple Deli pods**. Strict monotonic total ordering requires one Deli partition to sequence that document. High fan-out loads on a single document are handled by op boxcarring and offloading WebSocket fan-out downstream to the Broadcaster $\rightarrow$ Redis $\rightarrow$ Nexus gateway fleet.

---

## 23. Local Development — Tinylicious and Docker Compose

### Tinylicious — single-process test server

**Package:** `server/routerlicious/packages/tinylicious/`  
**Port:** 7070 (default)

Tinylicious is a minimal Fluid server for local development and testing. It replaces the entire Routerlicious stack with a single Node.js process:

| Routerlicious | Tinylicious |
|---|---|
| Kafka + Zookeeper | In-memory orderer |
| MongoDB | LevelDB (or in-memory with `db.inMemory=true`) |
| Redis | In-memory pub/sub |
| Git/Historian | Local filesystem (`/var/tmp/tinylicious`) |
| 8+ Docker containers | 1 Node.js process |

**Start:**
```sh
cd server/routerlicious
pnpm i && pnpm build
cd packages/tinylicious
pnpm start
```

**Configuration** (via `config.json` or env vars):

| Parameter | Default | Meaning |
|---|---|---|
| `db.inMemory` | `true` | Store ops in memory (not persisted) |
| `db.path` | `/var/tmp/db` | If `db.inMemory=false`, LevelDB path |
| `storage` | `/var/tmp/tinylicious` | Snapshot storage path |
| `PORT` | `7070` | HTTP port |
| `logger__level` | `info` | Log level (set `crit` to silence all output) |

**When to use tinylicious vs Routerlicious:**
- **Tinylicious**: unit tests, local development, trying out DDSes, quick iteration
- **Routerlicious**: integration tests, production, multi-instance scenarios, testing Kafka/MSN behaviour

### Docker Compose — full Routerlicious stack

**File:** `server/routerlicious/docker-compose.yml`

Spins up the complete 14-container stack:

```sh
cd server/routerlicious
docker-compose up
```

**Service ports exposed:**
| Port | Service |
|---|---|
| 3001 | Historian (Git snapshots) |
| 3002 | Nexus (WebSocket) |
| 3003 | Alfred (REST API) |
| 5000 | Riddler (auth) |
| 3022 | Git SSH |
| 9092 | Kafka broker |
| 2181 | Zookeeper |
| 27017 | MongoDB |
| 6379 | Redis |

**Environment-specific config overrides** are done via the `config.json` file at `server/routerlicious/packages/routerlicious/config/config.json`. The docker-compose mounts this into each container.

### Pre-configured tenants (config.json)

Three tenants are pre-configured for local development:

| Tenant | Orderer type | Use |
|---|---|---|
| `fluid` | Kafka (Deli) | Full production path |
| `github` | Kafka (Deli) | GitHub-backed storage |
| `local` | In-memory orderer | Tests that bypass Kafka |

### Fluent Bit log collection

**Files:** `server/routerlicious/fluent-bit.conf`, `server/routerlicious/parse_fluid_log.lua`

The repo includes a Fluent Bit configuration for collecting and forwarding structured logs from all Routerlicious services. The Lua script (`parse_fluid_log.lua`) parses the JSON structured logs emitted by Lumberjack/Winston and extracts fields for forwarding to a log aggregation backend.

---

## 24. Recent Upstream Fluid 2.x Architecture & API Evolution

Key architectural shifts and optimizations introduced in recent upstream commits:

### 1. SharedTree Anchor Navigation (Up to 94% Read & Query Speedup)
- **Problem:** Deeply nested trees (10+ levels) previously suffered path recalculation and object allocation overhead during reads and parent queries.
- **Optimization:** SharedTree now caches field navigations and reuses anchors directly (`#28554`):
  - **Parent/key queries:** 90.9% to 94.6% less elapsed time (down from 13.5µs to 0.7µs).
  - **Object & array reads:** 55.9% to 69.6% less elapsed time (down from 5.3µs to 1.6µs).

### 2. Extrinsic Range Tracking (`TreeArrayNodes` & `FormattedText`)
- **New Alpha API (`#27621`):** `ExtrinsicLocations.createArraySchema` and `FormattedText.createSchemaWithRanges` allow tracking collaborative annotations, comments, and formatting ranges that rebase automatically across peer edits to arrays and formatted text.

### 3. Deprecation of `SharedObject` and `SharedObjectCore`
- **Notice:** Custom subclassing of `SharedObject` / `SharedObjectCore` from `@fluidframework/shared-object-base` is deprecated and will become internal in 3.20.0 (`#28533`, `#28575`).
- **Guidance:** Applications must use built-in DDSes (`SharedTree`, `SharedMap`) or depend solely on the `ISharedObject` interface.

### 4. Promotion of On-Demand Summaries to `@beta`
- **API:** `loadSummarizerContainerAndMakeSummary` in `@fluidframework/container-loader` promoted from `@alpha` to `@beta` (`#28546`), allowing server workflows and tests to force synchronous container summaries on demand.

### 5. Client Compatibility Negotiation (`oldestSupportedClient`)
- **API:** Runtime contexts now expose `context.oldestSupportedClient` replacing `minVersionForCollab` (`#28537`), formalizing wire-protocol negotiation across mixed client versions.

---

## 25. 1-Hour Deep-Dive Technical Interview Script (Director & Distinguished Engineer)

This script is calibrated for an interview panel consisting of a **Director of Engineering** (focusing on system scalability, operational resilience, SLAs, noisy neighbors, and cost efficiency) and a **Distinguished Engineer** (focusing on distributed consensus, race conditions, monotonic invariants, and code-level concurrency guarantees).

### Master 60-Minute Timing & Strategy Blueprint

```
 0:00 ──── 0:08 (8m)   Phase 1: Executive Framing & Why ToB (Not OT, Not Pure CRDT)
 0:08 ──── 0:22 (14m)  Phase 2: Hot-Path Deep Dive: Op Flow, Dual Counters & Deli Concurrency
 0:22 ──── 0:34 (12m)  Phase 3: Soft-State Failover, Checkpointing & At-Least-Once Replay
 0:34 ──── 0:45 (11m)  Phase 4: Dual-Tier Storage: GitRest Snapshots & The 4-Step Catch-Up Flow
 0:45 ──── 0:54 (9m)   Phase 5: Multi-Tenant Scaling, Kafka Partitioning & Noisy Neighbors
 0:54 ──── 1:00 (6m)   Phase 6: The Single-Doc Ceiling & High-Conviction Close
```

---

### Phase 1: Executive Framing & First Principles (0:00 – 0:08)
**Goal:** Establish immediate technical authority. Frame the fundamental computer science problem and defend your architectural choices before they ask.

#### What to Draw on the Whiteboard:
```
       ┌──────────────────────────┐
       │ Distributed Co-Authoring │
       └─────────────┬────────────┘
                     │
     ┌───────────────┼───────────────┐
     ▼               ▼               ▼
[ OT Matrix ]   [ Pure CRDT ]   [ Total Order Broadcast ]
 (Google Docs)    (Automerge)       (Fluid Framework)
  O(N²) pairs     Tombstone debt     ★ Monotonic Counter
  Complex proofs  Heavy payloads     ★ Cheap Snapshots at Seq N
```

#### What to Say:
> "When building real-time collaborative applications at massive scale, every distributed system must solve state convergence under concurrency. Historically, the industry explored three paths:
> 
> 1. **Operational Transformation (OT)**, which requires pairwise transform functions scaling at $O(N^2)$ across operation types—infamously difficult to formally prove and maintain.
> 2. **Pure Peer-to-Peer CRDTs**, which solve decentralized consensus, but incur massive metadata overhead—vector clocks, per-character IDs, and tombstone garbage collection debt that bloats memory over multi-year document lifecycles.
> 3. **Total Order Broadcast (ToB) with Centralized Sequencing**, which is the architectural foundation of Fluid Framework.
> 
> Fluid makes an intentional trade-off: in enterprise collaboration (like Office 365, Teams, and Loop), clients are cloud-connected. By using a lightweight cloud sequencer—**Routerlicious with Kafka and Deli**—we establish an unambiguous, monotonically increasing integer sequence number for all operations. This eliminates OT transformation matrices, eliminates vector clocks, allows trivial GC, and makes snapshots as simple as checkpointing at integer sequence $N$."

- **Director Focus:** Highlight simplicity, smaller payloads, lower cloud egress costs, and predictable SLAs.
- **Distinguished Engineer Trap:** *"Doesn't a centralized sequencer make offline-first impossible?"*  
  **Your Answer:** *"Yes, that is the deliberate trade-off. Fluid is offline-tolerant with optimistic local rebasing, but requires the ordering service to establish final global consensus."*

---

### Phase 2: Hot-Path Op Flow, Dual Counters & Concurrency = 1 (0:08 – 0:22)
**Goal:** Trace the packet journey from keystroke to broadcast, proving you understand in-memory concurrency.

#### What to Draw on the Whiteboard:
```
Client A (Types 'H') ──► Alfred Gateway ──► Kafka: [rawdeltas] (key=documentId)
 (clientSeq=1, refSeq=0)                         │
                                                 ▼
                                            [ Deli Pod ]
                                  Partition.ts: queue(concurrency=1)
                                  DeliLambda: checkOrder() -> Duplicate Drop
                                              ++this.sequenceNumber (Global 51)
                                                 │
                                                 ▼
                                            Kafka: [deltas]
                                           /               \
                       Broadcaster ──► Redis              Scriptorium
                            │                                  │
                            ▼ WebSocket                        ▼
                     Clients (Client B & ACK A)          MongoDB deltas
```

#### What to Say:
> "Let's trace what happens when User A types the letter 'H' in a SharedString DDS:
> 
> 1. **In the Browser:** The character is applied optimistically to the local MergeTree at 0ms latency. The client assigns its local counter `clientSequenceNumber = 1`, captures `referenceSequenceNumber = 0`, and sends an `IDocumentMessage` over WebSocket to Alfred.
> 2. **Gateway to Kafka:** Alfred attaches `clientId: 'client-A'` and publishes the op as a Boxcar to Kafka topic `rawdeltas`, keyed on `documentId`. Kafka's Murmur2 partitioner hashes all ops for that document into the exact same partition.
> 3. **The Sequencing Layer (Deli):** The Deli pod assigned that partition consumes the op.
> 
> Now, here is the critical concurrency guarantee:
> Inside `Partition.ts`, Deli does not execute incoming messages concurrently. It feeds an `async.queue` with hardcoded `concurrency = 1`. Each op must completely finish its async event-loop tick before the next op is dequeued.
> 
> Next, Deli addresses deduplication via `checkOrder()`:
> Deli maintains an in-memory `ClientSequenceNumberManager`. It checks: `is clientSequenceNumber === expected + 1`?
> - If a network retry caused Alfred to forward a duplicate, `clientSequenceNumber < expected` triggers `IncomingMessageOrder.Duplicate`, and Deli **silently drops it** before any global sequence number can be minted.
> - If valid, Deli increments the global counter: `sequenceNumber = ++this.sequenceNumber` (say, advancing from 50 to 51), stamps the Minimum Sequence Number (MSN), and emits an `ISequencedDocumentMessage` to Kafka topic `deltas`.
> 4. **Dual Fan-Out:** Broadcaster consumes Op 51 and publishes to Redis Pub/Sub for WebSocket fan-out to all clients, while Scriptorium consumes in parallel to write durable deltas into MongoDB."

- **Distinguished Engineer Trap:** *"Why can't Kafka's partition guarantee concurrency safety on its own?"*  
  **Your Answer:** *"Kafka only guarantees log ordering at the partition. Once the Node.js process reads a batch, if you use `Promise.all` or `async.queue(..., 10)`, ops for the same document race in the event loop. Routerlicious enforces strict sequential execution via `queue(lambda.handler, 1)` in `Partition.ts`."*

---

### Phase 3: Soft-State Failover, Checkpointing & At-Least-Once Replay (0:22 – 0:34)
**Goal:** Explain disaster recovery. Show that Deli is stateless in storage, but stateful in memory.

#### What to Draw on the Whiteboard:
```
[ Pod 1 Dies ] ──(Missed heartbeat)──► Kafka Group Coordinator Rebalance
                                               │
                                               ▼
[ Pod 2 Takes Over ] ──► 1. MongoDB Checkpoint (read sequenceNumber: 50, logOffset: 120)
                         2. Seek Kafka rawdeltas to Offset 121
                         3. Replay & Resume: sequenceNumber = ++seq (51, 52...)
                         4. Downstream Idempotency: MongoDB E11000 Duplicate Key Ignored
```

#### What to Say:
> "A natural question is: If Deli keeps the global `sequenceNumber` in memory, what happens if the container pod crashes due to an OOM or node termination?
> 
> Deli is an **ephemeral-stateful (soft-state)** service. It has no Persistent Volume Claims (PVCs). Its durability is anchored across MongoDB and Kafka:
> 
> 1. **Checkpoint Anchor:** Deli periodically writes a checkpoint tuple to MongoDB's `documents` collection containing `[sequenceNumber, logOffset, clientRoster]`. Crucially, `sequenceNumber` is paired with the exact Kafka read offset on `rawdeltas`.
> 2. **Crash & Rebalance:** When Pod 1 crashes, Kafka detects missed heartbeats (`session.timeout.ms`) and triggers a cooperative rebalance. Pod 2 claims the orphaned partition.
> 3. **Rehydration:** Pod 2 loads the document checkpoint from MongoDB: it sets its starting `sequenceNumber = 50` and seeks its Kafka consumer on `rawdeltas` to `logOffset + 1` (offset 121).
> 4. **Replay & Monotonicity:** The uncommitted raw ops replay from Kafka. Deli increments from 50 to 51. No sequence numbers are ever skipped.
> 
> What about at-least-once edge cases?
> If Pod 1 had emitted Op 51 to Kafka `deltas` right before dying, Pod 2 will re-emit Op 51. We absorb duplicates idempotently at two layers:
> - **Storage Layer:** Scriptorium writes to MongoDB with a compound unique index `{ tenantId, documentId, sequenceNumber }`. On replay, MongoDB throws `E11000 duplicate key`, which Scriptorium explicitly catches and ignores.
> - **Client Layer:** Clients track `lastProcessedSequenceNumber` and use `DuplicateBatchDetector` to discard any op where `seq <= lastProcessedSeq`."

---

### Phase 4: GitRest Snapshots & The 4-Step New User Join (0:34 – 0:45)
**Goal:** Explain long-term storage, log truncation, and new collaborator bootstrap.

#### What to Draw on the Whiteboard:
```
[ New User Bob Joins (Alice is at Op 1000) ]
  │
  ├─► Step 1: Fetch Git Snapshot ──► GitRest (Commit @ Op 950) ──► Hydrates DDSes
  │
  ├─► Step 2: WebSocket Connect ──► Nexus (Announces refSeq: 950) ──► Broadcasts ClientJoin
  │
  ├─► Step 3: Catch-Up Deltas   ──► Alfred ──► MongoDB (Replays Ops 951..1000)
  │
  └─► Step 4: Live WebSocket    ──► Nexus (Receives Op 1001+ live)
```

#### What to Say:
> "Individual ops are NEVER written to Git. Committing every keystroke would destroy Git object performance. Instead, Fluid operates a **dual-tier storage strategy**:
> - MongoDB `deltas` stores the granular, short-term append-only log.
> - GitRest stores periodic, hierarchical snapshot trees.
> 
> Every ~100 ops, an elected summarizer client creates an `ISummaryTree` and submits a `summarize` op. Scribe validates it against the quorum, appends protocol metadata (`.protocol`, `.logTail`), and coordinates with Historian and **GitRest** to commit Git blobs and trees. Unmodified DDSes are not re-uploaded—they reuse their existing Git SHA handles.
> 
> When a new user, Bob, joins Alice's session where Alice is at Op 1,000 and the latest Git summary is at Op 950:
> 1. **Step 1 — Base Snapshot:** Bob queries Alfred for the latest summary. GitRest returns the flat snapshot tree at Commit SHA representing Op 950. Bob’s browser hydrates all DDSes to state 950.
> 2. **Step 2 — Handshake:** Bob opens a WebSocket to Nexus with `referenceSequenceNumber = 950`. Nexus adds Bob to the room and emits a `ClientJoin` op.
> 3. **Step 3 — Delta Catch-Up:** Bob calls Alfred's REST API `GET /deltas?from=951&to=1000`. Alfred fetches these 50 ops from MongoDB `deltas`. Bob's runtime plays them forward, bridging the gap from 950 to 1000.
> 4. **Step 4 — Live Transition:** Bob seamlessly switches to live WebSocket streaming for Op 1001 onwards."

- **Distinguished Engineer Trap:** *"Why use Git objects instead of a traditional SQL/NoSQL snapshot blob?"*  
  **Your Answer:** *"Content-addressable storage. Unchanged subtrees between summaries share the same SHA-1/SHA-256 handle. A 100MB document where only one paragraph changed requires uploading only a tiny blob and re-linking existing tree handles, giving us massive storage deduplication."*

---

### Phase 5: Multi-Tenant Scaling, Partitioning & Noisy Neighbors (0:45 – 0:54)
**Goal:** Address cluster scaling, noisy neighbors, and enterprise multi-tenancy.

#### What to Draw on the Whiteboard:
```
[ Tenant Provisioning: Riddler ] ──► ordererUrl & historianUrl
         │
         ├──► Tenant A (VIP Bank) ──► Dedicated Cluster 1 (Kafka 1, Deli 1, Mongo 1)
         └──► Tenant B, C (Pooled) ──► Shared Cluster 2
                                            │
                                            ▼
           Within Cluster: murmur2(documentId) % N Partitions
           (Tenant B's 50,000 docs parallelize across ALL 64 Deli pods)
```

#### What to Say:
> "How does Routerlicious scale across enterprise tenants? It uses a 4-tier model:
> 
> 1. **Macro Sharding via Riddler:** Riddler provisions tenants with dedicated `orderer.url` and `storage.historianUrl` endpoints. We isolate large enterprise VIP tenants onto dedicated physical clusters, satisfying strict SLAs and GDPR data residency, while smaller tenants share a pooled cluster.
> 2. **Micro Partitioning within a Tenant:** A single tenant with 50,000 active documents is NEVER constrained to one pod. Because Kafka keys on `documentId`, ops are uniformly distributed across all topic partitions via Murmur2 hash, utilizing every Deli pod in the fleet.
> 3. **Noisy Neighbor Defense:** Shared clusters enforce multi-axis Redis token-bucket throttling: `connectionsPerTenant`, `submitOps`, and `submitSignals`. A rogue tenant generating excessive traffic gets throttled at the gateway (HTTP 429) without degrading neighboring tenants.
> 4. **Storage Sharding:** MongoDB `deltas` uses compound shard keys `{ tenantId: 1, documentId: 1 }`, and GitRest repositories are namespace-isolated (`/repos/{tenantId}/{documentId}`) with support for Customer-Managed Keys (BYOK)."

---

### Phase 6: The Single-Doc Ceiling & High-Conviction Close (0:54 – 1:00)
**Goal:** Address the ultimate scaling limit honestly, show deep architectural wisdom, and finish with conviction.

#### What to Say:
> "Finally, let’s address the fundamental scaling boundary of this architecture: **The Single-Document Ceiling**.
> 
> If an interviewer asks: 'Can we scale Deli by adding 10 pods to process one single document?'
> The answer is **No**. In Fluid, total strict ordering requires a single monotonic sequencer. A single document's sequencing cannot be sharded across multiple nodes without distributed consensus, which would destroy sub-millisecond latency.
> 
> Instead, Routerlicious scales single-document collaboration by:
> 1. **Boxcarring:** Clients batch ops into arrays, letting Deli sequence hundreds of operations in a single event loop tick.
> 2. **Fan-out Offloading:** Deli only writes to Kafka `deltas`. The massive broadcast burden (say, 50,000 WebSockets listening to one document) is offloaded entirely to the Broadcaster, Redis Pub/Sub, and the horizontal Nexus gateway fleet.
> 
> To summarize the architecture in one sentence:  
> **Fluid Framework achieves extreme real-time collaborative speed by combining Total Order Broadcast over Kafka for monotonic ordering, event sourcing over MongoDB for op durability, and content-addressable Git trees for incremental snapshotting.**"

---

### Panel Cheat Sheet: Anticipated Questions & Winning Answers

| Interviewer | Question They Will Ask | Winning 10-Second Answer |
| :--- | :--- | :--- |
| **Director** | *"How do we manage infrastructure cost if documents stay open for weeks?"* | *"Deli's `DocumentLambda` runs an `inactivityCheck` timer. Idle documents (>10 min) checkpoint to Mongo and are evicted from RAM. They reload on demand on the next op, keeping memory footprint minimal."* |
| **Distinguished Eng** | *"If a Kafka rebalance happens while Deli is processing, how do you prevent split-brain?"* | *"Routerlicious uses `cooperative-sticky` assignor. On `rebalancing`, `PartitionManager` marks `isRebalancing = true`, calls `partition.drain()` to finish in-flight ops, and closes existing partitions before the new partition assignment takes effect."* |
| **Director** | *"How do we protect against DDoS or bad client code flooding the server?"* | *"Four independent token-bucket throttlers at Nexus/Alfred gateway reject oversized payloads, rate-limit socket handshakes, and throttle op/signal submission rates before messages ever touch Kafka."* |
| **Distinguished Eng** | *"Why doesn't the client just replay from MongoDB instead of fetching Git snapshots?"* | *"Log replay is $O(\text{total ops})$. For a document with 500,000 historical edits, replaying from MongoDB would take minutes and consume gigabytes of client memory. Git snapshots provide an $O(1)$ materialized view."* |

---

## Updated Key File Index

### New files added in sections 14–23

| File | Purpose |
|---|---|
| `packages/runtime/container-runtime/src/opLifecycle/README.md` | Batching, compression, chunking deep-dive |
| `packages/runtime/container-runtime/src/opLifecycle/outbox.ts` | Op accumulation and flush |
| `packages/runtime/container-runtime/src/opLifecycle/opGroupingManager.ts` | Grouped batch wrapping |
| `packages/runtime/container-runtime/src/opLifecycle/remoteMessageProcessor.ts` | Inbound chunk/decompress/ungroup pipeline |
| `packages/runtime/container-runtime/src/summary/README.md` | Summary architecture overview |
| `packages/runtime/container-runtime/src/summary/orderedClientElection.ts` | Summarizer client election |
| `packages/runtime/container-runtime/src/summary/summarizerNode/summarizerNode.ts` | Incremental summary tracking |
| `packages/runtime/container-runtime/src/gc/gcDefinitions.ts` | GC types, states, config interfaces |
| `packages/runtime/container-runtime/src/gc/gcUnreferencedStateTracker.ts` | Per-node state machine (Active→Inactive→Tombstone→Sweep) |
| `packages/runtime/container-runtime/src/gc/gcReferenceGraphAlgorithm.ts` | Reference graph reachability sweep |
| `packages/loader/container-loader/src/container.ts` | Container attach/load lifecycle |
| `packages/loader/container-loader/src/attachment.ts` | AttachState transitions |
| `server/routerlicious/packages/lambdas-driver/src/document-router/documentPartition.ts` | Per-document lambda queue |
| `server/routerlicious/packages/lambdas-driver/src/document-router/contextManager.ts` | Cross-document checkpoint consolidation |
| `server/routerlicious/packages/lambdas/src/deli/lambda.ts` | NoOp sending (line 1715, 1756) |
| `server/routerlicious/packages/routerlicious-base/src/riddler/tenantManager.ts` | Tenant key fetch + cache |
| `server/routerlicious/packages/services-utils/src/auth.ts` | JWT verification middleware |
| `server/routerlicious/packages/tinylicious/README.md` | Tinylicious config and usage |
| `server/routerlicious/docker-compose.yml` | Full stack container definitions |
| `common/lib/protocol-definitions/src/protocol.ts` | `MessageType.NoOp`, `ISignalMessage` |

---

*Generated: 2026-05-15. Repository branch: main. Updated with sections 14–23.*
