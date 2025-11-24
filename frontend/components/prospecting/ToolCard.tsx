'use client';

import React, { useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { CheckCircle, Circle, Loader2, ChevronDown } from 'lucide-react';
import { PlatformTool, ToolActivity } from '@/lib/types';
import { ReasoningStep } from './ReasoningStep';

interface ToolCardProps {
  activity: ToolActivity;
  isExpanded: boolean;
  onToggle: () => void;
  isActive?: boolean;
}

const PLATFORM_ICONS: Record<PlatformTool, string> = {
  Reddit: '/icons/reddit.svg',
  LinkedIn: '/icons/linkedin.svg',
  Twitter: '/icons/x.svg',
  Google: '/icons/google.svg',
};

export function ToolCard({ activity, isExpanded, onToggle, isActive }: ToolCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to active card
  useEffect(() => {
    if (isActive && cardRef.current) {
      cardRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
      });
    }
  }, [isActive]);

  const getStatusIcon = () => {
    switch (activity.status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'active':
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
      case 'pending':
        return <Circle className="w-5 h-5 text-gray-300" />;
    }
  };

  const getBorderClass = () => {
    if (activity.status === 'active') {
      return 'border-blue-500 shadow-lg shadow-blue-100';
    }
    if (activity.status === 'completed') {
      return 'border-green-200';
    }
    return 'border-gray-200';
  };

  return (
    <Card
      ref={cardRef}
      className={`transition-all duration-300 ${getBorderClass()}`}
    >
      <CardHeader
        onClick={onToggle}
        className="cursor-pointer hover:bg-gray-50 transition-colors py-4"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img
              src={PLATFORM_ICONS[activity.tool]}
              alt={`${activity.tool} icon`}
              className="w-8 h-8"
            />
            <span className="font-semibold text-lg">{activity.tool}</span>
          </div>
          <div className="flex items-center gap-2">
            {getStatusIcon()}
            <ChevronDown
              className={`w-5 h-5 text-gray-500 transition-transform duration-200 ${
                isExpanded ? 'rotate-180' : ''
              }`}
            />
          </div>
        </div>
      </CardHeader>

      {isExpanded && (
        <CardContent className="pt-0 pb-4 space-y-2">
          {/* Reasoning steps */}
          {activity.thoughts.length > 0 && (
            <div className="space-y-1">
              {activity.thoughts.map((thought, idx) => (
                <ReasoningStep key={idx} text={thought} />
              ))}
            </div>
          )}

          {/* Thinking state */}
          {activity.isThinking && (
            <div className="flex items-center gap-2 text-muted-foreground py-3 px-2 bg-blue-50 rounded-lg">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-sm font-medium">Thinking...</span>
            </div>
          )}

          {/* Results summary */}
          {activity.results && (
            <div className="bg-green-50 border border-green-200 p-3 rounded-lg mt-3">
              <p className="text-sm text-green-900 font-medium">{activity.results}</p>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}
