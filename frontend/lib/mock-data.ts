/**
 * Mock data for CRM software demo - simulates realistic prospecting with incremental lead extraction
 * NEW FLOW: Multi-tool usage with intelligent reasoning connecting sources
 */

import { Lead, ActivityEvent } from './types';

// Reorganized batches to match discovery story
// BATCH 1: Direct from Reddit (2 leads)
export const MOCK_LEADS_BATCH_1: Lead[] = [
  {
    score: 94,
    priority: 'HOT',
    name: 'Marcus Johnson',
    title: 'VP of Sales',
    company: 'SalesForce Analytics',
    contact: {
      email: 'marcus.j@salesforceanalytics.com',
      linkedin: 'linkedin.com/in/marcusjohnson'
    },
    fit_score: 92,
    icp_match: {
      title_score: 50,
      industry_score: 25,
      signals_score: 25
    },
    final_score_breakdown: {
      icp_contribution: 38,
      platform_diversity: 15,
      contact_quality: 20,
      intent_strength: 15,
      data_completeness: 6
    },
    match_reason: 'VP of Sales actively complaining about current CRM limitations on Reddit. Posted detailed list of pain points including "manual data entry killing our productivity" and "lack of AI insights". High authority decision-maker with urgent need.',
    intent_signals: [
      { platform: 'Reddit', signal: 'Posted "Our CRM is terrible - what alternatives exist?" in r/sales 2 days ago' },
      { platform: 'Reddit', signal: 'Comment: "Manual data entry is killing our team\'s productivity" 2 days ago' }
    ],
    platforms_found: ['Reddit', 'LinkedIn', 'Twitter'],
    recency: '2 days ago',
    domain: 'salesforceanalytics.com',
    recommended_action: 'IMMEDIATE outreach - respond to Reddit post with value, then connect on LinkedIn',
    tier: 1
  },
  {
    score: 86,
    priority: 'HOT',
    name: 'David Torres',
    title: 'Head of Sales',
    company: 'CloudScale Solutions',
    contact: {
      linkedin: 'linkedin.com/in/davidtorres'
    },
    fit_score: 84,
    icp_match: {
      title_score: 45,
      industry_score: 25,
      signals_score: 20
    },
    final_score_breakdown: {
      icp_contribution: 34,
      platform_diversity: 15,
      contact_quality: 10,
      intent_strength: 15,
      data_completeness: 12
    },
    match_reason: 'Head of Sales expressing frustration with current CRM on multiple platforms. Reddit post about "CRM migration nightmare" and Twitter thread about lost deals due to CRM data issues. Strong pain signals.',
    intent_signals: [
      { platform: 'Reddit', signal: 'Asked "Has anyone successfully migrated from Salesforce?" in r/sales' },
      { platform: 'Twitter', signal: 'Tweeted: "Just lost a deal because our CRM didn\'t sync properly"' }
    ],
    platforms_found: ['Reddit', 'Twitter', 'LinkedIn'],
    recency: '3 days ago',
    domain: 'cloudscale.io',
    recommended_action: 'Immediate follow-up - address migration concerns and data sync reliability',
    tier: 2
  }
];

// BATCH 2: From LinkedIn Round 1 (1 lead)
export const MOCK_LEADS_BATCH_2: Lead[] = [
  {
    score: 89,
    priority: 'HOT',
    name: 'Rachel Kim',
    title: 'Chief Revenue Officer',
    company: 'GrowthMetrics Inc',
    contact: {
      email: 'rachel@growthmetrics.io',
      linkedin: 'linkedin.com/in/rachelkim'
    },
    fit_score: 88,
    icp_match: {
      title_score: 50,
      industry_score: 25,
      signals_score: 20
    },
    final_score_breakdown: {
      icp_contribution: 36,
      platform_diversity: 15,
      contact_quality: 20,
      intent_strength: 12,
      data_completeness: 6
    },
    match_reason: 'CRO at fast-growing SaaS company. Google search shows company just raised Series B and is scaling sales team 3x. LinkedIn shows she posted job opening for "Director of Sales Operations" mentioning need for better CRM infrastructure.',
    intent_signals: [
      { platform: 'Google', signal: 'Company announced $30M Series B funding 1 week ago' },
      { platform: 'LinkedIn', signal: 'Posted job for "Director of Sales Ops - CRM expertise required"' }
    ],
    platforms_found: ['LinkedIn', 'Google'],
    recency: '1 week ago',
    domain: 'growthmetrics.io',
    recommended_action: 'High priority - reference funding round and sales team expansion',
    tier: 1
  }
];

// BATCH 3: From LinkedIn Round 2 (2 leads)
export const MOCK_LEADS_BATCH_3: Lead[] = [
  {
    score: 82,
    priority: 'HOT',
    name: 'Jennifer Martinez',
    title: 'Sales Director',
    company: 'TechVentures Corp',
    contact: {
      email: 'j.martinez@techventures.com',
      linkedin: 'linkedin.com/in/jennifermartinez'
    },
    fit_score: 80,
    icp_match: {
      title_score: 45,
      industry_score: 20,
      signals_score: 20
    },
    final_score_breakdown: {
      icp_contribution: 32,
      platform_diversity: 10,
      contact_quality: 20,
      intent_strength: 12,
      data_completeness: 8
    },
    match_reason: 'Sales Director at mid-market B2B company. LinkedIn activity shows she\'s actively researching CRM solutions and engaging with CRM-related content. Company LinkedIn page announced sales team expansion.',
    intent_signals: [
      { platform: 'LinkedIn', signal: 'Liked and commented on "Top CRM features for 2025" article' },
      { platform: 'LinkedIn', signal: 'Company page announced doubling sales team size' }
    ],
    platforms_found: ['LinkedIn'],
    recency: '5 days ago',
    domain: 'techventures.com',
    recommended_action: 'Engage with relevant content first, then personalized outreach',
    tier: 2
  },
  {
    score: 78,
    priority: 'WARM',
    name: 'Alex Patel',
    title: 'VP of Revenue Operations',
    company: 'SalesOps Pro',
    contact: {
      email: 'alex@salesopspro.io',
      linkedin: 'linkedin.com/in/alexpatel'
    },
    fit_score: 76,
    icp_match: {
      title_score: 50,
      industry_score: 15,
      signals_score: 15
    },
    final_score_breakdown: {
      icp_contribution: 30,
      platform_diversity: 15,
      contact_quality: 20,
      intent_strength: 9,
      data_completeness: 4
    },
    match_reason: 'VP RevOps with strong authority. Twitter activity shows interest in AI-powered CRM capabilities. Google shows company is growing rapidly and hiring for sales roles.',
    intent_signals: [
      { platform: 'Twitter', signal: 'Tweeted asking about "AI features in modern CRMs"' },
      { platform: 'Google', signal: 'Company hiring 5+ sales positions this quarter' }
    ],
    platforms_found: ['Twitter', 'LinkedIn', 'Google'],
    recency: '1 week ago',
    domain: 'salesopspro.io',
    recommended_action: 'Emphasize AI capabilities and automation features',
    tier: 1
  }
];

// BATCH 4: From Twitter + Reddit validation (2 leads)
export const MOCK_LEADS_BATCH_4: Lead[] = [
  {
    score: 75,
    priority: 'WARM',
    name: 'Sarah O\'Connor',
    title: 'CEO',
    company: 'StartupBoost',
    contact: {
      linkedin: 'linkedin.com/in/sarahoconnor'
    },
    fit_score: 72,
    icp_match: {
      title_score: 50,
      industry_score: 15,
      signals_score: 12
    },
    final_score_breakdown: {
      icp_contribution: 29,
      platform_diversity: 15,
      contact_quality: 8,
      intent_strength: 12,
      data_completeness: 11
    },
    match_reason: 'CEO of early-stage startup (Series A). Twitter activity shows frustration with current sales tools. High authority but smaller deal size. Recently hired first VP of Sales per LinkedIn.',
    intent_signals: [
      { platform: 'Twitter', signal: 'Tweeted: "Why do all CRMs feel like they\'re built for enterprises?"' },
      { platform: 'LinkedIn', signal: 'Announced hiring VP of Sales 2 weeks ago' }
    ],
    platforms_found: ['Twitter', 'LinkedIn'],
    recency: '4 days ago',
    domain: 'startupboost.io',
    recommended_action: 'Position as startup-friendly solution, quick time-to-value',
    tier: 3
  },
  {
    score: 67,
    priority: 'WARM',
    name: 'Lisa Wang',
    title: 'Head of Business Development',
    company: 'GrowthEngine',
    contact: {
      linkedin: 'linkedin.com/in/lisawang'
    },
    fit_score: 65,
    icp_match: {
      title_score: 40,
      industry_score: 20,
      signals_score: 10
    },
    final_score_breakdown: {
      icp_contribution: 26,
      platform_diversity: 15,
      contact_quality: 8,
      intent_strength: 12,
      data_completeness: 6
    },
    match_reason: 'Head of BD at growing consultancy. Twitter shows complaints about CRM reporting limitations. Reddit post asking about analytics-focused CRMs.',
    intent_signals: [
      { platform: 'Twitter', signal: 'Complained about "impossible to get useful reports from our CRM"' },
      { platform: 'Reddit', signal: 'Asked about CRMs with better analytics in r/sales' }
    ],
    platforms_found: ['Twitter', 'Reddit', 'LinkedIn'],
    recency: '1 week ago',
    domain: 'growthengine.com',
    recommended_action: 'Lead with analytics and reporting capabilities',
    tier: 2
  }
];

// BATCH 5: From LinkedIn Round 3 (2 leads)
export const MOCK_LEADS_BATCH_5: Lead[] = [
  {
    score: 71,
    priority: 'WARM',
    name: 'Michael Chen',
    title: 'Director of Sales Enablement',
    company: 'EnterpriseGrow',
    contact: {
      email: 'mchen@enterprisegrow.com',
      linkedin: 'linkedin.com/in/michaelchen'
    },
    fit_score: 68,
    icp_match: {
      title_score: 40,
      industry_score: 20,
      signals_score: 12
    },
    final_score_breakdown: {
      icp_contribution: 27,
      platform_diversity: 10,
      contact_quality: 20,
      intent_strength: 9,
      data_completeness: 5
    },
    match_reason: 'Director of Sales Enablement researching CRM integrations. LinkedIn shows active interest in sales tech stack. Influencer but may not be final decision-maker.',
    intent_signals: [
      { platform: 'LinkedIn', signal: 'Asked connections for "CRM + sales engagement platform" recommendations' }
    ],
    platforms_found: ['LinkedIn'],
    recency: '6 days ago',
    domain: 'enterprisegrow.com',
    recommended_action: 'Provide integration documentation and case studies',
    tier: 2
  },
  {
    score: 64,
    priority: 'WARM',
    name: 'James Rodriguez',
    title: 'Sales Operations Manager',
    company: 'B2B Dynamics',
    contact: {
      email: 'j.rodriguez@b2bdynamics.com',
      linkedin: 'linkedin.com/in/jamesrodriguez'
    },
    fit_score: 62,
    icp_match: {
      title_score: 35,
      industry_score: 20,
      signals_score: 10
    },
    final_score_breakdown: {
      icp_contribution: 24,
      platform_diversity: 10,
      contact_quality: 20,
      intent_strength: 6,
      data_completeness: 4
    },
    match_reason: 'Sales Ops Manager who influences CRM decisions. LinkedIn shows engagement with sales tech content. Good entry point to larger opportunity.',
    intent_signals: [
      { platform: 'LinkedIn', signal: 'Shared article about "Modern CRM requirements for 2025"' }
    ],
    platforms_found: ['LinkedIn'],
    recency: '1 week ago',
    domain: 'b2bdynamics.com',
    recommended_action: 'Nurture relationship, identify decision-maker',
    tier: 3
  }
];

// Combined array for reference
export const ALL_MOCK_LEADS = [
  ...MOCK_LEADS_BATCH_1,
  ...MOCK_LEADS_BATCH_2,
  ...MOCK_LEADS_BATCH_3,
  ...MOCK_LEADS_BATCH_4,
  ...MOCK_LEADS_BATCH_5
];

/**
 * Generates realistic event flow for CRM software demo with multi-tool usage
 * Total duration: ~95 seconds with realistic pauses and reasoning
 *
 * STORY: "Following the Breadcrumbs"
 * - Reddit (3x), LinkedIn (3x), Google (2x), Twitter (1x)
 * - 9 leads in 5 batches distributed throughout discovery
 */
export function generateCRMDemoEvents(): ActivityEvent[] {
  const now = Date.now();

  return [
    // === ACT 1: INITIAL DISCOVERY (0-16s) ===
    {
      type: 'thought',
      data: 'Initializing intelligent prospecting flow for CRM software...',
      timestamp: new Date(now),
      tool: undefined,
      leads: undefined
    },
    {
      type: 'thought',
      data: 'Query: find me leads for my CRM software',
      timestamp: new Date(now + 1000),
      tool: undefined,
      leads: undefined
    },
    {
      type: 'thought',
      data: 'Starting with Reddit to find high-intent discussions',
      timestamp: new Date(now + 2000),
      tool: undefined,
      leads: undefined
    },

    // REDDIT #1 START
    {
      type: 'tool_start',
      data: 'Scanning r/sales, r/crm, r/salesforce for CRM discussions',
      timestamp: new Date(now + 3000),
      tool: 'Reddit',
      leads: undefined
    },
    {
      type: 'thinking',
      data: 'Analyzing high-intent discussions...',
      timestamp: new Date(now + 4000),
      tool: 'Reddit',
      leads: undefined
    },
    {
      type: 'thought',
      data: 'Found discussion: "Our CRM is terrible - what alternatives exist?"',
      timestamp: new Date(now + 7000),
      tool: 'Reddit',
      leads: undefined
    },
    {
      type: 'thought',
      data: 'Thread has 47 comments with detailed pain points',
      timestamp: new Date(now + 8000),
      tool: 'Reddit',
      leads: undefined
    },
    {
      type: 'thinking',
      data: 'Extracting company names and user profiles...',
      timestamp: new Date(now + 9000),
      tool: 'Reddit',
      leads: undefined
    },
    {
      type: 'thought',
      data: 'Found 7 company names mentioned in discussion',
      timestamp: new Date(now + 12000),
      tool: 'Reddit',
      leads: undefined
    },
    {
      type: 'thought',
      data: '2 users are VP/Director level with detailed CRM complaints',
      timestamp: new Date(now + 13000),
      tool: 'Reddit',
      leads: undefined
    },
    {
      type: 'lead_batch',
      data: 'Extracted 2 high-intent leads from Reddit',
      timestamp: new Date(now + 15000),
      tool: 'Reddit',
      leads: MOCK_LEADS_BATCH_1
    },
    {
      type: 'tool_complete',
      data: 'Found 15 discussions, identified 7 companies with CRM pain',
      timestamp: new Date(now + 16000),
      tool: 'Reddit',
      leads: undefined
    },

    // === ACT 2: LINKEDIN INVESTIGATION ROUND 1 (17-31s) ===
    {
      type: 'thought',
      data: 'Scanning LinkedIn for decision-makers at these 7 companies',
      timestamp: new Date(now + 17000),
      tool: undefined,
      leads: undefined
    },

    // LINKEDIN #1 START
    {
      type: 'tool_start',
      data: 'Searching for VPs, CROs, Directors at identified companies',
      timestamp: new Date(now + 18000),
      tool: 'LinkedIn',
      leads: undefined
    },
    {
      type: 'thinking',
      data: 'Checking profiles at SalesForce Analytics, CloudScale, GrowthMetrics...',
      timestamp: new Date(now + 20000),
      tool: 'LinkedIn',
      leads: undefined
    },
    {
      type: 'thought',
      data: 'Found VPs at 3 of the 7 companies',
      timestamp: new Date(now + 23000),
      tool: 'LinkedIn',
      leads: undefined
    },
    {
      type: 'thought',
      data: 'GrowthMetrics posted job: "Director of Sales Ops - CRM expertise required"',
      timestamp: new Date(now + 25000),
      tool: 'LinkedIn',
      leads: undefined
    },
    {
      type: 'thinking',
      data: 'Enriching Rachel Kim\'s profile (CRO at GrowthMetrics)...',
      timestamp: new Date(now + 27000),
      tool: 'LinkedIn',
      leads: undefined
    },
    {
      type: 'lead_batch',
      data: 'Extracted 1 lead from LinkedIn',
      timestamp: new Date(now + 29000),
      tool: 'LinkedIn',
      leads: MOCK_LEADS_BATCH_2
    },
    {
      type: 'thought',
      data: 'Notice: GrowthMetrics actively hiring for CRM-focused role',
      timestamp: new Date(now + 30000),
      tool: 'LinkedIn',
      leads: undefined
    },
    {
      type: 'tool_complete',
      data: 'Screened 24 decision-makers across 7 companies',
      timestamp: new Date(now + 31000),
      tool: 'LinkedIn',
      leads: undefined
    },

    // === ACT 3: GOOGLE DEEP DIVE (32-46s) ===
    {
      type: 'thought',
      data: 'Researching GrowthMetrics and similar companies in Google',
      timestamp: new Date(now + 32000),
      tool: undefined,
      leads: undefined
    },

    // GOOGLE #1 START
    {
      type: 'tool_start',
      data: 'Searching for company triggers: funding, hiring, expansions',
      timestamp: new Date(now + 33000),
      tool: 'Google',
      leads: undefined
    },
    {
      type: 'thought',
      data: 'GrowthMetrics raised $30M Series B funding 1 week ago',
      timestamp: new Date(now + 35000),
      tool: 'Google',
      leads: undefined
    },
    {
      type: 'thinking',
      data: 'Analyzing funding announcements for CRM buying signals...',
      timestamp: new Date(now + 37000),
      tool: 'Google',
      leads: undefined
    },
    {
      type: 'thought',
      data: 'Series B funding typically means sales team expansion',
      timestamp: new Date(now + 39000),
      tool: 'Google',
      leads: undefined
    },
    {
      type: 'thought',
      data: 'Found 5 more companies with recent funding or aggressive hiring',
      timestamp: new Date(now + 41000),
      tool: 'Google',
      leads: undefined
    },
    {
      type: 'thinking',
      data: 'Scanning job boards for CRM-related sales positions...',
      timestamp: new Date(now + 44000),
      tool: 'Google',
      leads: undefined
    },
    {
      type: 'tool_complete',
      data: 'Identified 12 companies with strong buying signals',
      timestamp: new Date(now + 46000),
      tool: 'Google',
      leads: undefined
    },

    // === ACT 4: LINKEDIN ROUND 2 (47-61s) ===
    {
      type: 'thought',
      data: 'Discovered 5 new companies - scanning LinkedIn for decision-makers',
      timestamp: new Date(now + 47000),
      tool: undefined,
      leads: undefined
    },

    // LINKEDIN #2 START
    {
      type: 'tool_start',
      data: 'Searching decision-makers at newly discovered companies',
      timestamp: new Date(now + 48000),
      tool: 'LinkedIn',
      leads: undefined
    },
    {
      type: 'thinking',
      data: 'Targeting VPs, CROs, Sales Directors, RevOps leaders...',
      timestamp: new Date(now + 50000),
      tool: 'LinkedIn',
      leads: undefined
    },
    {
      type: 'thought',
      data: 'Jennifer Martinez (Sales Director) actively researching CRM solutions',
      timestamp: new Date(now + 52000),
      tool: 'LinkedIn',
      leads: undefined
    },
    {
      type: 'thought',
      data: 'Alex Patel (VP RevOps) posting about AI-powered CRM features',
      timestamp: new Date(now + 54000),
      tool: 'LinkedIn',
      leads: undefined
    },
    {
      type: 'thought',
      data: 'Alex\'s AI focus matches our product strengths perfectly',
      timestamp: new Date(now + 56000),
      tool: 'LinkedIn',
      leads: undefined
    },
    {
      type: 'thinking',
      data: 'Enriching contact information and validating email addresses...',
      timestamp: new Date(now + 58000),
      tool: 'LinkedIn',
      leads: undefined
    },
    {
      type: 'lead_batch',
      data: 'Extracted 2 leads from LinkedIn',
      timestamp: new Date(now + 60000),
      tool: 'LinkedIn',
      leads: MOCK_LEADS_BATCH_3
    },
    {
      type: 'tool_complete',
      data: 'Screened 31 profiles, selected 2 with strongest signals',
      timestamp: new Date(now + 61000),
      tool: 'LinkedIn',
      leads: undefined
    },

    // === ACT 5: TWITTER REAL-TIME SIGNALS (62-73s) ===
    {
      type: 'thought',
      data: 'Checking Twitter for real-time CRM complaints and discussions',
      timestamp: new Date(now + 62000),
      tool: undefined,
      leads: undefined
    },

    // TWITTER #1 START
    {
      type: 'tool_start',
      data: 'Monitoring CRM-related conversations and complaints',
      timestamp: new Date(now + 63000),
      tool: 'Twitter',
      leads: undefined
    },
    {
      type: 'thought',
      data: 'CEO asking: "Why do all CRMs feel like they\'re built for enterprises?"',
      timestamp: new Date(now + 65000),
      tool: 'Twitter',
      leads: undefined
    },
    {
      type: 'thought',
      data: 'Head of BD complaining about "impossible to get useful CRM reports"',
      timestamp: new Date(now + 67000),
      tool: 'Twitter',
      leads: undefined
    },
    {
      type: 'thought',
      data: 'Cross-referencing Twitter profiles with LinkedIn for validation',
      timestamp: new Date(now + 69000),
      tool: 'Twitter',
      leads: undefined
    },
    {
      type: 'thinking',
      data: 'Matching 23 Twitter users to LinkedIn profiles...',
      timestamp: new Date(now + 71000),
      tool: 'Twitter',
      leads: undefined
    },
    {
      type: 'tool_complete',
      data: 'Analyzed 42 conversations, found qualified prospects',
      timestamp: new Date(now + 73000),
      tool: 'Twitter',
      leads: undefined
    },

    // === ACT 6: REDDIT VALIDATION (74-82s) ===
    {
      type: 'thought',
      data: 'Validating Twitter leads in Reddit for multi-platform signals',
      timestamp: new Date(now + 74000),
      tool: undefined,
      leads: undefined
    },

    // REDDIT #2 START
    {
      type: 'tool_start',
      data: 'Searching for Sarah and Lisa in Reddit discussions',
      timestamp: new Date(now + 75000),
      tool: 'Reddit',
      leads: undefined
    },
    {
      type: 'thought',
      data: 'Lisa Wang also posted about CRM analytics limitations in r/sales',
      timestamp: new Date(now + 77000),
      tool: 'Reddit',
      leads: undefined
    },
    {
      type: 'thought',
      data: 'Multi-platform signals indicate stronger buying intent',
      timestamp: new Date(now + 79000),
      tool: 'Reddit',
      leads: undefined
    },
    {
      type: 'lead_batch',
      data: 'Extracted 2 leads validated across platforms',
      timestamp: new Date(now + 81000),
      tool: 'Reddit',
      leads: MOCK_LEADS_BATCH_4
    },
    {
      type: 'tool_complete',
      data: 'Validated 2 leads with cross-platform presence',
      timestamp: new Date(now + 82000),
      tool: 'Reddit',
      leads: undefined
    },

    // === ACT 7: FINAL PASS (83-93s) ===
    {
      type: 'thought',
      data: 'Final pass: Google for company verification, LinkedIn for remaining leads',
      timestamp: new Date(now + 83000),
      tool: undefined,
      leads: undefined
    },

    // GOOGLE #2 START
    {
      type: 'tool_start',
      data: 'Verifying company details and hiring activity',
      timestamp: new Date(now + 84000),
      tool: 'Google',
      leads: undefined
    },
    {
      type: 'thought',
      data: '5 companies actively hiring for multiple sales roles',
      timestamp: new Date(now + 86000),
      tool: 'Google',
      leads: undefined
    },
    {
      type: 'tool_complete',
      data: 'Verified 8 companies with active sales hiring',
      timestamp: new Date(now + 88000),
      tool: 'Google',
      leads: undefined
    },

    // LINKEDIN #3 START
    {
      type: 'tool_start',
      data: 'Final LinkedIn sweep for any missed decision-makers',
      timestamp: new Date(now + 89000),
      tool: 'LinkedIn',
      leads: undefined
    },
    {
      type: 'thought',
      data: 'Found 2 more influencers at companies with multiple signals',
      timestamp: new Date(now + 90000),
      tool: 'LinkedIn',
      leads: undefined
    },
    {
      type: 'lead_batch',
      data: 'Extracted 2 final leads from LinkedIn',
      timestamp: new Date(now + 92000),
      tool: 'LinkedIn',
      leads: MOCK_LEADS_BATCH_5
    },
    {
      type: 'tool_complete',
      data: 'Final sweep complete - covered all high-potential targets',
      timestamp: new Date(now + 93000),
      tool: 'LinkedIn',
      leads: undefined
    },

    // === ACT 8: WRAP UP (94-95s) ===
    {
      type: 'thought',
      data: 'Prospecting complete! Found 9 qualified leads across 4 platforms',
      timestamp: new Date(now + 94000),
      tool: undefined,
      leads: undefined
    },
    {
      type: 'thought',
      data: 'Top priority: 3 HOT leads with immediate buying signals',
      timestamp: new Date(now + 95000),
      tool: undefined,
      leads: undefined
    }
  ];
}
