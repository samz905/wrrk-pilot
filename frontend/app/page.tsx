'use client';

import { useState, useEffect, useRef } from 'react';
import { QueryInput } from '@/components/prospecting/QueryInput';
import { AgentWorkspace } from '@/components/prospecting/AgentWorkspace';
import { LeadsTable } from '@/components/prospecting/LeadsTable';
import { LeadDetailModal } from '@/components/prospecting/LeadDetailModal';
import { Lead, WorkspaceCard, PlatformTool, WORKER_TO_PLATFORM, transformLead } from '@/lib/types';
import { startProspecting, subscribeToEvents, cancelJob, ProspectingEvent } from '@/lib/api';

export default function ProspectingPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState<'idle' | 'running' | 'completed' | 'failed' | 'cancelled'>('idle');
  const [highlightedLeads, setHighlightedLeads] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Workspace cards - chronological list of all reasoning and tool cards
  const [workspaceCards, setWorkspaceCards] = useState<WorkspaceCard[]>([]);

  // Job and stream refs
  const jobIdRef = useRef<string | null>(null);
  const eventSourceRef = useRef<{ close: () => void } | null>(null);

  const handleStart = async (query: string) => {
    setIsLoading(true);
    setStatus('running');
    setLeads([]);
    setHighlightedLeads([]);
    setWorkspaceCards([]);
    setError(null);

    try {
      // Start prospecting job (hardcoded 50 leads)
      const response = await startProspecting(query, 50);
      jobIdRef.current = response.job_id;

      // Subscribe to SSE stream
      eventSourceRef.current = subscribeToEvents(
        response.job_id,
        handleEvent,
        (err) => {
          console.error('SSE error:', err);
          setError(err.message);
          setStatus('failed');
          setIsLoading(false);
        }
      );
    } catch (err: any) {
      console.error('Failed to start prospecting:', err);
      setError(err.message || 'Failed to start prospecting');
      setStatus('failed');
      setIsLoading(false);
    }
  };

  const handleStop = async () => {
    if (!jobIdRef.current) return;

    try {
      // Close SSE connection
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }

      // Cancel job on backend
      await cancelJob(jobIdRef.current);

      setStatus('cancelled');
      setIsLoading(false);
    } catch (err: any) {
      console.error('Failed to cancel job:', err);
      // Still update UI even if cancel fails
      setStatus('cancelled');
      setIsLoading(false);
    }
  };

  const handleEvent = (event: ProspectingEvent) => {
    const timestamp = event.timestamp ? new Date(event.timestamp) : new Date();

    switch (event.type) {
      case 'status':
        // Initial status event
        break;

      case 'thought':
        if (event.worker) {
          // Add thought to the most recent tool card with this worker
          const tool = WORKER_TO_PLATFORM[event.worker];
          if (tool) {
            setWorkspaceCards(prev => {
              const lastIndex = prev.map(c => c.tool).lastIndexOf(tool);
              if (lastIndex >= 0) {
                return prev.map((card, idx) =>
                  idx === lastIndex && card.type === 'tool'
                    ? {
                        ...card,
                        thoughts: [...(card.thoughts || []), event.data],
                        isThinking: false
                      }
                    : card
                );
              }
              return prev;
            });
          }
        } else {
          // Create NEW reasoning card
          setWorkspaceCards(prev => [...prev, {
            id: `reasoning-${Date.now()}-${Math.random()}`,
            type: 'reasoning',
            reasoningText: event.data,
            timestamp
          }]);
        }
        break;

      case 'worker_start':
        if (event.worker) {
          const tool = WORKER_TO_PLATFORM[event.worker];
          if (tool) {
            // Create NEW tool card
            setWorkspaceCards(prev => [...prev, {
              id: `${tool}-${Date.now()}-${Math.random()}`,
              type: 'tool',
              tool,
              status: 'active',
              thoughts: [event.data],
              isThinking: true,
              timestamp
            }]);
          }
        }
        break;

      case 'worker_complete':
        if (event.worker) {
          const tool = WORKER_TO_PLATFORM[event.worker];
          if (tool) {
            // Update most recent tool card with this tool to completed
            setWorkspaceCards(prev => {
              const lastIndex = prev.map(c => c.tool).lastIndexOf(tool);
              if (lastIndex >= 0) {
                return prev.map((card, idx) =>
                  idx === lastIndex && card.type === 'tool'
                    ? {
                        ...card,
                        status: 'completed',
                        isThinking: false,
                        results: event.data
                      }
                    : card
                );
              }
              return prev;
            });
          }
        }
        break;

      case 'lead_batch':
        // Parse leads from event
        let rawLeads: any[] = [];
        if (event.leads) {
          rawLeads = event.leads;
        } else if (event.data) {
          try {
            rawLeads = JSON.parse(event.data);
          } catch {
            rawLeads = [];
          }
        }

        if (rawLeads.length > 0) {
          // Transform to frontend Lead format
          const newLeads = rawLeads.map(transformLead);

          // Add new leads
          setLeads(prev => {
            const combined = [...prev, ...newLeads];
            // Sort by score descending
            return combined.sort((a, b) => b.score - a.score);
          });

          // Highlight new leads
          const newLeadNames = newLeads.map(l => l.name);
          setHighlightedLeads(newLeadNames);

          // Remove highlight after 2 seconds
          setTimeout(() => {
            setHighlightedLeads([]);
          }, 2000);
        }
        break;

      case 'completed':
        setStatus('completed');
        setIsLoading(false);
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
        break;

      case 'cancelled':
        setStatus('cancelled');
        setIsLoading(false);
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
        break;

      case 'error':
        setError(event.data);
        setStatus('failed');
        setIsLoading(false);
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
        break;
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header with Query Input and Stop Button */}
      <header className="bg-white border-b shadow-sm">
        <div className="container mx-auto px-6 py-6">
          <QueryInput
            onStart={handleStart}
            onStop={handleStop}
            isLoading={isLoading}
          />
        </div>
      </header>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 border-b border-red-200 px-6 py-3">
          <div className="container mx-auto text-red-700">
            Error: {error}
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="container mx-auto p-6">
        <div className="grid grid-cols-12 gap-6">
          {/* Left Panel - Agent Workspace */}
          <div className="col-span-12 lg:col-span-4">
            {status !== 'idle' ? (
              <AgentWorkspace workspaceCards={workspaceCards} />
            ) : (
              <div className="flex items-center justify-center h-[calc(100vh-180px)] bg-white rounded-lg border-2 border-dashed border-gray-200">
                <div className="text-center text-muted-foreground p-8">
                  <p className="text-lg font-medium mb-2">Ready to find leads</p>
                  <p className="text-sm">Enter a query above to start prospecting</p>
                </div>
              </div>
            )}
          </div>

          {/* Right Panel - Results Table */}
          <div className="col-span-12 lg:col-span-8">
            <LeadsTable
              leads={leads}
              onLeadClick={setSelectedLead}
              highlightedLeads={highlightedLeads}
            />
          </div>
        </div>
      </div>

      {/* Lead Detail Modal */}
      <LeadDetailModal
        lead={selectedLead}
        isOpen={!!selectedLead}
        onClose={() => setSelectedLead(null)}
      />
    </div>
  );
}
