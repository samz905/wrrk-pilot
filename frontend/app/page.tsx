'use client';

import { useState, useEffect, useRef } from 'react';
import { QueryInput } from '@/components/prospecting/QueryInput';
import { AgentWorkspace } from '@/components/prospecting/AgentWorkspace';
import { LeadsTable } from '@/components/prospecting/LeadsTable';
import { LeadDetailModal } from '@/components/prospecting/LeadDetailModal';
import { Header } from '@/components/layout/Header';
import { Lead, WorkspaceCard, PlatformTool, WORKER_TO_PLATFORM, transformLead } from '@/lib/types';
import { startProspecting, subscribeToEvents, cancelJob, ProspectingEvent } from '@/lib/api';
import { createClient } from '@/lib/supabase/client';

export default function ProspectingPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState<'idle' | 'running' | 'completed' | 'failed' | 'cancelled'>('idle');
  const [highlightedLeads, setHighlightedLeads] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Progress tracking
  const [progress, setProgress] = useState({ current: 0, target: 50 });

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
    setProgress({ current: 0, target: 50 });

    try {
      // Get auth token for persistence
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;

      // Start prospecting job (hardcoded 50 leads)
      const response = await startProspecting(query, 50, token);
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
          // Only show meaningful reasoning cards (strategy decisions, completion)
          const MEANINGFUL_PATTERNS = [
            /planning/i,
            /strategy/i,
            /identified.*competitors?/i,
            /target.*reached/i,
            /complete/i,
            /found \d+ leads/i,
            /deploying/i,
            /starting lead search/i,
          ];

          const isReasoningMeaningful = MEANINGFUL_PATTERNS.some(p => p.test(event.data));
          if (isReasoningMeaningful) {
            // Create NEW reasoning card
            setWorkspaceCards(prev => [...prev, {
              id: `reasoning-${Date.now()}-${Math.random()}`,
              type: 'reasoning',
              reasoningText: event.data,
              timestamp
            }]);
          }
          // Otherwise skip - don't clutter UI with technical details
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

          // Add new leads (backend already limits to target via aggregation)
          setLeads(prev => {
            const combined = [...prev, ...newLeads];
            // Sort by score descending
            return combined.sort((a, b) => b.score - a.score);
          });

          // Update progress
          setProgress(prev => ({
            ...prev,
            current: prev.current + newLeads.length
          }));

          // Update workspace card with strategic details AND mark as complete
          if (event.worker) {
            const tool = WORKER_TO_PLATFORM[event.worker];
            if (tool) {
              // Extract unique company names from leads
              const companies = [...new Set(newLeads.map(l => l.company).filter(Boolean))] as string[];

              setWorkspaceCards(prev => {
                const lastIndex = prev.map(c => c.tool).lastIndexOf(tool);
                if (lastIndex >= 0) {
                  return prev.map((card, idx) =>
                    idx === lastIndex && card.type === 'tool'
                      ? {
                          ...card,
                          status: 'completed',  // Mark worker as complete when leads arrive
                          isThinking: false,
                          strategicDetails: {
                            leadCount: (card.strategicDetails?.leadCount || 0) + newLeads.length,
                            companies: [...(card.strategicDetails?.companies || []), ...companies].slice(0, 10)
                          }
                        }
                      : card
                  );
                }
                return prev;
              });
            }
          }

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
        // Close connection FIRST to prevent any more events
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
        setStatus('completed');
        setIsLoading(false);
        // Mark ALL tool cards as completed (not just active ones)
        setWorkspaceCards(prev => prev.map(card =>
          card.type === 'tool' && card.status !== 'completed'
            ? { ...card, status: 'completed', isThinking: false }
            : card
        ));
        break;

      case 'cancelled':
        // Close connection FIRST
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
        setStatus('cancelled');
        setIsLoading(false);
        // Mark all tool cards as completed to stop spinners
        setWorkspaceCards(prev => prev.map(card =>
          card.type === 'tool' && card.status !== 'completed'
            ? { ...card, status: 'completed', isThinking: false }
            : card
        ));
        break;

      case 'error':
        // Close connection FIRST
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
        setError(event.data);
        setStatus('failed');
        setIsLoading(false);
        // Mark all tool cards as completed to stop spinners
        setWorkspaceCards(prev => prev.map(card =>
          card.type === 'tool' && card.status !== 'completed'
            ? { ...card, status: 'completed', isThinking: false }
            : card
        ));
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
    <div className="min-h-screen bg-gradient-to-br from-zinc-900 via-zinc-800 to-zinc-900">
      {/* Navigation Header */}
      <Header />

      {/* Query Input Section */}
      <div className="border-b border-zinc-800 bg-zinc-900/50">
        <div className="container mx-auto px-6 py-6">
          <QueryInput
            onStart={handleStart}
            onStop={handleStop}
            isLoading={isLoading}
          />
        </div>
      </div>

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
              <AgentWorkspace
                workspaceCards={workspaceCards}
                progress={progress}
                phase={status === 'completed' ? 'complete' : status === 'running' ? 'searching' : 'idle'}
              />
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
          <div className="col-span-12 lg:col-span-8 h-[calc(100vh-180px)]">
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
