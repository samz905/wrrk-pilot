'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import { Header } from '@/components/layout/Header'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { LeadsTable } from '@/components/prospecting/LeadsTable'
import { LeadDetailModal } from '@/components/prospecting/LeadDetailModal'
import { format } from 'date-fns'
import { Download, Loader2, Users, MessageSquare, Building2, Target } from 'lucide-react'
import { transformLead, type Lead } from '@/lib/types'

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

export default function RunDetailsPage() {
  const params = useParams()
  const runId = params.id as string

  const [run, setRun] = useState<Run | null>(null)
  const [leads, setLeads] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null)
  const [exporting, setExporting] = useState(false)

  const supabase = createClient()

  useEffect(() => {
    const fetchRunDetails = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession()
        if (!session) {
          setError('Not authenticated')
          return
        }

        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/prospect/runs/${runId}`,
          {
            headers: {
              'Authorization': `Bearer ${session.access_token}`,
            },
          }
        )

        if (!response.ok) {
          throw new Error('Failed to fetch run details')
        }

        const data = await response.json()
        setRun(data.run)
        // Transform leads from database format to frontend format
        const transformedLeads = (data.leads || []).map(transformLead)
        setLeads(transformedLeads)
      } catch (err: any) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchRunDetails()
  }, [runId, supabase.auth])

  const handleExport = async () => {
    setExporting(true)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) throw new Error('Not authenticated')

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/prospect/runs/${runId}/export`,
        {
          headers: {
            'Authorization': `Bearer ${session.access_token}`,
          },
        }
      )

      if (!response.ok) throw new Error('Export failed')

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `leads_${runId.slice(0, 8)}.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err: any) {
      console.error('Export error:', err)
    } finally {
      setExporting(false)
    }
  }

  const formatDuration = (seconds: number) => {
    if (!seconds) return '-'
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-zinc-900 via-zinc-800 to-zinc-900">
        <Header showBackToRuns />
        <div className="flex items-center justify-center py-24">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        </div>
      </div>
    )
  }

  if (error || !run) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-zinc-900 via-zinc-800 to-zinc-900">
        <Header showBackToRuns />
        <main className="container mx-auto px-4 py-8">
          <Card className="p-6 bg-red-900/20 border-red-800">
            <p className="text-red-400">{error || 'Run not found'}</p>
          </Card>
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-zinc-900 via-zinc-800 to-zinc-900">
      <Header showBackToRuns />

      <main className="container mx-auto px-4 py-8">
        {/* Query Title */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-white mb-2">{run.query}</h1>
          <div className="flex items-center gap-4 text-sm text-zinc-400">
            <span>{format(new Date(run.created_at), 'MMMM d, yyyy h:mm a')}</span>
            <span>•</span>
            <span>{formatDuration(run.duration_seconds)}</span>
            <span>•</span>
            <span className="capitalize">{run.status}</span>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <Card className="p-4 bg-zinc-900/50 border-zinc-700">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-500/20">
                <Users className="h-5 w-5 text-blue-400" />
              </div>
              <div>
                <div className="text-2xl font-bold text-white">{run.total_leads || 0}</div>
                <div className="text-xs text-zinc-500">Total Leads</div>
              </div>
            </div>
          </Card>

          <Card className="p-4 bg-zinc-900/50 border-zinc-700">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-orange-500/20">
                <Target className="h-5 w-5 text-orange-400" />
              </div>
              <div>
                <div className="text-2xl font-bold text-white">{run.techcrunch_leads || 0}</div>
                <div className="text-xs text-zinc-500">TechCrunch</div>
              </div>
            </div>
          </Card>

          <Card className="p-4 bg-zinc-900/50 border-zinc-700">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-purple-500/20">
                <Building2 className="h-5 w-5 text-purple-400" />
              </div>
              <div>
                <div className="text-2xl font-bold text-white">{run.competitor_leads || 0}</div>
                <div className="text-xs text-zinc-500">Competitor</div>
              </div>
            </div>
          </Card>

          <Card className="p-4 bg-zinc-900/50 border-zinc-700">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-red-500/20">
                <MessageSquare className="h-5 w-5 text-red-400" />
              </div>
              <div>
                <div className="text-2xl font-bold text-white">{run.reddit_leads || 0}</div>
                <div className="text-xs text-zinc-500">Reddit</div>
              </div>
            </div>
          </Card>
        </div>

        {/* Export Button */}
        <div className="flex justify-end mb-4">
          <Button
            onClick={handleExport}
            disabled={exporting || leads.length === 0}
            className="bg-zinc-800 hover:bg-zinc-700 text-white"
          >
            {exporting ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : (
              <Download className="h-4 w-4 mr-2" />
            )}
            Export CSV
          </Button>
        </div>

        {/* Leads Table */}
        {leads.length > 0 ? (
          <Card className="bg-zinc-900/50 border-zinc-700 overflow-hidden">
            <LeadsTable leads={leads} onLeadClick={setSelectedLead} />
          </Card>
        ) : (
          <Card className="p-8 bg-zinc-900/50 border-zinc-700 text-center">
            <Users className="h-12 w-12 text-zinc-600 mx-auto mb-4" />
            <p className="text-zinc-400">No leads found for this run</p>
          </Card>
        )}
      </main>

      {/* Lead Detail Modal */}
      <LeadDetailModal
        lead={selectedLead}
        isOpen={!!selectedLead}
        onClose={() => setSelectedLead(null)}
      />
    </div>
  )
}
