CUSTOM_CSS = """
<style>
:root {
  --brand: #2563eb;
  --brand-2: #06b6d4;
  --ink: #172033;
  --muted: #667085;
  --line: #d7deea;
  --soft: #f6f8fb;
  --ok: #16803c;
  --warn: #b7791f;
  --danger: #c33149;
}

.stApp {
  background:
    radial-gradient(circle at 10% 0%, rgba(37, 99, 235, 0.12), transparent 32rem),
    linear-gradient(180deg, #f7fbff 0%, #eef3f8 100%);
  color: var(--ink);
}

[data-testid="stSidebar"] {
  background: rgba(255, 255, 255, 0.86);
  border-right: 1px solid rgba(215, 222, 234, 0.9);
}

.hero {
  background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 56%, #06b6d4 100%);
  border-radius: 8px;
  color: white;
  margin-bottom: 1rem;
  padding: 1.2rem 1.4rem;
}

.hero h1 {
  font-size: 1.75rem;
  margin: 0 0 .35rem;
}

.hero p {
  margin: 0;
  opacity: .92;
}

.metric-row {
  display: grid;
  gap: .75rem;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-bottom: 1rem;
}

.metric-card, .doc-card, .source-card {
  background: rgba(255, 255, 255, .92);
  border: 1px solid var(--line);
  border-radius: 8px;
  box-shadow: 0 10px 26px rgba(15, 23, 42, .06);
}

.metric-card {
  padding: .9rem 1rem;
}

.metric-card strong {
  color: var(--brand);
  display: block;
  font-size: 1.45rem;
}

.metric-card span {
  color: var(--muted);
  font-size: .86rem;
}

.doc-card {
  margin: .55rem 0;
  padding: .75rem;
}

.doc-title {
  font-weight: 800;
  margin-bottom: .25rem;
}

.doc-meta {
  color: var(--muted);
  font-size: .82rem;
}

.status {
  border-radius: 999px;
  display: inline-block;
  font-size: .72rem;
  font-weight: 800;
  margin-top: .45rem;
  padding: .18rem .5rem;
}

.status-ready { background: #dcfce7; color: #166534; }
.status-processing { background: #fef3c7; color: #92400e; }
.status-failed { background: #fee2e2; color: #991b1b; }

.chat {
  display: flex;
  margin: .65rem 0;
}

.chat-user { justify-content: flex-end; }
.chat-assistant { justify-content: flex-start; }

.bubble {
  border-radius: 8px;
  line-height: 1.72;
  max-width: 82%;
  padding: .85rem 1rem;
}

.bubble-user {
  background: var(--brand);
  color: white;
}

.bubble-assistant {
  background: rgba(255, 255, 255, .96);
  border: 1px solid var(--line);
  color: var(--ink);
}

.source-card {
  margin: .55rem 0;
  padding: .8rem .9rem;
}

.source-card h4 {
  font-size: .95rem;
  margin: 0 0 .4rem;
}

.source-card p {
  color: var(--muted);
  font-size: .88rem;
  line-height: 1.65;
  margin: 0;
}

.cursor::after {
  animation: blink 1s infinite;
  content: "▋";
}

@keyframes blink {
  0%, 45% { opacity: 1; }
  46%, 100% { opacity: 0; }
}

@media (max-width: 760px) {
  .metric-row {
    grid-template-columns: 1fr;
  }
  .bubble {
    max-width: 100%;
  }
}
</style>
"""
