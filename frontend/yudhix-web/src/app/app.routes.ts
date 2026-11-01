import { Routes } from '@angular/router';
import { ShellComponent } from './layout/shell.component';

// Truth first: the app opens on "Analyze a video". Each page is lazy-loaded.
export const routes: Routes = [
  {
    path: '',
    component: ShellComponent,
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'analyze' },
      { path: 'analyze', title: 'Analyze · Yudhix', loadComponent: () => import('./features/analyze/analyze.page').then((m) => m.AnalyzePage) },
      { path: 'videos', title: 'Videos · Yudhix', loadComponent: () => import('./features/videos/videos.page').then((m) => m.VideosPage) },
      { path: 'videos/:videoId', title: 'Truth report · Yudhix', loadComponent: () => import('./features/videos/video-report.page').then((m) => m.VideoReportPage) },
      { path: 'inbox', title: 'Inbox · Yudhix', loadComponent: () => import('./features/inbox/inbox.page').then((m) => m.InboxPage) },
      { path: 'approvals', title: 'Approvals · Yudhix', loadComponent: () => import('./features/approvals/approvals.page').then((m) => m.ApprovalsPage) },
      { path: 'track', title: 'Track · Yudhix', loadComponent: () => import('./features/track/track.page').then((m) => m.TrackPage) },
      { path: 'knowledge', title: 'Knowledge · Yudhix', loadComponent: () => import('./features/knowledge/knowledge.page').then((m) => m.KnowledgePage) },
      { path: '**', redirectTo: 'analyze' },
    ],
  },
];
