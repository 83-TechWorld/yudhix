import { HttpClient, HttpErrorResponse, HttpInterceptorFn, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  Claim,
  ClaimComment,
  Health,
  Impact,
  InboxItem,
  InboxPage,
  Job,
  Knowledge,
  LeaderboardRow,
  OutreachNote,
  Reply,
  Summary,
  TrendPoint,
  Video,
} from './models';
import { SessionService } from './session.service';

/** Adds tenant + acting-user headers. The gateway will set these from the JWT once auth ships. */
export const contextInterceptor: HttpInterceptorFn = (req, next) => {
  if (!req.url.startsWith(environment.apiUrl)) return next(req);
  const session = inject(SessionService);
  return next(
    req.clone({
      setHeaders: {
        'X-Tenant-Id': environment.tenantId,
        'X-User-Role': session.role(),
        'X-User-Id': session.user().id,
      },
    }),
  );
};

/** Turns any HTTP error into one readable sentence for toasts and inline errors. */
export function errorMessage(err: unknown): string {
  if (err instanceof HttpErrorResponse) {
    if (err.status === 0) return "Can't reach the Yudhix API. Is yudhix-sense running on " + environment.apiUrl + '?';
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
  analyze(body: { video_url: string; transcript?: string | null }): Observable<Job> {
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
  knowledge(): Observable<{ knowledge: Knowledge[] }> {
    return this.http.get<{ knowledge: Knowledge[] }>(`${this.v1}/truth/knowledge`);
  }
  addKnowledge(body: { title: string; statement: string; category?: string; clauseRef?: string; source?: string }): Observable<Knowledge> {
    return this.http.post<Knowledge>(`${this.v1}/truth/knowledge`, body);
  }
  deleteKnowledge(id: string): Observable<void> {
    return this.http.delete<void>(`${this.v1}/truth/knowledge/${id}`);
  }

  // --- Respond ---------------------------------------------------------------
  inbox(filters: {
    video_id?: string | null;
    priority?: string | null;
    sentiment?: string | null;
    cause?: string | null;
    status?: string | null;
    q?: string | null;
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
}
