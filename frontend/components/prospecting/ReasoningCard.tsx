'use client';

import React from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Brain, ChevronDown } from 'lucide-react';

interface ReasoningCardProps {
  reasoningText: string;
  timestamp: Date;
  isExpanded: boolean;
  onToggle: () => void;
}

export function ReasoningCard({ reasoningText, timestamp, isExpanded, onToggle }: ReasoningCardProps) {
  return (
    <Card className="border-blue-200 bg-blue-50/50 animate-in fade-in duration-300">
      <CardHeader
        onClick={onToggle}
        className="py-3 px-4 cursor-pointer hover:bg-blue-100/50 transition-colors"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-blue-600 flex-shrink-0" />
            <span className="font-semibold text-blue-900">Reasoning</span>
          </div>
          <ChevronDown
            className={`w-5 h-5 text-blue-600 transition-transform duration-200 ${
              isExpanded ? 'rotate-180' : ''
            }`}
          />
        </div>
      </CardHeader>
      {isExpanded && (
        <CardContent className="pt-0 pb-4 px-4">
          <p className="text-sm text-blue-800">{reasoningText}</p>
        </CardContent>
      )}
    </Card>
  );
}
