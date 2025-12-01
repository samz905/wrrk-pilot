/**
 * TypeScript interfaces for Lead Prospecting application
 *
 * Lead interface matches backend structure from SupervisorOrchestrator
 */

export interface Lead {
  // Core identification
  name: string;
  username?: string;
  title?: string;
  company?: string;

  // Scoring (from backend intent_score)
  score: number;
  priority: 'HOT' | 'WARM' | 'COLD';  // Derived: >=80 HOT, >=60 WARM, else COLD

  // Contact info
  contact: {
    email?: string;
    linkedin?: string;
  };

  // Intent signals
  intent_signal?: string;
  source_platform?: string;  // 'reddit' | 'techcrunch' | 'linkedin'

  // Additional fields
  platforms_found: string[];
  user_type?: string;
}

/**
 * Transform raw backend lead to frontend Lead format
 * Handles both SSE event format and database format
 */
export function transformLead(raw: any): Lead {
  // Handle both intent_score (backend) and score (if already transformed)
  const score = raw.score ?? raw.intent_score ?? 0;
  let priority: 'HOT' | 'WARM' | 'COLD' = 'COLD';
  if (score >= 80) priority = 'HOT';
  else if (score >= 60) priority = 'WARM';

  // Handle intent_signals (database array) or intent_signal (SSE event)
  let intentSignal = raw.intent_signal;
  if (!intentSignal && raw.intent_signals) {
    // Database stores as array - join them or take first
    intentSignal = Array.isArray(raw.intent_signals)
      ? raw.intent_signals.join(', ')
      : raw.intent_signals;
  }

  // Handle platform (database) or source_platform (SSE event)
  const platform = raw.source_platform || raw.platform;

  return {
    name: raw.name || raw.username || 'Unknown',
    username: raw.username,
    title: raw.title,
    company: raw.company,
    score,
    priority,
    contact: {
      email: raw.email,
      linkedin: raw.linkedin_url,
    },
    intent_signal: intentSignal,
    source_platform: platform,
    platforms_found: platform ? [platform] : [],
    user_type: raw.user_type,
  };
}

export interface ActivityEvent {
  type: 'thought' | 'worker_start' | 'worker_complete' | 'error' | 'tool_start' | 'tool_complete' | 'thinking' | 'lead_batch' | 'completed' | 'cancelled' | 'status';
  data: string;
  timestamp: Date;
  tool?: PlatformTool;
  worker?: string;  // 'reddit' | 'techcrunch' | 'competitor'
  leads?: Lead[];
}

export type PlatformTool = 'Reddit' | 'LinkedIn' | 'Twitter' | 'Google';

/**
 * Map backend worker names to frontend PlatformTool
 */
export const WORKER_TO_PLATFORM: Record<string, PlatformTool> = {
  'reddit': 'Reddit',
  'techcrunch': 'Google',    // TechCrunch uses Google SERP
  'competitor': 'LinkedIn',  // Competitor scrapes LinkedIn
};

export interface ToolActivity {
  tool: PlatformTool;
  status: 'pending' | 'active' | 'completed';
  thoughts: string[];
  isThinking: boolean;
  results?: string;
  startTime?: Date;
  endTime?: Date;
  strategicDetails?: StrategicDetails;  // Lead count and companies found
}

// Strategic details for workspace cards
export interface StrategicDetails {
  leadCount: number;
  companies: string[];  // First 2-3 company names from leads
}

// Unified card interface for chronological workspace
export interface WorkspaceCard {
  id: string; // Unique ID for each card
  type: 'tool' | 'reasoning';
  timestamp: Date;

  // For tool cards
  tool?: PlatformTool;
  status?: 'active' | 'completed';
  thoughts?: string[];
  isThinking?: boolean;
  results?: string;
  strategicDetails?: StrategicDetails;  // Lead count and companies found

  // For reasoning cards
  reasoningText?: string;
}

export interface ProspectingJob {
  job_id: string;
  query: string;
  status: 'initializing' | 'running' | 'completed' | 'failed';
  leads: Lead[];
  events: ActivityEvent[];
}

export const CREWS = [
  { name: 'Reddit', weight: 16.7, description: 'Finding intent signals in discussions' },
  { name: 'LinkedIn', weight: 16.7, description: 'Identifying decision-makers' },
  { name: 'Twitter', weight: 16.7, description: 'Discovering conversations' },
  { name: 'Google', weight: 16.7, description: 'Finding company triggers' },
  { name: 'Aggregation', weight: 16.6, description: 'Deduplicating leads' },
  { name: 'Qualification', weight: 16.6, description: 'Scoring and ranking' }
] as const;
