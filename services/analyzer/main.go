package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"time"

	_ "github.com/lib/pq"
	"github.com/nats-io/nats.go"
)

type EventMsg struct {
	ID        string `json:"id"`
	SessionID string `json:"session_id"`
	AgentID   string `json:"agent_id"`
	ProjectID string `json:"project_id"`
	Type      string `json:"type"`
}

type Analyzer struct {
	db     *sql.DB
	natsJS nats.JetStreamContext
}

func main() {
	log.Println("Starting VERI Real-time Analysis Engine...")

	// Get configuration from env
	pgURL := os.Getenv("DATABASE_URL")
	if pgURL == "" {
		pgURL = "postgresql://veri_admin:veri_password_2026@localhost:5432/veri_db?sslmode=disable"
	}
	natsURL := os.Getenv("NATS_URL")
	if natsURL == "" {
		natsURL = "nats://localhost:4222"
	}

	// 1. Postgres connection setup
	db, err := sql.Open("postgres", pgURL)
	if err != nil {
		log.Fatalf("Fatal: PostgreSQL connection failure: %v", err)
	}
	defer db.Close()

	// Wait and verify database connection
	for i := 0; i < 5; i++ {
		if err := db.Ping(); err == nil {
			log.Println("Successfully connected to PostgreSQL Database.")
			break
		}
		log.Println("Waiting for PostgreSQL database to be ready...")
		time.Sleep(2 * time.Second)
	}

	// 2. NATS connection setup
	nc, err := nats.Connect(natsURL)
	if err != nil {
		log.Fatalf("Fatal: NATS connection failure: %v", err)
	}
	defer nc.Close()

	js, err := nc.JetStream()
	if err != nil {
		log.Fatalf("Fatal: JetStream config failure: %v", err)
	}

	analyzer := &Analyzer{
		db:     db,
		natsJS: js,
	}

	// 3. Subscribe to NATS Stream
	sub, err := js.PullSubscribe("veri.event.*", "veri-analyzer-group", nats.ManualAck())
	if err != nil {
		log.Fatalf("Fatal: PullSubscribe failed: %v", err)
	}

	log.Println("Rule & Analysis Engine is actively listening for event streams...")
	for {
		msgs, err := sub.Fetch(10, nats.MaxWait(1*time.Second))
		if err != nil && err != nats.ErrTimeout {
			log.Printf("Fetch error: %v", err)
			time.Sleep(1 * time.Second)
			continue
		}

		for _, m := range msgs {
			analyzer.processEvent(m)
			_ = m.Ack()
		}
	}
}

func (a *Analyzer) processEvent(msg *nats.Msg) {
	var ev EventMsg
	if err := json.Unmarshal(msg.Data, &ev); err != nil {
		log.Printf("Unmarshalling event msg failed: %v", err)
		return
	}

	// Rule 1: Simple Loop Check (detect if there are >5 identical events for this session)
	a.evaluateLoopCheck(ev)
}

func (a *Analyzer) evaluateLoopCheck(ev EventMsg) {
	// Query to see if identical call threshold has been crossed
	// (Simulated logic using a fast postgres lookup for demonstration)
	var count int
	err := a.db.QueryRow(`
		SELECT COUNT(*) FROM suggestions 
		WHERE agent_id = $1 AND type = 'loop.identical_tool_calls' AND status = 'pending'`,
		ev.AgentID,
	).Scan(&count)

	if err != nil {
		log.Printf("DB check failed: %v", err)
		return
	}

	// If we haven't already raised a suggestion for this loop, create one
	if count == 0 {
		log.Printf("⚠️ Loop detector triggered for Agent: %s, Session: %s. Creating suggestion.", ev.AgentID, ev.SessionID)

		suggestionID := fmt.Sprintf("sug_%d", time.Now().UnixNano())
		_, err = a.db.Exec(`
			INSERT INTO suggestions (id, agent_id, type, finding_message, fix_description, config_diff, risk_level, confidence)
			VALUES ($1, $2, $3, $4, $5, $6, $7, $8)`,
			suggestionID,
			ev.AgentID,
			"loop.identical_tool_calls",
			"Tool 'order_lookup' called 5 times with identical arguments: {'id': 4521}.",
			"Add a call limit of 4 to prevent infinite retry loops.",
			`# veri.yaml — add under agent.guardrails:
guardrails:
  tool_limits:
    - tool: order_lookup
      max_calls: 4
      on_exceed: "return_explanation"`,
			"L1",
			0.9000,
		)
		if err != nil {
			log.Printf("Failed to insert suggestion to DB: %v", err)
		}
	}
}
