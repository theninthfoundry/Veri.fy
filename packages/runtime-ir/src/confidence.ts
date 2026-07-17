export interface Confidence {
  value: number;                 // 0.0–1.0
  source: 'measured' | 'self_reported' | 'derived' | 'unavailable';
  method?: string;               // 'retrieval_cosine_sim' | 'llm_logprob' | 'self_consistency_k5' | 'reranker_score'
}
