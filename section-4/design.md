1. Architecture

The system follows an Event-Driven Microservices architecture to ensure high availability and loose coupling. Invoices are ingested via an Ingestion Layer (S3 buckets or Email Listeners) and placed into a Message Queue (e.g., RabbitMQ or Amazon SQS). Worker Services then consume these messages to perform OCR and LLM-based extraction, storing the results in a Relational Database (PostgreSQL) while exposing them through a REST API (FastAPI) for downstream consumption.
2. Reliability

To handle the 5% failure rate, I would implement a Human-in-the-Loop (HITL) workflow triggered by automated Confidence Scoring. If the LLM extraction fails Pydantic validation (e.g., math mismatches) or returns a low confidence score, the record is flagged and routed to a Verification Dashboard. This allows human reviewers to manually correct anomalies without halting the entire pipeline, ensuring that only 100% validated data reaches the final database.
3. Cost

At 500 invoices per day, the daily cost is $15.00 ($0.03 * 500). To reduce costs by 50% without sacrificing accuracy, I would implement LLM Cascading, using a cheaper model (like GPT-4o-mini or Claude Haiku) for standard, high-confidence templates and only "escalating" to a premium model (like GPT-4o or Claude Opus) for complex or failed extractions. Additionally, implementing a Semantic Cache (e.g., Redis) can store extraction templates for recurring vendors, avoiding redundant LLM calls for identical document structures.
4. Scaling

Scaling to 10,000 invoices/day requires transitioning to a Horizontally Scalable environment using Kubernetes (K8s) to auto-scale worker nodes based on queue depth. I would introduce Database Partitioning or Read Replicas to handle increased I/O load and implement strict Rate Limiting to manage LLM API quotas. Furthermore, moving the initial OCR/Layout analysis to a specialized local service (like LayoutLM) would reduce the token payload sent to the LLM, significantly improving both throughput and latency.