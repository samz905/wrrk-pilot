'use client';

import React from 'react';
import { Brain } from 'lucide-react';

interface ReasoningStepProps {
  text: string;
  timestamp?: Date;
}

export function ReasoningStep({ text, timestamp }: ReasoningStepProps) {
  return (
    <div className="flex items-start gap-3 py-2 animate-in fade-in duration-300">
      <Brain className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
      <div className="flex-1">
        <p className="text-sm text-gray-700">{text}</p>
        {timestamp && (
          <p className="text-xs text-gray-400 mt-1">
            {timestamp.toLocaleTimeString()}
          </p>
        )}
      </div>
    </div>
  );
}
