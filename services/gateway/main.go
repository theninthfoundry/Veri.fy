package main

import (
	"context"
	"database/sql"
	"fmt"
	"log"
	"net/http"
	"os"
	"time"

	_ "github.com/ClickHouse/clickhouse-go/v2"
	"github.com/gin-gonic/gin"
	"github.com/nats-io/nats.go"
)

// Event maps to the ClickHouse schema structure.
type Event struct {
	ID             string    `json:"id" binding:"required"`
	ParentSpanID   string    `json:"parent_span_id"`
	SpanID         string    `json:"span_id"`
	ProjectID      string    `json:"project_id" binding:"required"`
	AgentID        string    `json:"agent_id" binding:"required"`
	SessionID      string    `json:"session_id" binding:"required"`
	Category       string    `json:"category" binding:"required"`
	Type           string    `json:"type" binding:"required"`
	Name           string    `json:"name"`
	Payload        any       `json:"payload"`
	Timestamp      float64   `json:"timestamp" binding:"required"`
	LatencyMs      uint32    `json:"latency_ms"`
	CostUSD        float64   `json:"cost_usd"`
	TokensInput    uint32    `json:"tokens_input"`
	TokensOutput   uint32    `json:"tokens_output"`
}

type BatchRequest struct {
	Events []Event `json:"events" binding:"required"`
}

type GatewayServer struct {
	chConn *sql.DB
	natsJS nats.JetStreamContext
}

func main() {
	log.Println("Starting VERI Ingestion Gateway Server...")

	// Get configuration from env
	chURL := os.Getenv("CLICKHOUSE_URL")
	if chURL == "" {
		chURL = "clickhouse://localhost:9000?database=veri"
	}
	natsURL := os.Getenv("NATS_URL")
	if natsURL == "" {
		natsURL = "nats://localhost:4222"
	}
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	// 1. ClickHouse connection setup
	chConn, err := sql.Open("clickhouse", chURL)
	if err != nil {
		log.Fatalf("Fatal: ClickHouse connection failure: %v", err)
	}
	defer chConn.Close()

	// Wait and verify ClickHouse connection
	for i := 0; i < 5; i++ {
		if err := chConn.Ping(); err == nil {
			log.Println("Successfully connected to ClickHouse Event Store.")
			break
		}
		log.Println("Waiting for ClickHouse server to be ready...")
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
		log.Fatalf("Fatal: JetStream configuration failure: %v", err)
	}

	// Create verification stream if not present
	_, _ = js.AddStream(&nats.StreamConfig{
		Name:     "VERI_EVENTS",
		Subjects: []string{"veri.event.*"},
	})

	server := &GatewayServer{
		chConn: chConn,
		natsJS: js,
	}

	// 3. Gin HTTP server setup
	gin.SetMode(gin.ReleaseMode)
	r := gin.New()
	r.Use(gin.Recovery())

	// Health and Ingestion endpoints
	r.GET("/health", server.HandleHealth)
	r.POST("/v1/events", server.HandleIngestion)

	log.Printf("Gateway running successfully on port %s", port)
	if err := r.Run(":" + port); err != nil {
		log.Fatalf("Fatal: Ingestion gateway crash: %v", err)
	}
}

func (s *GatewayServer) HandleHealth(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"status": "healthy", "time": time.Now().UTC()})
}

func (s *GatewayServer) HandleIngestion(c *gin.Context) {
	var req BatchRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Validation failed: " + err.Error()})
		return
	}

	// Process batch in non-blocking way to keep latency ≤ 30ms
	go s.processBatch(req.Events)

	c.JSON(http.StatusOK, gin.H{"processed": len(req.Events)})
}

func (s *GatewayServer) processBatch(events []Event) {
	ctx := context.Background()

	// Prepare ClickHouse batch insert statement
	tx, err := s.chConn.BeginTx(ctx, nil)
	if err != nil {
		log.Printf("Error starting ClickHouse transaction: %v", err)
		return
	}

	stmt, err := tx.Prepare("INSERT INTO events (id, parent_span_id, span_id, project_id, agent_id, session_id, category, type, name, payload, latency_ms, cost_usd, tokens_input, tokens_output, timestamp)")
	if err != nil {
		log.Printf("Error preparing ClickHouse query: %v", err)
		_ = tx.Rollback()
		return
	}
	defer stmt.Close()

	for _, e := range events {
		// Convert floating unix timestamp to DateTime64 compatibility
		t := time.Unix(0, int64(e.Timestamp*1e9)).UTC()

		// Serialize payload fallback to avoid DB crashes
		payloadStr := "{}"
		if e.Payload != nil {
			if str, ok := e.Payload.(string); ok {
				payloadStr = str
			} else {
				payloadStr = fmt.Sprintf("%v", e.Payload)
			}
		}

		// Insert event to ClickHouse batch
		_, err = stmt.Exec(
			e.ID,
			e.ParentSpanID,
			e.SpanID,
			e.ProjectID,
			e.AgentID,
			e.SessionID,
			e.Category,
			e.Type,
			e.Name,
			payloadStr,
			e.LatencyMs,
			e.CostUSD,
			e.TokensInput,
			e.TokensOutput,
			t,
		)
		if err != nil {
			log.Printf("Error batching event %s: %v", e.ID, err)
			continue
		}

		// Dispatch event to NATS JetStream for rule processing
		subj := fmt.Sprintf("veri.event.%s", e.Category)
		eventJSON := fmt.Sprintf(`{"id":"%s","session_id":"%s","agent_id":"%s","project_id":"%s","type":"%s"}`, e.ID, e.SessionID, e.AgentID, e.ProjectID, e.Type)
		_, err = s.natsJS.PublishAsync(subj, []byte(eventJSON))
		if err != nil {
			log.Printf("NATS JetStream async publish failed for %s: %v", e.ID, err)
		}
	}

	// Commit batch transaction to ClickHouse
	if err := tx.Commit(); err != nil {
		log.Printf("Error committing transaction to ClickHouse: %v", err)
	}
}
