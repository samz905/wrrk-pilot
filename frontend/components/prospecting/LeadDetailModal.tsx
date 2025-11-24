'use client';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription
} from '@/components/ui/dialog';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Lead } from '@/lib/types';
import { Mail, Linkedin, Twitter, Globe, TrendingUp, Target, Zap } from 'lucide-react';

interface LeadDetailModalProps {
  lead: Lead | null;
  isOpen: boolean;
  onClose: () => void;
}

export function LeadDetailModal({ lead, isOpen, onClose }: LeadDetailModalProps) {
  if (!lead) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between gap-4">
            <span className="text-2xl">{lead.name}</span>
            <Badge
              variant={
                lead.priority === 'HOT' ? 'destructive' :
                lead.priority === 'WARM' ? 'default' : 'secondary'
              }
              className="text-lg px-4 py-1"
            >
              {lead.priority} • {lead.score}
            </Badge>
          </DialogTitle>
          <DialogDescription>
            {lead.title} at {lead.company}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 pt-4">
          {/* Contact Information */}
          <Card className="p-6">
            <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
              <Mail className="w-5 h-5" />
              Contact Information
            </h3>
            <dl className="space-y-3">
              <div className="flex items-start gap-2">
                <dt className="font-medium min-w-[120px] text-muted-foreground">Title:</dt>
                <dd>{lead.title}</dd>
              </div>
              <div className="flex items-start gap-2">
                <dt className="font-medium min-w-[120px] text-muted-foreground">Company:</dt>
                <dd>{lead.company}</dd>
              </div>
              <div className="flex items-start gap-2">
                <dt className="font-medium min-w-[120px] text-muted-foreground">Domain:</dt>
                <dd className="flex items-center gap-1">
                  <Globe className="w-4 h-4" />
                  {lead.domain}
                </dd>
              </div>
              {lead.contact.email && (
                <div className="flex items-start gap-2">
                  <dt className="font-medium min-w-[120px] text-muted-foreground">Email:</dt>
                  <dd className="flex items-center gap-1">
                    <Mail className="w-4 h-4" />
                    <a href={`mailto:${lead.contact.email}`} className="text-blue-600 hover:underline">
                      {lead.contact.email}
                    </a>
                  </dd>
                </div>
              )}
              {lead.contact.linkedin && (
                <div className="flex items-start gap-2">
                  <dt className="font-medium min-w-[120px] text-muted-foreground">LinkedIn:</dt>
                  <dd className="flex items-center gap-1">
                    <Linkedin className="w-4 h-4" />
                    <a href={`https://${lead.contact.linkedin}`} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                      View Profile
                    </a>
                  </dd>
                </div>
              )}
              {lead.contact.twitter && (
                <div className="flex items-start gap-2">
                  <dt className="font-medium min-w-[120px] text-muted-foreground">Twitter:</dt>
                  <dd className="flex items-center gap-1">
                    <Twitter className="w-4 h-4" />
                    <a href={`https://twitter.com/${lead.contact.twitter.replace('@', '')}`} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                      {lead.contact.twitter}
                    </a>
                  </dd>
                </div>
              )}
              <div className="flex items-start gap-2">
                <dt className="font-medium min-w-[120px] text-muted-foreground">Tier:</dt>
                <dd>
                  <Badge variant="outline">
                    Tier {lead.tier} ({lead.platforms_found.length} {lead.platforms_found.length === 1 ? 'platform' : 'platforms'})
                  </Badge>
                </dd>
              </div>
              <div className="flex items-start gap-2">
                <dt className="font-medium min-w-[120px] text-muted-foreground">Recency:</dt>
                <dd>{lead.recency}</dd>
              </div>
            </dl>
          </Card>

          {/* ICP Fit Score */}
          <Card className="p-6">
            <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
              <Target className="w-5 h-5" />
              ICP Fit Score: {lead.fit_score}/100
            </h3>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between mb-2">
                  <span className="text-sm font-medium">Title Score</span>
                  <span className="text-sm font-bold">{lead.icp_match.title_score}/50</span>
                </div>
                <Progress value={(lead.icp_match.title_score / 50) * 100} className="h-2" />
                <p className="text-xs text-muted-foreground mt-1">
                  Authority level and decision-making power
                </p>
              </div>

              <div>
                <div className="flex justify-between mb-2">
                  <span className="text-sm font-medium">Industry Score</span>
                  <span className="text-sm font-bold">{lead.icp_match.industry_score}/25</span>
                </div>
                <Progress value={(lead.icp_match.industry_score / 25) * 100} className="h-2" />
                <p className="text-xs text-muted-foreground mt-1">
                  Company industry and market fit
                </p>
              </div>

              <div>
                <div className="flex justify-between mb-2">
                  <span className="text-sm font-medium">Signals Score</span>
                  <span className="text-sm font-bold">{lead.icp_match.signals_score}/25</span>
                </div>
                <Progress value={(lead.icp_match.signals_score / 25) * 100} className="h-2" />
                <p className="text-xs text-muted-foreground mt-1">
                  Buying intent and pain point signals
                </p>
              </div>
            </div>
          </Card>

          {/* Match Reason */}
          <Card className="p-6 bg-blue-50 border-blue-200">
            <h3 className="font-semibold text-lg mb-3 flex items-center gap-2">
              <TrendingUp className="w-5 h-5" />
              Why This Lead Matters
            </h3>
            <p className="text-sm leading-relaxed text-blue-900">
              {lead.match_reason}
            </p>
          </Card>

          {/* Intent Signals */}
          <Card className="p-6">
            <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
              <Zap className="w-5 h-5" />
              Intent Signals
            </h3>
            <div className="space-y-3">
              {lead.intent_signals.map((signal, idx) => (
                <div key={idx} className="flex gap-3 items-start p-3 bg-gray-50 rounded-lg border">
                  <Badge variant="outline" className="flex-shrink-0">
                    {signal.platform}
                  </Badge>
                  <p className="text-sm leading-relaxed">
                    "{signal.signal}"
                  </p>
                </div>
              ))}
            </div>

            <div className="mt-4 pt-4 border-t">
              <div className="flex gap-2 flex-wrap">
                <span className="text-sm font-medium">Found on:</span>
                {lead.platforms_found.map(platform => (
                  <Badge key={platform} variant="secondary">
                    {platform}
                  </Badge>
                ))}
              </div>
            </div>
          </Card>

          {/* Final Score Breakdown */}
          <Card className="p-6">
            <h3 className="font-semibold text-lg mb-4">Final Score Breakdown</h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between p-2 rounded hover:bg-gray-50">
                <dt className="text-muted-foreground">ICP Contribution:</dt>
                <dd className="font-semibold">{lead.final_score_breakdown.icp_contribution} pts</dd>
              </div>
              <div className="flex justify-between p-2 rounded hover:bg-gray-50">
                <dt className="text-muted-foreground">Platform Diversity (Tier {lead.tier}):</dt>
                <dd className="font-semibold">{lead.final_score_breakdown.platform_diversity} pts</dd>
              </div>
              <div className="flex justify-between p-2 rounded hover:bg-gray-50">
                <dt className="text-muted-foreground">Contact Quality:</dt>
                <dd className="font-semibold">{lead.final_score_breakdown.contact_quality} pts</dd>
              </div>
              <div className="flex justify-between p-2 rounded hover:bg-gray-50">
                <dt className="text-muted-foreground">Intent Strength:</dt>
                <dd className="font-semibold">{lead.final_score_breakdown.intent_strength} pts</dd>
              </div>
              <div className="flex justify-between p-2 rounded hover:bg-gray-50">
                <dt className="text-muted-foreground">Data Completeness:</dt>
                <dd className="font-semibold">{lead.final_score_breakdown.data_completeness} pts</dd>
              </div>
              <div className="flex justify-between p-3 rounded bg-blue-50 border border-blue-200 mt-2">
                <dt className="font-bold">Total Score:</dt>
                <dd className="font-bold text-lg">{lead.score}/100</dd>
              </div>
            </dl>
          </Card>

          {/* Recommended Action */}
          <Card className="p-6 bg-green-50 border-green-200">
            <h3 className="font-semibold text-lg mb-3">Recommended Action</h3>
            <p className="text-sm leading-relaxed text-green-900">
              {lead.recommended_action}
            </p>
          </Card>
        </div>
      </DialogContent>
    </Dialog>
  );
}
