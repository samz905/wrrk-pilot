'use client';

import React, { useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { CheckCircle, Clock, Loader2, ChevronDown } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { PlatformTool, ToolActivity } from '@/lib/types';
import { ReasoningStep } from './ReasoningStep';
import Image from 'next/image';

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

  const getStatusBadge = () => {
    switch (activity.status) {
      case 'completed':
        return (
          <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200 gap-1">
            <CheckCircle className="w-3.5 h-3.5" />
            Done
          </Badge>
        );
      case 'active':
        return (
          <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 gap-1">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            Searching
          </Badge>
        );
      case 'pending':
        return (
          <Badge variant="outline" className="bg-gray-50 text-gray-500 border-gray-200 gap-1">
            <Clock className="w-3.5 h-3.5" />
            Pending
          </Badge>
        );
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
            <Image
              src={PLATFORM_ICONS[activity.tool]}
              alt={activity.tool}
              width={32}
              height={32}
              className="flex-shrink-0"
            />
            <span className="font-semibold text-lg">{activity.tool}</span>
          </div>
          <div className="flex items-center gap-3">
            {getStatusBadge()}
            <ChevronDown
              className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${
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

          {/* Strategic details - lead count and companies */}
          {activity.strategicDetails && activity.strategicDetails.leadCount > 0 && (
            <div className="bg-blue-50 border border-blue-200 p-3 rounded-lg mt-3">
              <p className="text-sm text-blue-900 font-semibold mb-1">
                Found {activity.strategicDetails.leadCount} lead{activity.strategicDetails.leadCount !== 1 ? 's' : ''}
              </p>
              {activity.strategicDetails.companies.length > 0 && (
                <p className="text-xs text-blue-700">
                  {activity.strategicDetails.companies.slice(0, 2).join(', ')}
                  {activity.strategicDetails.companies.length > 2 && (
                    <span className="text-blue-500"> +{activity.strategicDetails.companies.length - 2} more</span>
                  )}
                </p>
              )}
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
