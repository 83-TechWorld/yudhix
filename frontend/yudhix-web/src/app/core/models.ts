// Shapes returned by yudhix-sense (services/yudhix-sense/app/api).

export type Verdict = 'FACTUALLY_CORRECT' | 'MISLEADING' | 'FALSE' | 'UNVERIFIED_SPECULATION';
export type Sentiment = 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL' | 'MIXED';
export type Priority = 'P1' | 'P2' | 'P3';
export type RootCause = 'MISINFORMATION' | 'VALID_CONCERN' | 'UNLINKED';
export type ReplyStatus = 'DRAFT' | 'IN_REVIEW' | 'REJECTED' | 'APPROVED' | 'POSTED';
export type Outcome = 'IMPROVED' | 'NEUTRAL' | 'WORSENED';


export interface Health {
  status: string;
  capabilities: {
    llm: boolean;
    llmModel: string;
    youtubeApi: boolean;
    captions: boolean;
    whisper: boolean;
    livePosting: boolean;
  };
}

export interface Job {
  id: string;
  videoUrl: string;
  videoId: string;
  productId: string | null;
  status: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  stage: string;
  progress: number;
  message: string | null;
  error: string | null;
  createdAt: string;
  finishedAt: string | null;
}

export interface KnowledgeRef {
  id: string;
  title: string;
  clauseRef: string | null;
  statement: string;
  source: string | null;
}

export interface Claim {
  id: string;
  timestamp: string;
  timestampSeconds: number;
  quote: string;
  topic: string;
  verdict: Verdict;
  isMisinformation: boolean;
  confidence: number;
  analysis: string;
  citation: string | null;
  linkedComments: number;
  sentimentImpact: string | null;
  verificationMethod: string | null;
  knowledge: KnowledgeRef | null;
}

export interface Video {
  id: string;
  videoId: string;
  title: string;
  channel: string;
  url: string;
  thumbnailUrl: string;
  publishedDate: string | null;
  durationSeconds: number;
  viewCount: number | null;
  factualAccuracy: number;
  rageBaitScore: number;
  sensationalismGrade: string | null;
  totalClaims: number;
  misleadingClaims: number;
  summary: string | null;
  transcriptSource: string | null;
  analysisMethod: string | null;
  analyzedAt: string | null;
  comments: number;
  negativeComments: number;
  positiveComments: number;
  linkedComments: number;
  claims?: Claim[];
}

export interface ClaimImpact extends Claim {
  sentiment: { positive?: number; negative?: number; neutral?: number };
}

export interface Impact {
  video: Video;
  claims: ClaimImpact[];
  rootCauses: { cause: RootCause; total: number; negative: number }[];
  negativeComments: number;
  misinformationShareOfNegative: number;
  headline: string;
}

export interface ClaimComment {
  id: string;
  text: string;
  likes: number;
  replies: number;
  sentiment: Sentiment;
  priority: Priority;
  impactScore: number;
  linkScore: number;
  linkMethod: string;
  evidence: string | null;
}

export interface Knowledge {
  id: string;
  productId: string | null;
  productName: string | null;
  title: string;
  category: string;
  clauseRef: string | null;
  statement: string;
  source: string | null;
  verifiedAt: string | null;
  usedByClaims: number;
}

export interface OutreachNote {
  id: string;
  videoId: string;
  channel: string | null;
  claimIds: string[];
  subject: string;
  body: string;
  status: 'DRAFT' | 'SENT';
  createdAt: string;
  updatedAt: string;
}

export interface InboxItem {
  id: string;
  platform: string;
  text: string;
  likes: number;
  replies: number;
  createdAt: string;
  authorHash: string;
  videoId: string | null;
  videoTitle: string | null;
  sentiment: Sentiment;
  impactScore: number;
  priority: Priority;
  rootCause: RootCause;
  claim: {
    id: string;
    verdict: Verdict;
    topic: string;
    timestamp: string;
    evidence: string | null;
    quote?: string;
    analysis?: string;
    officialStatement?: string | null;
    source?: string | null;
  } | null;
  replyId: string | null;
  replyStatus: ReplyStatus | null;
  churnRisk?: number;
  replyHistory?: Reply[];
}

export interface InboxPage {
  items: InboxItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface ApprovalStep {
  step: string;
  decision: string;
  reviewerId: string;
  reviewerName: string;
  comments: string | null;
  at: string;
}

export interface Reply {
  id: string;
  commentId: string;
  commentText: string;
  videoId: string | null;
  videoTitle: string | null;
  priority: Priority | null;
  commentSentiment: Sentiment | null;
  text: string;
  status: ReplyStatus;
  authorId: string;
  authorName: string;
  approverId: string | null;
  approverName: string | null;
  slaDueAt: string;
  slaBreached: boolean;
  rejectionReason: string | null;
  deliveryMode: 'LIVE' | 'SIMULATED' | null;
  platformReplyId: string | null;
  createdAt: string;
  updatedAt: string;
  submittedAt: string | null;
  approvedAt: string | null;
  postedAt: string | null;
  claimId: string | null;
  outcome: Outcome | null;
  followUpText: string | null;
  steps: ApprovalStep[];
}

export interface Summary {
  videos: number;
  claims: { total: number; correct: number; misleading: number; false: number; unverified: number };
  comments: { total: number; negative: number; positive: number; neutral: number; p1: number; p2: number; p3: number };
  misinformationShareOfNegative: number;
  validConcernShareOfNegative: number;
  replies: { draft: number; in_review: number; rejected: number; approved: number; posted: number; sla_breached: number };
  avgReviewHours: number | null;
  outcomes: { improved: number; neutral: number; worsened: number; pending: number };
  turnaroundRate: number | null;
}

export interface TrendPoint {
  day: string;
  positive: number;
  negative: number;
  neutral: number;
}

export interface LeaderboardRow {
  videoId: string;
  title: string;
  channel: string;
  factualAccuracy: number;
  misleadingClaims: number;
  totalClaims: number;
  comments: number;
  repliesPosted: number;
}

// ---------------------------------------------------------------------------- SaaS

export type WorkspaceRole = 'admin' | 'approver' | 'agent' | 'analyst';
export type SubscriptionStatus = 'TRIALING' | 'TRIAL_EXPIRED' | 'ACTIVE' | 'CANCELED';

export interface WorkspaceSummary {
  id: string;
  name: string;
  slug: string;
  isDemo: boolean;
  country: string;
  role: WorkspaceRole;
  plan: string | null;
  subscriptionStatus: SubscriptionStatus | null;
  trialEndsAt: string | null;
}

export interface Me {
  user: { id: string; email: string; name: string; emailVerified: boolean };
  workspaces: WorkspaceSummary[];
  pendingInvitations: { id: string; workspace: string; role: WorkspaceRole; expiresAt: string }[];
  demoAvailable: boolean;
}

export interface WorkspaceDetail {
  id: string;
  name: string;
  slug: string;
  country: string;
  countryName: string | null;
  industry: string | null;
  teamSize: string | null;
  dataRegion: string;
  isDemo: boolean;
  createdAt: string;
  role?: WorkspaceRole;
}

export interface Country { code: string; name: string; currency: string; }

export interface Plan {
  id: string;
  name: string;
  tagline: string | null;
  currency: string;
  monthlyPrice: number;
  yearlyPrice: number | null;
  features: string[];
  highlighted: boolean;
  quotas: { videos: number; comments: number; aiCalls: number; replies: number; seats: number };
}

export interface Meter {
  metric: string;
  label: string;
  used: number;
  quota: number | null;
  percent: number | null;
  hardLimit: boolean;
}

export interface InvoiceLine { description: string; quantity: number; unit_price?: number; unitPrice?: number; amount: number; }

export interface BillingSummary {
  plan: { id: string; name: string; currency: string; price: number; interval: 'MONTH' | 'YEAR' };
  status: SubscriptionStatus;
  trialEndsAt: string | null;
  periodStart: string;
  periodEnd: string;
  meters: Meter[];
  upcoming: { date: string; subtotal: number; tax: number; taxLabel: string; total: number; lines: InvoiceLine[] } | null;
  paymentsConnected: boolean;
}

export interface Invoice {
  id: string;
  number: string;
  status: string;
  currency: string;
  subtotal: number;
  tax: number;
  taxLabel: string;
  total: number;
  issuedAt: string;
  dueAt: string | null;
  periodStart: string | null;
  periodEnd: string | null;
  paidAt: string | null;
  lines?: InvoiceLine[];
  billTo?: { name: string; country: string };
}

export interface Member { userId: string; email: string; name: string; role: WorkspaceRole; joinedAt: string; lastSeenAt: string | null; }

export interface Invitation {
  id: string;
  email: string;
  role: WorkspaceRole;
  status: string;
  expiresAt: string;
  createdAt: string;
  expired: boolean;
  invitedBy?: string | null;
  link?: string;
  emailSent?: boolean;
}

export interface InvitePreview { workspace: string; role: WorkspaceRole; roleLabel: string; invitedBy: string; email: string; expiresAt: string; }

export interface AppNotification { id: number; kind: string; title: string; body: string | null; link: string | null; read: boolean; createdAt: string; }

export interface Onboarding { steps: { key: string; label: string; done: boolean; link: string }[]; completed: number; total: number; }

export interface Product { id: string; name: string; code: string; category: string | null; }
