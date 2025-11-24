'use client';

import { useEffect, useRef } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { ActivityEvent } from '@/lib/types';
import { Brain, Loader2, CheckCircle, AlertCircle, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AgentActivityProps {
  events: ActivityEvent[];
}

export function AgentActivity({ events }: AgentActivityProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTo({
        top: containerRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [events]);

  const getEventIcon = (type: ActivityEvent['type']) => {
    switch (type) {
      case 'crew_started':
        return <Loader2 className="w-4 h-4 animate-spin flex-shrink-0" />;
      case 'crew_completed':
        return <CheckCircle className="w-4 h-4 flex-shrink-0" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 flex-shrink-0" />;
      case 'thought':
        return <Brain className="w-4 h-4 flex-shrink-0" />;
      default:
        return <Activity className="w-4 h-4 flex-shrink-0" />;
    }
  };

  const getEventStyles = (type: ActivityEvent['type']) => {
    switch (type) {
      case 'crew_started':
        return 'bg-blue-50 text-blue-900 border-blue-200';
      case 'crew_completed':
        return 'bg-green-50 text-green-900 border-green-200';
      case 'error':
        return 'bg-red-50 text-red-900 border-red-200';
      case 'thought':
        return 'bg-gray-50 text-gray-700 border-gray-200';
      default:
        return 'bg-gray-50 text-gray-700 border-gray-200';
    }
  };

  const formatEventType = (type: ActivityEvent['type']) => {
    return type.replace('_', ' ').toUpperCase();
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="w-5 h-5" />
          Agent Activity
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div
          ref={containerRef}
          className="h-96 overflow-y-auto space-y-2 pr-2"
        >
          {events.length === 0 ? (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <p className="text-sm">Waiting for prospecting to start...</p>
            </div>
          ) : (
            events.map((event, idx) => (
              <div
                key={idx}
                className={cn(
                  'p-3 rounded-lg border text-sm transition-all',
                  getEventStyles(event.type)
                )}
              >
                <div className="flex items-start gap-2">
                  {getEventIcon(event.type)}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-xs mb-1">
                      {formatEventType(event.type)}
                    </p>
                    <p className="text-sm leading-relaxed break-words">
                      {event.data}
                    </p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}
