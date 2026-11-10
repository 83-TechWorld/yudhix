import { HttpClient, HttpErrorResponse, HttpInterceptorFn, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, from, switchMap, throwError } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  AiProvider,
  AiSettings,
  AiStatus,
  AiSync,
  Listing,
  ProductComment,
  ProductOverview,
  ProductSummary,
  KnowledgeDocument,
  Claim,
  ClaimComment,
  CommentSchedule,
  Growth,
  Idea,
  IdeaStatus,
  Health,
  Impact,
  ProductImpact,
  InboxItem,
  InboxPage,
  Job,
  Knowledge,
  LeaderboardRow,
  OutreachNote,
  Reply,
  AppNotification,
  BillingSummary,
  Country,
  Invitation,
  InvitePreview,
  Invoice,
  Me,
  Member,
  Onboarding,
  Plan,
  Product,
  Summary,
  TrendPoint,
  Verdict,
  Video,
  WorkspaceDetail,
  WorkspaceRole,
} from './models';
import { AuthService } from './auth.service';
import { SessionService } from './session.service';

/**
 * Adds the Keycloak access token and the current workspace to every API call.
 * A 401 means the session ended: send the user back through sign-in.
 */
export const contextInterceptor: HttpInterceptorFn = (req, next) => {
  if (!req.url.startsWith(environment.apiUrl) || req.url.includes('/api/v1/public/')) return next(req);
  const auth = inject(AuthService);
  const session = inject(SessionService);
  return from(auth.token()).pipe(
    switchMap((token) => {
      const headers: Record<string, string> = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const ws = session.workspaceId();
      if (ws && !req.headers.has('X-Tenant-Id')) headers['X-Tenant-Id'] = ws;
      return next(req.clone({ setHeaders: headers }));
    }),
    catchError((err: unknown) => {
      // 401: the API no longer accepts this session. Sign in again (once) and come back here.
      if (err instanceof HttpErrorResponse && err.status === 401) auth.sessionEnded();
      return throwError(() => err);
    }),
  );
};

/** Turns any HTTP error into one readable sentence for toasts and inline errors. */
export function errorMessage(err: unknown): string {
  if (err instanceof HttpErrorResponse) {
    if (err.status === 0) return "Can't reach the Yudhix API. Is yudhix-sense running on " + environment.apiUrl + '?';
    if (err.status === 402 && typeof err.error?.detail === 'string') return err.error.detail;
    const detail = err.error?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
    return `Request failed (${err.status}).`;
  }
  return 'Something went wrong.';
}

function params(obj: Record<string, string | number | null | undefined>): HttpParams {
  let p = new HttpParams();
  for (const [k, v] of Object.entries(obj)) {
    if (v !== null && v !== undefined && v !== '') p = p.set(k, String(v));
  }
  return p;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);
  private base = environment.apiUrl;
  private v1 = `${this.base}/api/v1`;

  health(): Observable<Health> {
    return this.http.get<Health>(`${this.base}/health`);
  }

  // --- Truth -----------------------------------------------------------------
  analyze(body: { video_url: string; transcript?: string | null; product_id?: string | null }): Observable<Job> {
    return this.http.post<Job>(`${this.v1}/truth/analyze`, body);
  }
  jobs(): Observable<{ jobs: Job[] }> {
    return this.http.get<{ jobs: Job[] }>(`${this.v1}/truth/jobs`);
  }
  job(id: string): Observable<Job> {
    return this.http.get<Job>(`${this.v1}/truth/jobs/${id}`);
  }
  videos(): Observable<{ videos: Video[] }> {
    return this.http.get<{ videos: Video[] }>(`${this.v1}/truth/videos`);
  }
  video(videoId: string): Observable<Video & { claims: Claim[] }> {
    return this.http.get<Video & { claims: Claim[] }>(`${this.v1}/truth/videos/${videoId}`);
  }
  impact(videoId: string): Observable<Impact> {
    return this.http.get<Impact>(`${this.v1}/truth/videos/${videoId}/impact`);
  }
  productImpact(videoId: string): Observable<ProductImpact> {
    return this.http.get<ProductImpact>(`${this.v1}/truth/videos/${videoId}/product-impact`);
  }
  /** Fetch comments posted since the last check. Returns the job to poll. */
  checkComments(videoId: string): Observable<Job> {
    return this.http.post<Job>(`${this.v1}/truth/videos/${videoId}/check-comments`, {});
  }
  /** Fact-check the stored claims again against the current knowledge base. Returns the job to poll. */
  recheckFacts(videoId: string): Observable<Job> {
    return this.http.post<Job>(`${this.v1}/truth/videos/${videoId}/recheck-facts`, {});
  }
  /** Re-check every video that was checked against older facts. */
  recheckAll(): Observable<{ queued: number; jobs: Job[] }> {
    return this.http.post<{ queued: number; jobs: Job[] }>(`${this.v1}/truth/knowledge/recheck`, {});
  }
  growth(videoId: string): Observable<Growth> {
    return this.http.get<Growth>(`${this.v1}/truth/videos/${videoId}/growth`);
  }
  ideas(filters: { status?: string | null; video_id?: string | null } = {}): Observable<{ ideas: Idea[] }> {
    return this.http.get<{ ideas: Idea[] }>(`${this.v1}/truth/ideas`, { params: params(filters) });
  }
  idea(id: string): Observable<Idea> {
    return this.http.get<Idea>(`${this.v1}/truth/ideas/${id}`);
  }
  updateIdea(id: string, body: { status?: IdeaStatus; note?: string; title?: string }): Observable<Idea> {
    return this.http.patch<Idea>(`${this.v1}/truth/ideas/${id}`, body);
  }
  commentSchedule(): Observable<CommentSchedule> {
    return this.http.get<CommentSchedule>(`${this.v1}/truth/comment-schedule`);
  }
  saveCommentSchedule(body: { enabled?: boolean; interval_hours?: number }): Observable<CommentSchedule> {
    return this.http.put<CommentSchedule>(`${this.v1}/truth/comment-schedule`, body);
  }
  reattribute(videoId: string): Observable<unknown> {
    return this.http.post(`${this.v1}/truth/videos/${videoId}/reattribute`, {});
  }
  claimComments(claimId: string): Observable<{ comments: ClaimComment[] }> {
    return this.http.get<{ comments: ClaimComment[] }>(`${this.v1}/truth/claims/${claimId}/comments`);
  }
  outreach(videoId: string): Observable<{ notes: OutreachNote[] }> {
    return this.http.get<{ notes: OutreachNote[] }>(`${this.v1}/truth/videos/${videoId}/outreach`);
  }
  createOutreach(videoId: string, claimIds?: string[]): Observable<OutreachNote> {
    return this.http.post<OutreachNote>(`${this.v1}/truth/videos/${videoId}/outreach`, { claim_ids: claimIds ?? null });
  }
  updateOutreach(id: string, body: Partial<Pick<OutreachNote, 'subject' | 'body' | 'status'>>): Observable<OutreachNote> {
    return this.http.patch<OutreachNote>(`${this.v1}/truth/outreach/${id}`, body);
  }
  knowledge(): Observable<{ knowledge: Knowledge[]; staleVideos: number }> {
    return this.http.get<{ knowledge: Knowledge[]; staleVideos: number }>(`${this.v1}/truth/knowledge`);
  }
  addKnowledge(body: { title: string; statement: string; category?: string; clauseRef?: string; source?: string }): Observable<Knowledge> {
    return this.http.post<Knowledge>(`${this.v1}/truth/knowledge`, body);
  }
  knowledgeDocuments(): Observable<{ documents: KnowledgeDocument[] }> {
    return this.http.get<{ documents: KnowledgeDocument[] }>(`${this.v1}/truth/knowledge/documents`);
  }
  uploadDocument(body: { filename: string; content_base64: string; title?: string; category?: string }): Observable<KnowledgeDocument> {
    return this.http.post<KnowledgeDocument>(`${this.v1}/truth/knowledge/documents`, body);
  }
  deleteDocument(id: string): Observable<void> {
    return this.http.delete<void>(`${this.v1}/truth/knowledge/documents/${id}`);
  }
  aiSync(): Observable<AiSync> {
    return this.http.get<AiSync>(`${this.v1}/ai/sync`);
  }
  syncNow(): Observable<AiSync> {
    return this.http.post<AiSync>(`${this.v1}/ai/sync`, {});
  }
  deleteKnowledge(id: string): Observable<void> {
    return this.http.delete<void>(`${this.v1}/truth/knowledge/${id}`);
  }

  // --- Products across channels (YouTube + Amazon) -------------------------------------
  catalogProducts(): Observable<{ products: ProductSummary[] }> {
    return this.http.get<{ products: ProductSummary[] }>(`${this.v1}/catalog/products`);
  }
  productOverview(id: string): Observable<ProductOverview> {
    return this.http.get<ProductOverview>(`${this.v1}/catalog/products/${id}`);
  }
  productComments(id: string, filters: { channel?: string | null; sentiment?: string | null; limit?: number; offset?: number }): Observable<{ items: ProductComment[]; total: number }> {
    return this.http.get<{ items: ProductComment[]; total: number }>(`${this.v1}/catalog/products/${id}/comments`, { params: params(filters) });
  }
  /** Track an Amazon listing for a product and collect its reviews. Returns the job to poll. */
  analyzeAmazon(body: { url: string; product_id: string }): Observable<Job & { listing: Listing }> {
    return this.http.post<Job & { listing: Listing }>(`${this.v1}/catalog/amazon`, body);
  }
  checkListing(id: string): Observable<Job> {
    return this.http.post<Job>(`${this.v1}/catalog/listings/${id}/check`, {});
  }
  removeListing(id: string): Observable<void> {
    return this.http.delete<void>(`${this.v1}/catalog/listings/${id}`);
  }

  // --- AI settings ---------------------------------------------------------------
  aiStatus(): Observable<AiStatus> {
    return this.http.get<AiStatus>(`${this.v1}/ai/status`);
  }
  aiProviders(): Observable<{ providers: AiProvider[] }> {
    return this.http.get<{ providers: AiProvider[] }>(`${this.v1}/ai/providers`);
  }
  aiSettings(): Observable<AiSettings> {
    return this.http.get<AiSettings>(`${this.v1}/ai/settings`);
  }
  /** Checks the key by listing the provider's models. */
  aiModels(body: { provider: string; api_key?: string | null; base_url?: string | null }): Observable<{ models: string[]; suggested: string | null; embedModel: string | null }> {
    return this.http.post<{ models: string[]; suggested: string | null; embedModel: string | null }>(`${this.v1}/ai/models`, body);
  }
  /** LOCAL switches right away; CLOUD runs a test request first and only switches if it passes. */
  saveAiSettings(body: { mode: 'LOCAL' | 'CLOUD'; provider?: string | null; model?: string | null; api_key?: string | null; base_url?: string | null }): Observable<AiSettings> {
    return this.http.put<AiSettings>(`${this.v1}/ai/settings`, body);
  }
  removeAiKey(): Observable<AiSettings> {
    return this.http.delete<AiSettings>(`${this.v1}/ai/key`);
  }
  overrideClaim(claimId: string, verdict: Verdict, note?: string): Observable<Video & { claims: Claim[] }> {
    return this.http.patch<Video & { claims: Claim[] }>(`${this.v1}/truth/claims/${claimId}`, { verdict, note: note || null });
  }

  // --- Respond ---------------------------------------------------------------
  inbox(filters: {
    video_id?: string | null;
    priority?: string | null;
    sentiment?: string | null;
    cause?: string | null;
    status?: string | null;
    q?: string | null;
    intent?: string | null;
    fresh?: number | null;
    platform?: string | null;
    limit?: number;
    offset?: number;
  }): Observable<InboxPage> {
    return this.http.get<InboxPage>(`${this.v1}/inbox`, { params: params(filters) });
  }
  inboxItem(commentId: string): Observable<InboxItem> {
    return this.http.get<InboxItem>(`${this.v1}/inbox/${commentId}`);
  }
  suggest(commentId: string): Observable<{ text: string; citesOfficialFact: boolean }> {
    return this.http.post<{ text: string; citesOfficialFact: boolean }>(`${this.v1}/inbox/${commentId}/suggest`, {});
  }
  replies(status?: string): Observable<{ replies: Reply[] }> {
    return this.http.get<{ replies: Reply[] }>(`${this.v1}/replies`, { params: params({ status }) });
  }
  reply(id: string): Observable<Reply> {
    return this.http.get<Reply>(`${this.v1}/replies/${id}`);
  }
  createReply(commentId: string, text: string): Observable<Reply> {
    return this.http.post<Reply>(`${this.v1}/replies`, { comment_id: commentId, text });
  }
  editReply(id: string, text: string): Observable<Reply> {
    return this.http.patch<Reply>(`${this.v1}/replies/${id}`, { text });
  }
  replyAction(id: string, action: 'submit' | 'approve' | 'reject' | 'post', reason?: string): Observable<Reply> {
    return this.http.post<Reply>(`${this.v1}/replies/${id}/${action}`, reason ? { reason } : {});
  }
  recordOutcome(id: string, body: { follow_up_text?: string; outcome?: string }): Observable<Reply> {
    return this.http.post<Reply>(`${this.v1}/replies/${id}/outcomes`, body);
  }
  checkOutcomes(): Observable<{ checked: number; awaitingFollowUp: number; simulatedReplies: number; youtubeConnected: boolean }> {
    return this.http.post<{ checked: number; awaitingFollowUp: number; simulatedReplies: number; youtubeConnected: boolean }>(
      `${this.v1}/outcomes/check`,
      {},
    );
  }

  // --- Track -----------------------------------------------------------------
  summary(videoId?: string | null): Observable<Summary> {
    return this.http.get<Summary>(`${this.v1}/insights/summary`, { params: params({ video_id: videoId }) });
  }
  trend(videoId?: string | null, days = 120): Observable<{ points: TrendPoint[] }> {
    return this.http.get<{ points: TrendPoint[] }>(`${this.v1}/insights/trend`, { params: params({ video_id: videoId, days }) });
  }
  leaderboard(): Observable<{ videos: LeaderboardRow[] }> {
    return this.http.get<{ videos: LeaderboardRow[] }>(`${this.v1}/insights/videos`);
  }

  // --- SaaS: public ---------------------------------------------------------------
  plans(currency?: string | null): Observable<{ currency: string; currencies: string[]; plans: Plan[] }> {
    return this.http.get<{ currency: string; currencies: string[]; plans: Plan[] }>(`${this.v1}/public/plans`, {
      params: params({ currency }),
    });
  }
  countries(): Observable<{ countries: Country[] }> {
    return this.http.get<{ countries: Country[] }>(`${this.v1}/public/countries`);
  }
  invitePreview(token: string): Observable<InvitePreview> {
    return this.http.get<InvitePreview>(`${this.v1}/public/invitations/${encodeURIComponent(token)}`);
  }

  // --- SaaS: account & workspaces ---------------------------------------------------
  me(): Observable<Me> {
    return this.http.get<Me>(`${this.v1}/me`);
  }
  createWorkspace(body: { name: string; country: string; industry?: string | null; teamSize?: string | null }): Observable<WorkspaceDetail> {
    return this.http.post<WorkspaceDetail>(`${this.v1}/workspaces`, body);
  }
  joinDemo(): Observable<WorkspaceDetail> {
    return this.http.post<WorkspaceDetail>(`${this.v1}/workspaces/demo/join`, {});
  }
  acceptInvite(token: string): Observable<WorkspaceDetail> {
    return this.http.post<WorkspaceDetail>(`${this.v1}/invitations/${encodeURIComponent(token)}/accept`, {});
  }
  workspace(): Observable<WorkspaceDetail> {
    return this.http.get<WorkspaceDetail>(`${this.v1}/workspace`);
  }
  updateWorkspace(body: Partial<{ name: string; country: string; industry: string; teamSize: string }>): Observable<WorkspaceDetail> {
    return this.http.patch<WorkspaceDetail>(`${this.v1}/workspace`, body);
  }
  deleteWorkspace(confirmName: string): Observable<void> {
    return this.http.post<void>(`${this.v1}/workspace/delete`, { confirm_name: confirmName });
  }
  leaveWorkspace(): Observable<void> {
    return this.http.post<void>(`${this.v1}/workspace/leave`, {});
  }
  onboarding(): Observable<Onboarding> {
    return this.http.get<Onboarding>(`${this.v1}/workspace/onboarding`);
  }
  products(): Observable<{ products: Product[] }> {
    return this.http.get<{ products: Product[] }>(`${this.v1}/workspace/products`);
  }
  addProduct(name: string, category?: string | null): Observable<Product> {
    return this.http.post<Product>(`${this.v1}/workspace/products`, { name, category: category || null });
  }

  // --- SaaS: team ---------------------------------------------------------------------
  team(): Observable<{ members: Member[]; invitations: Invitation[]; canManage: boolean }> {
    return this.http.get<{ members: Member[]; invitations: Invitation[]; canManage: boolean }>(`${this.v1}/team`);
  }
  invite(emails: string[], role: WorkspaceRole): Observable<{ results: { email: string; ok: boolean; error?: string; invitation?: Invitation }[] }> {
    return this.http.post<{ results: { email: string; ok: boolean; error?: string; invitation?: Invitation }[] }>(
      `${this.v1}/team/invitations`,
      { emails, role },
    );
  }
  resendInvite(id: string): Observable<Invitation> {
    return this.http.post<Invitation>(`${this.v1}/team/invitations/${id}/resend`, {});
  }
  revokeInvite(id: string): Observable<void> {
    return this.http.delete<void>(`${this.v1}/team/invitations/${id}`);
  }
  setRole(userId: string, role: WorkspaceRole): Observable<{ members: Member[] }> {
    return this.http.patch<{ members: Member[] }>(`${this.v1}/team/members/${userId}`, { role });
  }
  removeMember(userId: string): Observable<{ members: Member[] }> {
    return this.http.delete<{ members: Member[] }>(`${this.v1}/team/members/${userId}`);
  }

  // --- SaaS: billing ------------------------------------------------------------------
  billing(): Observable<BillingSummary> {
    return this.http.get<BillingSummary>(`${this.v1}/billing`);
  }
  changePlan(planId: string, interval: 'MONTH' | 'YEAR'): Observable<BillingSummary> {
    return this.http.post<BillingSummary>(`${this.v1}/billing/plan`, { plan_id: planId, interval });
  }
  invoices(): Observable<{ invoices: Invoice[] }> {
    return this.http.get<{ invoices: Invoice[] }>(`${this.v1}/billing/invoices`);
  }
  invoice(id: string): Observable<Invoice> {
    return this.http.get<Invoice>(`${this.v1}/billing/invoices/${id}`);
  }

  // --- SaaS: notifications ------------------------------------------------------------
  notifications(): Observable<{ items: AppNotification[]; unread: number }> {
    return this.http.get<{ items: AppNotification[]; unread: number }>(`${this.v1}/notifications`);
  }
  markRead(ids?: number[]): Observable<void> {
    return this.http.post<void>(`${this.v1}/notifications/read`, { ids: ids ?? null });
  }
}
