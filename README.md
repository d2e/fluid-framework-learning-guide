# Fluid Framework & Routerlicious Architecture Guide

An interactive, deep-dive architectural learning portal and visual reference for **Fluid Framework** and its **Routerlicious** backend ordering service.

---

## Included Documents

- **[`index.html`](index.html) / [`learning.html`](learning.html)**: The master developer learning guide and interactive reference portal (~420 KB standalone offline document with search, category filters, and architectural diagrams).
- **[`deli-replica-design.html`](deli-replica-design.html)**: Standalone interactive visual dashboard covering Deli container replica sharding, Kafka partition topology, and pod failover lifecycles.
- **[`Routerlicious-HLD.excalidraw`](Routerlicious-HLD.excalidraw)**: High-Level Architecture (HLD) diagram covering Client/App Layer, Routerlicious Service Plane (Alfred, Deli, Scribe, Scriptorium, Redis, Kafka), and Durable Storage & History (MongoDB, GitRest, Historian).

---

## Topics Covered

1. **Repository Layout & Architecture Overview:** Packages, runtime definitions, DDS hierarchy, FF-OCE on-call agent tooling.
2. **Routerlicious Backend:** Gateway (Alfred/Nexus), Ordering (Deli), Snapshots (Scribe/Historian/GitRest), and Persistence (Scriptorium/MongoDB).
3. **Op Flow & Total Order Broadcast (ToB):** End-to-end op lifecycle from keystroke to screen; why ToB instead of Operational Transform (OT) or pure CRDTs.
4. **Sequence Numbers & Deduplication:** `clientSequenceNumber` (local tab counter) vs `sequenceNumber` (global lifetime counter); in-memory deduplication via `checkOrder()`.
5. **Deli Container Scaling & Backpressure:** Kafka Consumer Group allocation ($R=P, R<P, R>P$), `Partition.ts` in-memory `queue(concurrency=1)`, document router eviction (`inactivityCheck`).
6. **Crash Recovery & Soft-State:** Dual-checkpoint mechanism (MongoDB `documents.deli` + Kafka seek offset), downstream idempotent duplicate absorption.
7. **Storage Tier Architecture:** Complete MongoDB collection breakdown (`deltas`, `documents`, `checkpoints`, `tenants`, `reservations`, `nodes`, `rawdeltas`).
8. **GitRest Snapshot Pipeline:** Client summarizer election, `ISummaryTree` generation, Git blobs/trees/commits, and new user catch-up flow (Git snapshot + Mongo deltas).
9. **Multi-Tenant Scaling:** Riddler tenant sharding across clusters, within-tenant partition distribution, and 4-axis token-bucket rate limiting.
10. **Recent Fluid 2.x Evolutions:** SharedTree Anchor Navigation 90%+ read optimizations, `ExtrinsicLocations` range tracking, and `SharedObjectCore` deprecation.
11. **Boxcar Messaging & Batching:** `IBoxcarMessage` envelope, micro-batching via Node.js event-loop `setImmediate`, Kafka offset optimization, and MongoDB bulk inserts.
12. **1-Hour Deep-Dive Technical Interview Script (Director & Distinguished Engineer):** 60-minute phased blueprint, whiteboard diagrams, verbatim spoken scripts, distributed consensus trap answers, and panel Q&A cheat sheet.

---

## How to View
Simply open `index.html` or `learning.html` in any web browser. No web server or node runtime is required.
