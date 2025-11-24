'use client';

import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { CREWS } from '@/lib/types';
import { CheckCircle, Loader2, Circle } from 'lucide-react';

interface ProgressBarProps {
  currentCrew: string | null;
  status: 'idle' | 'running' | 'completed' | 'failed';
}

export function ProgressBar({ currentCrew, status }: ProgressBarProps) {
  // Calculate progress based on current crew
  const progress = React.useMemo(() => {
    if (status === 'completed') return 100;
    if (status === 'idle' || !currentCrew) return 0;

    const currentIndex = CREWS.findIndex(crew => crew.name === currentCrew);
    if (currentIndex === -1) return 0;

    // Sum weights of completed crews + half weight of current crew
    return CREWS.reduce((acc, crew, idx) => {
      if (idx < currentIndex) {
        return acc + crew.weight;
      } else if (idx === currentIndex) {
        return acc + crew.weight / 2;
      }
      return acc;
    }, 0);
  }, [currentCrew, status]);

  const getCrewStatus = (crewName: string) => {
    if (status === 'idle') return 'pending';
    if (status === 'completed') return 'completed';

    const currentIndex = CREWS.findIndex(crew => crew.name === currentCrew);
    const crewIndex = CREWS.findIndex(crew => crew.name === crewName);

    if (crewIndex < currentIndex) return 'completed';
    if (crewIndex === currentIndex) return 'active';
    return 'pending';
  };

  const getCrewIcon = (crewName: string) => {
    const crewStatus = getCrewStatus(crewName);
    switch (crewStatus) {
      case 'completed':
        return <CheckCircle className="w-3 h-3" />;
      case 'active':
        return <Loader2 className="w-3 h-3 animate-spin" />;
      default:
        return <Circle className="w-3 h-3" />;
    }
  };

  const getCrewVariant = (crewName: string): 'default' | 'secondary' | 'outline' => {
    const crewStatus = getCrewStatus(crewName);
    switch (crewStatus) {
      case 'completed':
        return 'default';
      case 'active':
        return 'secondary';
      default:
        return 'outline';
    }
  };

  return (
    <Card>
      <CardContent className="pt-6 space-y-4">
        <div className="space-y-2">
          <div className="flex justify-between items-center text-sm">
            <span className="font-medium">Pipeline Progress</span>
            <span className="text-muted-foreground">{Math.round(progress)}%</span>
          </div>
          <Progress value={progress} className="h-2" />
        </div>

        <div className="grid grid-cols-2 gap-2">
          {CREWS.map(crew => (
            <Badge
              key={crew.name}
              variant={getCrewVariant(crew.name)}
              className="justify-start gap-2 py-2"
            >
              {getCrewIcon(crew.name)}
              <span className="text-xs">{crew.name}</span>
            </Badge>
          ))}
        </div>

        {currentCrew && status === 'running' && (
          <div className="text-xs text-muted-foreground text-center pt-2 border-t">
            {CREWS.find(c => c.name === currentCrew)?.description}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
