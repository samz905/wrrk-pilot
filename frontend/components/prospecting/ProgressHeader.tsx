'use client';

import { Search, CheckCircle, Loader2 } from 'lucide-react';

interface ProgressHeaderProps {
  currentLeads: number;
  targetLeads: number;
  phase: 'searching' | 'complete' | 'idle';
}

export function ProgressHeader({ currentLeads, targetLeads, phase }: ProgressHeaderProps) {
  const progress = Math.min((currentLeads / targetLeads) * 100, 100);
  const isComplete = phase === 'complete' || currentLeads >= targetLeads;

  const getPhaseText = () => {
    if (isComplete) return 'Search complete';
    if (phase === 'searching') return 'Searching for leads...';
    return 'Ready to search';
  };

  const getPhaseIcon = () => {
    if (isComplete) {
      return <CheckCircle className="w-5 h-5 text-green-500" />;
    }
    if (phase === 'searching') {
      return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
    }
    return <Search className="w-5 h-5 text-gray-400" />;
  };

  return (
    <div className="bg-white border rounded-lg p-4 mb-4 shadow-sm">
      <div className="flex items-center gap-3 mb-3">
        {getPhaseIcon()}
        <span className="font-medium text-gray-900">{getPhaseText()}</span>
      </div>

      {phase !== 'idle' && (
        <div className="space-y-2">
          {/* Progress bar */}
          <div className="w-full bg-gray-100 rounded-full h-2.5 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ease-out ${
                isComplete ? 'bg-green-500' : 'bg-blue-500'
              }`}
              style={{ width: `${progress}%` }}
            />
          </div>

          {/* Progress text */}
          <div className="flex justify-between items-center text-sm">
            <span className="text-gray-600">
              {currentLeads} / {targetLeads} leads
            </span>
            <span className="text-gray-500">
              {Math.round(progress)}%
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
