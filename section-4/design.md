## 1. Architecture

The architecture consists of an Ingestion Layer (Email/API gateways) that feeds raw documents into an Object Store (like AWS S3) and triggers an event queue (e.g., RabbitMQ or AWS SQS). A set of asynchronous worker nodes picks up these events, performs OCR for images/PDFs, and passes the extracted text to the LLM Extraction module. The resulting JSON is then evaluated by a Rules Engine (using Pydantic); strictly valid records are saved directly to a relational database (e.g., PostgreSQL), while failures are routed to a separate queue. Finally, a FastAPI backend exposes the stored, validated data to downstream systems and internal dashboards.
```text
======================= DATA PIPELINE (ETL) =======================
[Ingestion: Emails, PDFs, API]
             |
             v
    [Object Store (S3)] ---> (Event) ---> [Message Queue (SQS)]
                                                  |
                                                  v
                                       [Async Workers (Celery)]
                                       1. Document OCR
                                       2. LLM Data Extraction
                                                  |
                                                  v
                                      [Rules Engine (Pydantic)]
                                       /                     \
                                 (Valid)                 (Invalid)
                                   /                         \
                                  v                           v
                        [ DATABASE / DB STATE ]         [Review Queue]
                                  ^                           |
                                  |                           v
======================== API & AI AGENT ===========================
                                  +------------------[HITL Dashboard]
                                  |
                   +--------------+--------------+
                   | FastAPI Backend (/query)    |
                   +--------------+--------------+
                                  |
                     [User Query + thread_id]
                                  |
                                  v
                       +----------------------+
       +-------------> |   Node: "chatbot"    | <-------------+
       |               | (LLM bound to tools) |               |
       |               +----------------------+               |
[MemorySaver]            |                  |                 |
(Checkpointer)           | END       (tools_condition)        |
       |                 |                  |                 |
       +-----------------+                  v                 |
                         |       +----------------------+     |
                         |       |    Node: "tools"     | ----+
                         |       | (ToolNode execution) |
                         |       +----------------------+
                         |                  |
                         v                  v
                 [Final Response]     (Reads from DB)

```
                 
## 2. Reliability

To prevent the 5% failure rate from blocking the pipeline, the extraction and validation steps must run asynchronously using a message broker and background workers (e.g., Celery). When the validation engine detects anomalies, hallucinated fields, or mathematical mismatches, the system routes the document and its raw output to a dedicated "Review Queue" rather than halting the process. A Human-In-The-Loop (HITL) dashboard then allows operators to view the original document side-by-side with the flagged data, manually correct the errors, and commit the finalized record to the database.

## 3. Cost

At 500 invoices per day, the daily cost is $15.00 ($0.03 * 500). To reduce costs by 50% without sacrificing accuracy, I would implement LLM Cascading, using a cheaper model (like GPT-4o-mini or Claude Haiku) for standard, high-confidence templates and only "escalating" to a premium model (like GPT-4o or Claude Opus) for complex or failed extractions. Additionally, implementing a Semantic Cache (e.g., Redis) can store extraction templates for recurring vendors, avoiding redundant LLM calls for identical document structures.

## 4. Scaling

Scaling to 10,000 invoices/day requires transitioning to a Horizontally Scalable environment using Kubernetes (K8s) to auto-scale worker nodes based on queue depth. I would introduce Database Partitioning or Read Replicas to handle increased I/O load and implement strict Rate Limiting to manage LLM API quotas. Furthermore, moving the initial OCR/Layout analysis to a specialized local service (like LayoutLM) would reduce the token payload sent to the LLM, significantly improving both throughput and latency.