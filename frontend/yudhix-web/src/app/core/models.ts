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
  /** ANALYZE = full analysis, COMMENTS = "fetch new comments" only. */
  kind: 'ANALYZE' | 'COMMENTS' | 'FACTS';
  trigger: 'USER' | 'SCHEDULE';
  /** COMMENTS: newComments / negative / ideas. FACTS: claims / changed. */
  result: { videoTitle: string; newComments?: number; negative?: number; ideas?: number; claims?: number; changed?: number } | null;
}

export interface KnowledgeRef {
  id: string;
  title: string;
  clauseRef: string | null;
  statement: string;
  source: string | null;
}

export interface Claim {
  /** The sentence of the official source the verdict rests on (checked to really be in the source). */
  sourceQuote?: string | null;
  needsReview?: boolean;
  reviewReason?: string | null;
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
  /** Comments added by "Fetch new comments" or the schedule since the last full analysis. */
  newComments: number;
  commentsCheckedAt: string | null;
  /** The knowledge base changed after these claims were checked. */
  factsStale: boolean;
  factsCheckedAt: string | null;
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

export type ImpactLevel = 'HIGH' | 'MEDIUM' | 'LOW';
export type ImpactTrend = 'RISING' | 'STEADY' | 'FADING' | 'QUIET';
export interface SentimentSplit { positive: number; neutral: number; negative: number }

/** What a commenter wants (set by the AI, or keyword rules when the AI is offline). */
export type Intent = 'IDEA' | 'PRAISE' | 'BUY' | 'QUESTION' | 'COMPLAINT' | 'LEAVE' | 'OTHER';
export type GrowthLevel = 'STRONG' | 'MODERATE' | 'LOW';
export type IdeaStatus = 'NEW' | 'REVIEWING' | 'PLANNED' | 'SHIPPED' | 'DECLINED';

export interface GrowthComment { id: string; text: string; likes: number; replies: number; reach: number; sentiment: Sentiment | null }

/** GET /truth/videos/:id/growth: the positive side of a video's comments, and the ideas in them. */
export interface Growth {
  score: number;
  level: GrowthLevel;
  headline: string;
  totals: { comments: number; reach: number };
  positiveShareOfReach: number;
  intents: { intent: Intent; label: string; comments: number; reach: number }[];
  loved: { topic: string; label: string; comments: number; reach: number }[];
  ideas: { id: string; title: string; status: IdeaStatus; comments: number; reach: number; examples: GrowthComment[] }[];
  ideaComments: number;
  unthemedIdeas: GrowthComment[];
  topPraise: GrowthComment[];
  buyingSignals: GrowthComment[];
  leaving: GrowthComment[];
  coverage: { aiComments: number };
}

/** A product idea: similar feature requests from comments, grouped by theme, across videos. */
export interface Idea {
  id: string;
  title: string;
  topic: string | null;
  topicLabel: string | null;
  status: IdeaStatus;
  note: string | null;
  comments: number;
  reach: number;
  videos: number;
  lastCommentAt: string | null;
  createdAt: string;
  updatedAt: string;
  commentList?: {
    id: string; text: string; likes: number; replies: number; sentiment: Sentiment | null;
    videoId: string | null; videoTitle: string | null; createdAt: string | null; active: boolean;
  }[];
}

/** Who answers AI requests in this workspace right now. */
export interface AiStatus { mode: 'CLOUD' | 'LOCAL' | 'RULES'; provider: string | null; label: string; model: string | null; embeddings: boolean }
export interface AiProvider { id: string; label: string; keyUrl: string; needsBaseUrl: boolean; embeddings: boolean }
export interface AiSettings {
  mode: 'LOCAL' | 'CLOUD';
  provider: string | null;
  model: string | null;
  embedModel: string | null;
  baseUrl: string | null;
  keyHint: string | null;
  hasKey: boolean;
  status: 'UNTESTED' | 'VALID' | 'INVALID';
  lastError: string | null;
  validatedAt: string | null;
  active: AiStatus;
  local: { available: boolean; model: string; embedModel: string | null };
}

/** Workspace schedule for checking analyzed videos for new comments. */
export interface CommentSchedule {
  enabled: boolean;
  intervalHours: number;
  intervals: number[];
  serverEnabled: boolean;
  youtubeConnected: boolean;
  lastRunAt: string | null;
}

/** GET /truth/videos/:id/product-impact: how the comments affect the product. */
export interface ProductImpact {
  score: number;
  level: ImpactLevel;
  trend: ImpactTrend;
  headline: string;
  totals: { comments: number; reach: number; likes: number };
  sentiment: { byComments: SentimentSplit; byReach: SentimentSplit };
  negativeShareOfReach: number;
  negativeByCause: { cause: RootCause; comments: number; reach: number; share: number }[];
  topics: {
    topic: string; label: string; comments: number; positive: number; neutral: number; negative: number;
    reach: number; negativeReach: number;
  }[];
  timeline: { bucket: 'day' | 'week'; points: ({ date: string } & SentimentSplit)[] };
  topNegative: {
    id: string; text: string; likes: number; replies: number; priority: string | null; cause: RootCause;
    claimTimestamp: string | null; topics: string[];
  }[];
  coverage: { aiComments: number; aiShareOfReach: number };
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
  intent: Intent | null;
  isNew: boolean;
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
  overagePer1000: number;
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
