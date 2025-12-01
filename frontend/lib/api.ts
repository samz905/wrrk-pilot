/**
 * API client for prospecting backend
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
const PROSPECT_BASE = `${API_BASE}/prospect`;

export interface StartProspectingResponse {
  job_id: string;
  message: string;
  stream_url: string;
}

export interface ProspectingEvent {
  type: 'status' | 'thought' | 'worker_start' | 'worker_complete' | 'lead_batch' | 'completed' | 'cancelled' | 'error';
  data: string;
  worker?: string;
  leads?: any[];
  count?: number;
  timestamp?: string;
}

/**
 * Get auth headers if token is provided
 */
function getAuthHeaders(token?: string): HeadersInit {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

/**
 * Start a new prospecting job
 */
export async function startProspecting(
  query: string,
  maxLeads: number = 50,
  token?: string
): Promise<StartProspectingResponse> {
  const response = await fetch(`${PROSPECT_BASE}/start`, {
    method: 'POST',
    headers: getAuthHeaders(token),
    body: JSON.stringify({
      query,
      max_leads: maxLeads,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to start prospecting: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Subscribe to SSE stream for real-time updates
 * Returns an object with close() method to stop the stream
 */
export function subscribeToEvents(
  jobId: string,
  onEvent: (event: ProspectingEvent) => void,
  onError: (error: Error) => void
): { close: () => void } {
  const eventSource = new EventSource(`${PROSPECT_BASE}/${jobId}/stream`);

  // Handle all event types
  const eventTypes = ['status', 'thought', 'worker_start', 'worker_complete', 'lead_batch', 'completed', 'cancelled', 'error'];

  eventTypes.forEach(eventType => {
    eventSource.addEventListener(eventType, (e: MessageEvent) => {
      try {
        const eventData = JSON.parse(e.data);
        onEvent(eventData);
      } catch (err) {
        // If data is not JSON, wrap it
        onEvent({
          type: eventType as ProspectingEvent['type'],
          data: e.data,
        });
      }
    });
  });

  eventSource.onerror = () => {
    onError(new Error('SSE connection failed'));
    eventSource.close();
  };

  return {
    close: () => {
      eventSource.close();
    },
  };
}

/**
 * Cancel a running prospecting job
 */
export async function cancelJob(jobId: string, token?: string): Promise<void> {
  const response = await fetch(`${PROSPECT_BASE}/${jobId}/cancel`, {
    method: 'POST',
    headers: getAuthHeaders(token),
  });

  if (!response.ok) {
    throw new Error(`Failed to cancel job: ${response.statusText}`);
  }
}

/**
 * Get final results for a completed job
 */
export async function getJobResults(jobId: string, token?: string): Promise<any> {
  const response = await fetch(`${PROSPECT_BASE}/${jobId}/results`, {
    headers: getAuthHeaders(token),
  });

  if (!response.ok) {
    throw new Error(`Failed to get results: ${response.statusText}`);
  }

  return response.json();
}
