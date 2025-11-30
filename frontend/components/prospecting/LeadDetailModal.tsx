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
import { Lead } from '@/lib/types';
import { Mail, Linkedin, User, Building2, Zap } from 'lucide-react';

interface LeadDetailModalProps {
  lead: Lead | null;
  isOpen: boolean;
  onClose: () => void;
}

export function LeadDetailModal({ lead, isOpen, onClose }: LeadDetailModalProps) {
  if (!lead) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
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
            {lead.title ? `${lead.title}${lead.company ? ` at ${lead.company}` : ''}` : lead.company || 'No title or company'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 pt-4">
          {/* Contact Information */}
          <Card className="p-6">
            <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
              <User className="w-5 h-5" />
              Contact Information
            </h3>
            <dl className="space-y-3">
              {lead.title && (
                <div className="flex items-start gap-2">
                  <dt className="font-medium min-w-[120px] text-muted-foreground">Title:</dt>
                  <dd>{lead.title}</dd>
                </div>
              )}
              {lead.company && (
                <div className="flex items-start gap-2">
                  <dt className="font-medium min-w-[120px] text-muted-foreground">Company:</dt>
                  <dd className="flex items-center gap-1">
                    <Building2 className="w-4 h-4" />
                    {lead.company}
                  </dd>
                </div>
              )}
              {lead.username && (
                <div className="flex items-start gap-2">
                  <dt className="font-medium min-w-[120px] text-muted-foreground">Username:</dt>
                  <dd>@{lead.username}</dd>
                </div>
              )}
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
                    <a href={lead.contact.linkedin} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                      View Profile
                    </a>
                  </dd>
                </div>
              )}
              {lead.user_type && (
                <div className="flex items-start gap-2">
                  <dt className="font-medium min-w-[120px] text-muted-foreground">User Type:</dt>
                  <dd>
                    <Badge variant="outline">{lead.user_type}</Badge>
                  </dd>
                </div>
              )}
            </dl>
          </Card>

          {/* Intent Signal */}
          {lead.intent_signal && (
            <Card className="p-6 bg-blue-50 border-blue-200">
              <h3 className="font-semibold text-lg mb-3 flex items-center gap-2">
                <Zap className="w-5 h-5" />
                Intent Signal
              </h3>
              <p className="text-sm leading-relaxed text-blue-900">
                {lead.intent_signal}
              </p>
            </Card>
          )}

          {/* Source Information */}
          <Card className="p-6">
            <h3 className="font-semibold text-lg mb-4">Source Information</h3>
            <div className="space-y-4">
              {lead.source_platform && (
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-muted-foreground">Primary Source:</span>
                  <Badge
                    variant="outline"
                    className={
                      lead.source_platform === 'reddit' ? 'bg-orange-100 text-orange-800' :
                      lead.source_platform === 'techcrunch' ? 'bg-green-100 text-green-800' :
                      lead.source_platform === 'linkedin' ? 'bg-blue-100 text-blue-800' : ''
                    }
                  >
                    {lead.source_platform}
                  </Badge>
                </div>
              )}
              {lead.platforms_found.length > 0 && (
                <div className="flex gap-2 flex-wrap items-center">
                  <span className="text-sm font-medium text-muted-foreground">Found on:</span>
                  {lead.platforms_found.map(platform => (
                    <Badge key={platform} variant="secondary">
                      {platform}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          </Card>

          {/* Score */}
          <Card className="p-6">
            <h3 className="font-semibold text-lg mb-4">Lead Score</h3>
            <div className="flex justify-between p-3 rounded bg-blue-50 border border-blue-200">
              <span className="font-bold">Intent Score:</span>
              <span className="font-bold text-lg">{lead.score}/100</span>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              {lead.priority === 'HOT' && 'High-priority lead with strong buying signals'}
              {lead.priority === 'WARM' && 'Good potential lead worth following up'}
              {lead.priority === 'COLD' && 'Lower priority, may need nurturing'}
            </p>
          </Card>
        </div>
      </DialogContent>
    </Dialog>
  );
}
