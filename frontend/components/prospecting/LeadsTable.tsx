'use client';

import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  SortingState,
  ColumnDef,
  flexRender
} from '@tanstack/react-table';
import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Lead } from '@/lib/types';
import { CheckCircle, XCircle, ArrowUpDown, Users } from 'lucide-react';

interface LeadsTableProps {
  leads: Lead[];
  onLeadClick: (lead: Lead) => void;
  highlightedLeads?: string[]; // Names of newly added leads to highlight
}

const columns: ColumnDef<Lead>[] = [
  {
    accessorKey: 'priority',
    header: 'Priority',
    cell: ({ row }) => {
      const priority = row.original.priority;
      return (
        <Badge
          variant={
            priority === 'HOT' ? 'destructive' :
            priority === 'WARM' ? 'default' : 'secondary'
          }
          className="font-semibold"
        >
          {priority}
        </Badge>
      );
    }
  },
  {
    accessorKey: 'score',
    header: ({ column }) => {
      return (
        <button
          className="flex items-center gap-1 hover:text-foreground"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        >
          Score
          <ArrowUpDown className="w-3 h-3" />
        </button>
      );
    },
    cell: ({ row }) => (
      <div className="font-bold text-lg">{row.original.score}</div>
    )
  },
  {
    accessorKey: 'name',
    header: 'Name',
    cell: ({ row }) => (
      <div className="font-medium">{row.original.name}</div>
    )
  },
  {
    accessorKey: 'title',
    header: 'Title',
    cell: ({ row }) => (
      <div className="text-sm text-muted-foreground max-w-[200px] truncate">
        {row.original.title || '-'}
      </div>
    )
  },
  {
    accessorKey: 'company',
    header: 'Company',
    cell: ({ row }) => (
      <div className="font-medium">{row.original.company || '-'}</div>
    )
  },
  {
    accessorKey: 'contact.linkedin',
    header: 'LinkedIn',
    cell: ({ row }) => (
      row.original.contact?.linkedin ? (
        <CheckCircle className="w-4 h-4 text-green-600" />
      ) : (
        <XCircle className="w-4 h-4 text-gray-300" />
      )
    )
  },
  {
    accessorKey: 'source_platform',
    header: 'Source',
    cell: ({ row }) => {
      const platform = row.original.source_platform;
      const colors: Record<string, string> = {
        reddit: 'bg-orange-100 text-orange-800',
        techcrunch: 'bg-green-100 text-green-800',
        linkedin: 'bg-blue-100 text-blue-800',
      };
      return (
        <Badge variant="outline" className={`text-xs ${colors[platform || ''] || ''}`}>
          {platform || 'unknown'}
        </Badge>
      );
    }
  },
  {
    accessorKey: 'intent_signal',
    header: 'Signal',
    cell: ({ row }) => (
      <div className="text-sm text-muted-foreground max-w-[200px] truncate" title={row.original.intent_signal}>
        {row.original.intent_signal || '-'}
      </div>
    )
  }
];

export function LeadsTable({ leads, onLeadClick, highlightedLeads = [] }: LeadsTableProps) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'score', desc: true } // Default sort by score descending
  ]);

  const isHighlighted = (leadName: string) => highlightedLeads.includes(leadName);

  const table = useReactTable({
    data: leads,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onSortingChange: setSorting,
    state: {
      sorting
    }
  });

  if (leads.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="w-5 h-5" />
            Results
          </CardTitle>
          <CardDescription>
            Top qualified leads will appear here
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-64 text-muted-foreground">
            <p>No leads yet. Start a prospecting search to see results.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 justify-between">
          <div className="flex items-center gap-2">
            <Users className="w-5 h-5" />
            Results
          </div>
          <Badge variant="outline" className="text-sm">
            {leads.length} leads
          </Badge>
        </CardTitle>
        <CardDescription>
          Top {leads.length} qualified leads ranked by score
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              {table.getHeaderGroups().map(headerGroup => (
                <TableRow key={headerGroup.id}>
                  {headerGroup.headers.map(header => (
                    <TableHead key={header.id}>
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                    </TableHead>
                  ))}
                </TableRow>
              ))}
            </TableHeader>
            <TableBody>
              {table.getRowModel().rows.map(row => (
                <TableRow
                  key={row.id}
                  onClick={() => onLeadClick(row.original)}
                  className={`cursor-pointer hover:bg-muted/50 transition-all duration-300 ${
                    isHighlighted(row.original.name)
                      ? 'bg-yellow-50 animate-in fade-in'
                      : ''
                  }`}
                >
                  {row.getVisibleCells().map(cell => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
