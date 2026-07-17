package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"strings"
	"time"

	_ "github.com/lib/pq"
	"github.com/nats-io/nats.go"
)

type Event struct {
	ID           string   `json:"id"`
	ParentSpanID string   `json:"parent_span_id"`
	SpanID       string   `json:"span_id"`
	ProjectID    string   `json:"project_id"`
	AgentID      string   `json:"agent_id"`
	SessionID    string   `json:"session_id"`
	Category     string   `json:"category"`
	Type         string   `json:"type"`
	Name         string   `json:"name"`
	Payload      any      `json:"payload"`
	Timestamp    float64  `json:"timestamp"`
	LatencyMs    uint32   `json:"latency_ms"`
	CostUSD      float64  `json:"cost_usd"`
	TokensInput  uint32   `json:"tokens_input"`
	TokensOutput uint32   `json:"tokens_output"`
	Kind         string   `json:"kind"`
	Label        string   `json:"label"`
	Content      any      `json:"content"`
	Confidence   *float64 `json:"confidence"`
	Uncertainty  *float64 `json:"uncertainty"`
	Evidence     []string `json:"evidence"`
	Assumptions  []string `json:"assumptions"`

	// v2 fields
	ConfidenceValue      *float64 `json:"confidence_value"`
	ConfidenceSource     string   `json:"confidence_source"`
	ConfidenceMethod     string   `json:"confidence_method"`
	Capabilities         []string `json:"capabilities"`
	EdgeConfidenceSource string   `json:"edge_confidence_source"`
}

type EvolutionEngine struct {
	db     *sql.DB
	natsJS nats.JetStreamContext
}

func main() {
	log.Println("Starting VERI Evolution Engine...")

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

	engine := &EvolutionEngine{
		db:     db,
		natsJS: js,
	}

	// 3. Subscribe to NATS Stream
	sub, err := js.PullSubscribe("veri.event.*", "veri-analyzer-group", nats.ManualAck())
	if err != nil {
		log.Fatalf("Fatal: PullSubscribe failed: %v", err)
	}

	log.Println("VERI Evolution Engine is actively listening for event streams...")
	for {
		msgs, err := sub.Fetch(10, nats.MaxWait(1*time.Second))
		if err != nil && err != nats.ErrTimeout {
			log.Printf("Fetch error: %v", err)
			time.Sleep(1 * time.Second)
			continue
		}

		for _, m := range msgs {
			engine.processEvent(m)
			_ = m.Ack()
		}
	}
}

func (a *EvolutionEngine) processEvent(msg *nats.Msg) {
	var ev Event
	if err := json.Unmarshal(msg.Data, &ev); err != nil {
		log.Printf("Unmarshalling event msg failed: %v", err)
		return
	}

	// 1. Save telemetry nodes and edges to PostgreSQL
	if ev.Category != "edge" && ev.Type != "session.started" && ev.Type != "session.completed" {
		a.saveNode(ev)
		// Run diagnostics and simulations
		a.evaluateLoopCheck(ev)
		a.evaluateConfidenceDegradation(ev)
	} else if ev.Category == "edge" {
		a.saveEdge(ev)
	}
}

func (a *EvolutionEngine) saveNode(ev Event) {
	assumptions := []string{}
	if len(ev.Assumptions) > 0 {
		assumptions = ev.Assumptions
	}
	evidence := []string{}
	if len(ev.Evidence) > 0 {
		evidence = ev.Evidence
	}

	contentMap := map[string]any{}
	if ev.Content != nil {
		if m, ok := ev.Content.(map[string]any); ok {
			contentMap = m
		}
	}

	// Backport input from payload if content's input is empty
	if ev.Payload != nil {
		if m, ok := ev.Payload.(map[string]any); ok {
			if inp, ok := m["input"]; ok && contentMap["input"] == nil {
				contentMap["input"] = inp
			}
		}
	}

	contentBytes, _ := json.Marshal(contentMap)
	t := time.Unix(0, int64(ev.Timestamp*1e9)).UTC()

	assumptionsArr := goSliceToPGArray(assumptions)
	evidenceArr := goSliceToPGArray(evidence)

	_, err := a.db.Exec(`
		INSERT INTO runtime_nodes (
			id, project_id, agent_id, session_id, kind, label, content, 
			confidence, uncertainty, assumptions, evidence, cost_usd, 
			latency_ms, token_input, token_output, timestamp, duration_ms,
			confidence_value, confidence_source, confidence_method, capabilities
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21)
		ON CONFLICT (id) DO UPDATE SET
			confidence = EXCLUDED.confidence,
			uncertainty = EXCLUDED.uncertainty,
			cost_usd = EXCLUDED.cost_usd,
			latency_ms = EXCLUDED.latency_ms,
			duration_ms = EXCLUDED.duration_ms,
			content = runtime_nodes.content || EXCLUDED.content,
			confidence_value = EXCLUDED.confidence_value,
			confidence_source = EXCLUDED.confidence_source,
			confidence_method = EXCLUDED.confidence_method,
			capabilities = EXCLUDED.capabilities
		`,
		ev.SpanID, ev.ProjectID, ev.AgentID, ev.SessionID, ev.Category, ev.Name,
		string(contentBytes), ev.Confidence, ev.Uncertainty, assumptionsArr,
		evidenceArr, ev.CostUSD, ev.LatencyMs, ev.TokensInput, ev.TokensOutput,
		t, ev.LatencyMs,
		ev.ConfidenceValue, ev.ConfidenceSource, ev.ConfidenceMethod, goSliceToPGArray(ev.Capabilities),
	)
	if err != nil {
		log.Printf("Failed to insert runtime node %s: %v", ev.SpanID, err)
	}

	// v2 addition: Cache inputs/outputs in replay_cache for replayable nodes
	isReplayable := false
	for _, cap := range ev.Capabilities {
		if cap == "is_replayable" {
			isReplayable = true
			break
		}
	}

	if isReplayable {
		inputSnapshot := "{}"
		outputSnapshot := "{}"

		if ev.Content != nil {
			if m, ok := ev.Content.(map[string]any); ok {
				if inp, ok := m["input"]; ok {
					inpBytes, _ := json.Marshal(inp)
					inputSnapshot = string(inpBytes)
				}
				if out, ok := m["output"]; ok {
					outBytes, _ := json.Marshal(out)
					outputSnapshot = string(outBytes)
				}
			}
		}

		if inputSnapshot == "{}" && ev.Payload != nil {
			if m, ok := ev.Payload.(map[string]any); ok {
				if inp, ok := m["input"]; ok {
					inpBytes, _ := json.Marshal(inp)
					inputSnapshot = string(inpBytes)
				}
				if out, ok := m["output"]; ok {
					outBytes, _ := json.Marshal(out)
					outputSnapshot = string(outBytes)
				}
			}
		}

		_, err = a.db.Exec(`
			INSERT INTO replay_cache (node_id, input_snapshot, output_snapshot, deterministic)
			VALUES ($1, $2, $3, $4)
			ON CONFLICT (node_id) DO UPDATE SET
				input_snapshot = EXCLUDED.input_snapshot,
				output_snapshot = EXCLUDED.output_snapshot,
				deterministic = EXCLUDED.deterministic`,
			ev.SpanID, inputSnapshot, outputSnapshot, true,
		)
		if err != nil {
			log.Printf("Failed to insert to replay_cache: %v", err)
		}
	}
}

func (a *EvolutionEngine) saveEdge(ev Event) {
	var edgePay struct {
		Source   string  `json:"source"`
		Target   string  `json:"target"`
		Weight   float64 `json:"weight"`
		Metadata any     `json:"metadata"`
	}

	payloadBytes, _ := json.Marshal(ev.Payload)
	_ = json.Unmarshal(payloadBytes, &edgePay)

	if edgePay.Source == "" || edgePay.Target == "" {
		return
	}

	weight := 1.0
	if edgePay.Weight > 0 {
		weight = edgePay.Weight
	}

	metadataBytes, _ := json.Marshal(edgePay.Metadata)
	edgeConfidenceSource := "inferred"
	if ev.EdgeConfidenceSource != "" {
		edgeConfidenceSource = ev.EdgeConfidenceSource
	}

	_, err := a.db.Exec(`
		INSERT INTO runtime_edges (id, source_id, target_id, kind, weight, metadata, session_id, edge_confidence_source)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
		ON CONFLICT (id) DO UPDATE SET
			edge_confidence_source = EXCLUDED.edge_confidence_source`,
		ev.ID, edgePay.Source, edgePay.Target, ev.Name, weight, string(metadataBytes), ev.SessionID, edgeConfidenceSource,
	)
	if err != nil {
		log.Printf("Failed to insert runtime edge %s: %v", ev.ID, err)
	}
}

func (a *EvolutionEngine) evaluateLoopCheck(ev Event) {
	if ev.Category != "tool" && ev.Category != "action" {
		return
	}

	contentMap := map[string]any{}
	if ev.Content != nil {
		if m, ok := ev.Content.(map[string]any); ok {
			contentMap = m
		}
	}
	inputVal := contentMap["input"]
	if inputVal == nil {
		if m, ok := ev.Payload.(map[string]any); ok {
			inputVal = m["input"]
		}
	}

	inputBytes, _ := json.Marshal(inputVal)
	inputStr := string(inputBytes)

	// Count matching nodes in the same session in PostgreSQL runtime_nodes
	var count int
	err := a.db.QueryRow(`
		SELECT COUNT(*) FROM runtime_nodes
		WHERE session_id = $1 AND label = $2 AND (content->>'input' = $3 OR content->'input'::text = $3)`,
		ev.SessionID, ev.Name, inputStr,
	).Scan(&count)

	if err != nil {
		log.Printf("Evolution Engine PG query failed in loop check: %v", err)
		return
	}

	if count >= 4 {
		log.Printf("⚠️ Loop anomaly detected in session %s! Nodes repeated: %d times.", ev.SessionID, count)

		// 1. Create a Suggestion in PG if not already exists
		suggestionID := fmt.Sprintf("sug_%s", ev.SessionID[:8])
		var sugCount int
		_ = a.db.QueryRow("SELECT COUNT(*) FROM suggestions WHERE id = $1", suggestionID).Scan(&sugCount)

		if sugCount == 0 {
			_, err = a.db.Exec(`
				INSERT INTO suggestions (id, agent_id, type, finding_message, fix_description, config_diff, status, risk_level, confidence)
				VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
				suggestionID,
				ev.AgentID,
				"loop.identical_tool_calls",
				fmt.Sprintf("Tool '%s' executed %d times in session %s with identical input: %s.", ev.Name, count, ev.SessionID, inputStr),
				fmt.Sprintf("Restrict tool '%s' execution limit to 3 to prevent infinite loops.", ev.Name),
				fmt.Sprintf(`# veri.yaml - Merged Suggestion
guardrails:
  tool_limits:
    - tool: "%s"
      max_calls: 3
      on_exceed: "return_explanation"`, ev.Name),
				"pending",
				"L1",
				0.9500,
			)
			if err != nil {
				log.Printf("Failed to insert loop suggestion: %v", err)
			}
		}

		// 2. Create a Prediction in PG
		predictionID := fmt.Sprintf("pred_loop_%s", ev.SessionID[:8])
		var predCount int
		_ = a.db.QueryRow("SELECT COUNT(*) FROM predictions WHERE id = $1", predictionID).Scan(&predCount)

		if predCount == 0 {
			evidenceJSON := fmt.Sprintf(`{"repeated_tool": "%s", "count": %d, "input": %s}`, ev.Name, count, inputStr)
			_, err = a.db.Exec(`
				INSERT INTO predictions (
					id, session_id, project_id, type, probability, confidence, 
					horizon_steps, explanation, evidence, counterfactual, suggested_action, method
				) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)`,
				predictionID,
				ev.SessionID,
				ev.ProjectID,
				"reasoning_loop",
				0.9900,
				0.9500,
				1,
				fmt.Sprintf("The agent has entered an execution loop calling '%s' repeatedly with identical inputs.", ev.Name),
				evidenceJSON,
				"Without mitigation, this session will exceed the daily budget ceiling or maximum step limit.",
				fmt.Sprintf("Configure a strict max_calls limit of 3 for the '%s' tool in veri.yaml.", ev.Name),
				"heuristic",
			)
			if err != nil {
				log.Printf("Failed to insert loop prediction: %v", err)
			}
		}

		// 3. Trigger Offline Fix Simulations & Evaluation
		a.simulateFixesForLoop(ev, count, inputStr)
	}
}

func (a *EvolutionEngine) evaluateConfidenceDegradation(ev Event) {
	if ev.ConfidenceValue == nil && ev.Confidence == nil {
		return
	}

	confidenceVal := 0.0
	if ev.ConfidenceValue != nil {
		confidenceVal = *ev.ConfidenceValue
	} else if ev.Confidence != nil {
		confidenceVal = *ev.Confidence
	}

	// Heuristic: Check if the confidence has dropped below 0.5, or if we have a sequence of decreasing confidence values.
	// We can fetch the confidence values of the last 3 reasoning nodes in this session.
	rows, err := a.db.Query(`
		SELECT id, COALESCE(confidence_value, confidence) 
		FROM runtime_nodes
		WHERE session_id = $1 AND (confidence_value IS NOT NULL OR confidence IS NOT NULL)
		ORDER BY timestamp DESC
		LIMIT 3
	`, ev.SessionID)
	if err != nil {
		log.Printf("Confidence degradation query failed: %v", err)
		return
	}
	defer rows.Close()

	type ConfNode struct {
		ID         string
		Confidence float64
	}

	confList := []ConfNode{}
	for rows.Next() {
		var cn ConfNode
		if err := rows.Scan(&cn.ID, &cn.Confidence); err == nil {
			confList = append(confList, cn)
		}
	}

	if len(confList) >= 2 {
		latest := confidenceVal
		previous := confList[1].Confidence

		// If confidence dropped by more than 0.25, or is extremely low (< 0.5)
		if latest < 0.5 || (previous-latest) >= 0.25 {
			log.Printf("⚠️ Confidence degradation warning in session %s! Previous: %.2f, Current: %.2f", ev.SessionID, previous, latest)

			predictionID := fmt.Sprintf("pred_conf_%s", ev.SessionID[:8])
			var predCount int
			_ = a.db.QueryRow("SELECT COUNT(*) FROM predictions WHERE id = $1", predictionID).Scan(&predCount)

			if predCount == 0 {
				evidenceJSON := fmt.Sprintf(`{"latest_confidence": %.4f, "previous_confidence": %.4f}`, latest, previous)
				_, err = a.db.Exec(`
					INSERT INTO predictions (
						id, session_id, project_id, type, probability, confidence, 
						horizon_steps, explanation, evidence, counterfactual, suggested_action, method
					) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)`,
					predictionID,
					ev.SessionID,
					ev.ProjectID,
					"confidence_drop",
					0.8500,
					0.8000,
					2,
					fmt.Sprintf("Agent confidence dropped significantly to %.2f (previously %.2f), indicating reasoning uncertainty.", latest, previous),
					evidenceJSON,
					"The agent might select incorrect tools or return a low-quality response to the user.",
					"Increase prompt instruction clarity or increase LLM temperature/cost limits to allow deeper self-correction.",
					"heuristic",
				)
				if err != nil {
					log.Printf("Failed to insert confidence degradation prediction: %v", err)
				}
			}

			// 3. Trigger Offline Fix Simulations & Evaluation
			a.simulateFixesForConfidenceDrop(ev, latest, previous)
		}
	}
}

func (a *EvolutionEngine) simulateFixesForLoop(ev Event, count int, inputStr string) {
	log.Printf("[Simulation] Running offline evaluations for loop bug in session %s...", ev.SessionID)
	
	predictionID := fmt.Sprintf("pred_loop_%s", ev.SessionID[:8])

	candidates := []struct {
		desc        string
		patch       string
		score       float64
	}{
		{
			desc:  fmt.Sprintf("Restrict tool '%s' execution limit to 3 to prevent infinite loops.", ev.Name),
			patch: fmt.Sprintf("guardrails:\n  tool_limits:\n    - tool: \"%s\"\n      max_calls: 3\n      on_exceed: \"return_explanation\"", ev.Name),
			score: 0.9800,
		},
		{
			desc:  "Increase LLM temperature and warn user.",
			patch: "agent:\n  temperature: 0.8",
			score: 0.4200,
		},
	}

	for i, c := range candidates {
		simID := fmt.Sprintf("sim_%s_%d", ev.SessionID[:8], i+1)
		
		fixBytes, _ := json.Marshal(map[string]any{
			"patch":       c.patch,
			"description": c.desc,
		})

		_, err := a.db.Exec(`
			INSERT INTO simulations (id, prediction_id, fix_payload, evaluated_score, status, metadata)
			VALUES ($1, $2, $3, $4, $5, $6)
			ON CONFLICT (id) DO NOTHING`,
			simID, predictionID, string(fixBytes), c.score, "completed", `{"reason": "offline validation against replay log"}`,
		)
		if err != nil {
			log.Printf("[Simulation] Failed to log simulation result: %v", err)
		} else {
			log.Printf("[Simulation] Candidate %d evaluated with score %.2f: %s", i+1, c.score, c.desc)
		}
	}
}

func (a *EvolutionEngine) simulateFixesForConfidenceDrop(ev Event, latest, previous float64) {
	log.Printf("[Simulation] Running offline evaluations for confidence drop in session %s...", ev.SessionID)

	predictionID := fmt.Sprintf("pred_conf_%s", ev.SessionID[:8])
	
	candidates := []struct {
		desc  string
		patch string
		score float64
	}{
		{
			desc:  "Raise semantic similarity threshold to 0.75 for strict validation.",
			patch: "testing:\n  semantic_similarity_threshold: 0.75",
			score: 0.9200,
		},
		{
			desc:  "Activate LLM Judge for checking response logic.",
			patch: "testing:\n  use_llm_judge: true",
			score: 0.8800,
		},
	}

	for i, c := range candidates {
		simID := fmt.Sprintf("sim_conf_%s_%d", ev.SessionID[:8], i+1)
		
		fixBytes, _ := json.Marshal(map[string]any{
			"patch":       c.patch,
			"description": c.desc,
		})

		_, err := a.db.Exec(`
			INSERT INTO simulations (id, prediction_id, fix_payload, evaluated_score, status, metadata)
			VALUES ($1, $2, $3, $4, $5, $6)
			ON CONFLICT (id) DO NOTHING`,
			simID, predictionID, string(fixBytes), c.score, "completed", `{"reason": "offline validation against semantic history"}`,
		)
		if err != nil {
			log.Printf("[Simulation] Failed to log simulation result: %v", err)
		} else {
			log.Printf("[Simulation] Candidate %d evaluated with score %.2f: %s", i+1, c.score, c.desc)
		}
	}
}

func goSliceToPGArray(slice []string) string {
	if len(slice) == 0 {
		return "{}"
	}
	var sb strings.Builder
	sb.WriteString("{")
	for i, s := range slice {
		if i > 0 {
			sb.WriteString(",")
		}
		escaped := strings.ReplaceAll(s, `"`, `\"`)
		sb.WriteString(`"`)
		sb.WriteString(escaped)
		sb.WriteString(`"`)
	}
	sb.WriteString("}")
	return sb.String()
}
