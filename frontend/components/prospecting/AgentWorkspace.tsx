'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Bot } from 'lucide-react';
import { WorkspaceCard } from '@/lib/types';
import { ToolCard } from './ToolCard';
import { ReasoningCard } from './ReasoningCard';
import { ProgressHeader } from './ProgressHeader';

interface AgentWorkspaceProps {
  workspaceCards: WorkspaceCard[];
  progress?: { current: number; target: number };
  phase?: 'searching' | 'complete' | 'idle';
}

export function AgentWorkspace({ workspaceCards, progress, phase = 'idle' }: AgentWorkspaceProps) {
  const [expandedCards, setExpandedCards] = useState<Set<string>>(new Set());
  const bottomRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new cards are added
  useEffect(() => {
    if (bottomRef.current && contentRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [workspaceCards]);

  // Auto-expand the latest card (active tool or most recent reasoning)
  useEffect(() => {
    if (workspaceCards.length > 0) {
      const lastCard = workspaceCards[workspaceCards.length - 1];

      // Auto-expand active tool cards
      const activeToolCard = workspaceCards.find(c => c.type === 'tool' && c.status === 'active');
      if (activeToolCard) {
        setExpandedCards(prev => new Set([...prev, activeToolCard.id]));
      }

      // Auto-expand the most recent card (reasoning or tool)
      if (lastCard) {
        setExpandedCards(prev => new Set([...prev, lastCard.id]));
      }
    }
  }, [workspaceCards]);

  const toggleExpand = (cardId: string) => {
    setExpandedCards(prev => {
      const newSet = new Set(prev);
      if (newSet.has(cardId)) {
        newSet.delete(cardId);
      } else {
        newSet.add(cardId);
      }
      return newSet;
    });
  };

  const activeToolCard = workspaceCards.find(c => c.type === 'tool' && c.status === 'active');

  return (
    <Card className="h-[calc(100vh-180px)]">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Bot className="w-5 h-5 text-blue-500" />
          Agent Workspace
        </CardTitle>
      </CardHeader>
      <CardContent ref={contentRef} className="h-[calc(100%-80px)] overflow-y-auto space-y-3">
        {/* Progress Header */}
        {progress && (
          <ProgressHeader
            currentLeads={progress.current}
            targetLeads={progress.target}
            phase={phase}
          />
        )}

        {workspaceCards.length === 0 && !progress ? (
          <div className="flex items-center justify-center h-full text-muted-foreground">
            <p className="text-sm">Waiting for query...</p>
          </div>
        ) : (
          <>
            {workspaceCards.map((card) => (
              <div key={card.id}>
                {card.type === 'reasoning' ? (
                  <ReasoningCard
                    reasoningText={card.reasoningText!}
                    timestamp={card.timestamp}
                    isExpanded={expandedCards.has(card.id)}
                    onToggle={() => toggleExpand(card.id)}
                  />
                ) : (
                  <ToolCard
                    activity={{
                      tool: card.tool!,
                      status: card.status === 'active' ? 'active' : 'completed',
                      thoughts: card.thoughts || [],
                      isThinking: card.isThinking || false,
                      results: card.results,
                      strategicDetails: card.strategicDetails
                    }}
                    isExpanded={expandedCards.has(card.id)}
                    onToggle={() => toggleExpand(card.id)}
                    isActive={activeToolCard?.id === card.id}
                  />
                )}
              </div>
            ))}
            {/* Invisible element at bottom for auto-scroll */}
            <div ref={bottomRef} />
          </>
        )}
      </CardContent>
    </Card>
  );
}
