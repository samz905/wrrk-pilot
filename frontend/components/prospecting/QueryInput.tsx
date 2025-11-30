'use client';

import { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Search, Loader2, Square } from 'lucide-react';

interface QueryInputProps {
  onStart: (query: string) => void;
  onStop?: () => void;
  isLoading: boolean;
}

export function QueryInput({ onStart, onStop, isLoading }: QueryInputProps) {
  const [query, setQuery] = useState('');

  const handleSubmit = () => {
    if (query.trim()) {
      onStart(query);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && query.trim() && !isLoading) {
      handleSubmit();
    }
  };

  return (
    <div className="flex items-center gap-3 w-full">
      <Input
        placeholder="find me leads for my CRM software"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={isLoading}
        className="flex-1 h-11"
      />

      {isLoading ? (
        <>
          {/* Running indicator */}
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Running...</span>
          </div>

          {/* Stop button */}
          <Button
            onClick={onStop}
            variant="destructive"
            size="default"
            className="h-11 px-6"
          >
            <Square className="w-4 h-4 mr-2" />
            Stop
          </Button>
        </>
      ) : (
        <Button
          onClick={handleSubmit}
          disabled={!query.trim()}
          size="default"
          className="h-11 px-6"
        >
          <Search className="w-4 h-4 mr-2" />
          Start
        </Button>
      )}
    </div>
  );
}
