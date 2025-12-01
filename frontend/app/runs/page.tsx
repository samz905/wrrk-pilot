'use client'

import { useEffect, useState, useMemo } from 'react'
import Link from 'next/link'
import { createClient } from '@/lib/supabase/client'
import { Header } from '@/components/layout/Header'
import { Card } from '@/components/ui/card'
import { format } from 'date-fns'
import { CheckCircle, XCircle, Loader2, ChevronRight, Users } from 'lucide-react'

interface Run {
  id: string
  query: string
  status: string
  max_leads: number
  total_leads: number
  reddit_leads: number
  techcrunch_leads: number
  competitor_leads: number
  duration_seconds: number
  created_at: string
  completed_at: string | null
  error: string | null
}

export default function RunsPage() {
  const [runs, setRuns] = useState<Run[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const supabase = useMemo(() => createClient(), [])

  useEffect(() => {
    const fetchRuns = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession()
        if (!session) {
          setError('Not authenticated')
          setLoading(false)
          return
        }

        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
        const response = await fetch(
          `${apiUrl}/prospect/runs`,
          {
            headers: {
              'Authorization': `Bearer ${session.access_token}`,
            },
          }
        )

        if (!response.ok) {
          throw new Error('Failed to fetch runs')
        }

        const data = await response.json()
        setRuns(data.runs || [])
      } catch (err: any) {
        console.error('Error fetching runs:', err)
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchRuns()
  }, [supabase])

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />
      case 'running':
        return <Loader2 className="h-5 w-5 text-yellow-500 animate-spin" />
      default:
        return <Loader2 className="h-5 w-5 text-zinc-500" />
    }
  }

  const formatDuration = (seconds: number) => {
    if (!seconds) return '-'
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-zinc-900 via-zinc-800 to-zinc-900">
      <Header showNewSearch />

      <main className="container mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold text-white mb-6">Your Prospecting Runs</h1>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
          </div>
        ) : error ? (
          <Card className="p-6 bg-red-900/20 border-red-800">
            <p className="text-red-400">{error}</p>
          </Card>
        ) : runs.length === 0 ? (
          <Card className="p-8 bg-zinc-900/50 border-zinc-700 text-center">
            <Users className="h-12 w-12 text-zinc-600 mx-auto mb-4" />
            <h2 className="text-lg font-medium text-white mb-2">No runs yet</h2>
            <p className="text-zinc-400 mb-4">
              Start your first prospecting search to find high-intent leads.
            </p>
            <Link
              href="/"
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              Start Searching
              <ChevronRight className="h-4 w-4" />
            </Link>
          </Card>
        ) : (
          <div className="space-y-3">
            {runs.map((run) => (
              <Link key={run.id} href={`/runs/${run.id}`}>
                <Card className="p-4 bg-zinc-900/50 border-zinc-700 hover:border-zinc-600 hover:bg-zinc-900/70 transition-all cursor-pointer group">
                  <div className="flex items-center gap-4">
                    {getStatusIcon(run.status)}

                    <div className="flex-1 min-w-0">
                      <h3 className="text-white font-medium truncate group-hover:text-blue-400 transition-colors">
                        {run.query}
                      </h3>
                      <div className="flex items-center gap-2 text-sm text-zinc-400 mt-1">
                        <span className="capitalize">{run.status}</span>
                        <span>•</span>
                        <span>{format(new Date(run.created_at), 'MMM d, yyyy')}</span>
                        {run.duration_seconds > 0 && (
                          <>
                            <span>•</span>
                            <span>{formatDuration(run.duration_seconds)}</span>
                          </>
                        )}
                      </div>
                    </div>

                    <div className="text-right">
                      <div className="text-lg font-semibold text-white">
                        {run.total_leads || 0}
                      </div>
                      <div className="text-xs text-zinc-500">leads</div>
                    </div>

                    <ChevronRight className="h-5 w-5 text-zinc-600 group-hover:text-zinc-400 transition-colors" />
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
