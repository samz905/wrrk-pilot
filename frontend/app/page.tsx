'use client';

import { useState, useEffect, useRef } from 'react';
import { QueryInput } from '@/components/prospecting/QueryInput';
import { AgentWorkspace } from '@/components/prospecting/AgentWorkspace';
import { LeadsTable } from '@/components/prospecting/LeadsTable';
import { LeadDetailModal } from '@/components/prospecting/LeadDetailModal';
import { Lead, ActivityEvent, WorkspaceCard } from '@/lib/types';
import { generateCRMDemoEvents } from '@/lib/mock-data';

// Demo mode flag - set to true to use mock data without backend
const DEMO_MODE = true;

export default function ProspectingPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState<'idle' | 'running' | 'completed' | 'failed'>('idle');
  const [highlightedLeads, setHighlightedLeads] = useState<string[]>([]);

  // Workspace cards - chronological list of all reasoning and tool cards
  const [workspaceCards, setWorkspaceCards] = useState<WorkspaceCard[]>([]);

  // Timeout refs for cleanup
  const timeoutsRef = useRef<NodeJS.Timeout[]>([]);

  const handleStart = async (query: string, maxLeads: number) => {
    setIsLoading(true);
    setStatus('running');
    setLeads([]);
    setHighlightedLeads([]);
    setWorkspaceCards([]); // Start with no cards

    // Clear any existing timeouts
    timeoutsRef.current.forEach(clearTimeout);
    timeoutsRef.current = [];

    if (DEMO_MODE) {
      // Generate events with realistic timing
      const demoEvents = generateCRMDemoEvents();

      // Schedule all events
      demoEvents.forEach((event, index) => {
        const delay = event.timestamp.getTime() - demoEvents[0].timestamp.getTime();

        const timeout = setTimeout(() => {
          handleDemoEvent(event);
        }, delay);

        timeoutsRef.current.push(timeout);
      });

      // Final completion after all events
      const finalDelay = demoEvents[demoEvents.length - 1].timestamp.getTime() - demoEvents[0].timestamp.getTime();
      const finalTimeout = setTimeout(() => {
        setStatus('completed');
        setIsLoading(false);
      }, finalDelay + 1000);

      timeoutsRef.current.push(finalTimeout);

      return;
    }

    // Real API mode (when backend is ready)
    // TODO: Implement real API integration
  };

  const handleDemoEvent = (event: ActivityEvent) => {
    switch (event.type) {
      case 'thought':
        if (!event.tool) {
          // Create NEW reasoning card
          setWorkspaceCards(prev => [...prev, {
            id: `reasoning-${Date.now()}-${Math.random()}`,
            type: 'reasoning',
            reasoningText: event.data,
            timestamp: event.timestamp
          }]);
        } else {
          // Add thought to the most recent tool card with this tool
          setWorkspaceCards(prev => {
            const lastIndex = prev.map(c => c.tool).lastIndexOf(event.tool);
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
        break;

      case 'tool_start':
        if (event.tool) {
          // ALWAYS create NEW tool card (never reuse)
          setWorkspaceCards(prev => [...prev, {
            id: `${event.tool}-${Date.now()}-${Math.random()}`,
            type: 'tool',
            tool: event.tool,
            status: 'active',
            thoughts: [],
            isThinking: false,
            timestamp: event.timestamp
          }]);
        }
        break;

      case 'thinking':
        if (event.tool) {
          // Update most recent tool card with this tool to show thinking state
          setWorkspaceCards(prev => {
            const lastIndex = prev.map(c => c.tool).lastIndexOf(event.tool);
            if (lastIndex >= 0) {
              return prev.map((card, idx) =>
                idx === lastIndex && card.type === 'tool'
                  ? { ...card, isThinking: true }
                  : card
              );
            }
            return prev;
          });
        }
        break;

      case 'tool_complete':
        if (event.tool) {
          // Update most recent tool card with this tool to completed
          setWorkspaceCards(prev => {
            const lastIndex = prev.map(c => c.tool).lastIndexOf(event.tool);
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
        break;

      case 'lead_batch':
        if (event.leads && event.leads.length > 0) {
          // Add new leads
          setLeads(prev => {
            const combined = [...prev, ...event.leads!];
            // Sort by score descending
            return combined.sort((a, b) => b.score - a.score);
          });

          // Highlight new leads
          const newLeadNames = event.leads.map(l => l.name);
          setHighlightedLeads(newLeadNames);

          // Remove highlight after 2 seconds
          setTimeout(() => {
            setHighlightedLeads([]);
          }, 2000);
        }
        break;
    }
  };

  // Cleanup timeouts on unmount
  useEffect(() => {
    return () => {
      timeoutsRef.current.forEach(clearTimeout);
    };
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Minimal Header - Not Sticky */}
      <header className="bg-white border-b shadow-sm">
        <div className="container mx-auto px-6 py-6">
          <QueryInput onStart={handleStart} isLoading={isLoading} />
        </div>
      </header>

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
