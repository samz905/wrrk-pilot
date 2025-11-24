'use client';

import { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Search, Loader2 } from 'lucide-react';

interface QueryInputProps {
  onStart: (query: string, maxLeads: number) => void;
  isLoading: boolean;
}

export function QueryInput({ onStart, isLoading }: QueryInputProps) {
  const [query, setQuery] = useState('');

  const handleSubmit = () => {
    if (query.trim()) {
      onStart(query, 10); // Default to 10 leads
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && query.trim()) {
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
      <Button
        onClick={handleSubmit}
        disabled={!query.trim() || isLoading}
        size="default"
        className="h-11 px-6"
      >
        {isLoading ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            Searching...
          </>
        ) : (
          <>
            <Search className="w-4 h-4 mr-2" />
            Start
          </>
        )}
      </Button>
    </div>
  );
}
