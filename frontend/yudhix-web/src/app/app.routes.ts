import { Routes } from '@angular/router';
import { authGuard, workspaceGuard } from './core/guards';
import { ShellComponent } from './layout/shell.component';

export const routes: Routes = [
  // ---- Public (marketing, pricing, invitations)
  { path: '', pathMatch: 'full', title: 'Yudhix: truth-first social intelligence', loadComponent: () => import('./features/public/landing.page').then((m) => m.LandingPage) },
  { path: 'pricing', title: 'Pricing · Yudhix', loadComponent: () => import('./features/public/pricing.page').then((m) => m.PricingPage) },
  { path: 'invite/:token', title: 'Join workspace · Yudhix', loadComponent: () => import('./features/public/invite.page').then((m) => m.InvitePage) },

  // ---- Signed in, before a workspace exists
  { path: 'onboarding', title: 'Set up your workspace · Yudhix', canActivate: [authGuard], loadComponent: () => import('./features/onboarding/onboarding.page').then((m) => m.OnboardingPage) },

  // ---- The app (signed in + workspace). Truth first: Analyze is the home screen.
  {
    path: '',
    component: ShellComponent,
    canActivate: [authGuard, workspaceGuard],
    children: [
      { path: 'analyze', title: 'Analyze · Yudhix', loadComponent: () => import('./features/analyze/analyze.page').then((m) => m.AnalyzePage) },
      { path: 'videos', title: 'Videos · Yudhix', loadComponent: () => import('./features/videos/videos.page').then((m) => m.VideosPage) },
      { path: 'videos/:videoId', title: 'Truth report · Yudhix', loadComponent: () => import('./features/videos/video-report.page').then((m) => m.VideoReportPage) },
      { path: 'products', title: 'Products · Yudhix', loadComponent: () => import('./features/products/products.page').then((m) => m.ProductsPage) },
      { path: 'products/:productId', title: 'Product · Yudhix', loadComponent: () => import('./features/products/product.page').then((m) => m.ProductPage) },
      { path: 'inbox', title: 'Inbox · Yudhix', loadComponent: () => import('./features/inbox/inbox.page').then((m) => m.InboxPage) },
      { path: 'approvals', title: 'Approvals · Yudhix', loadComponent: () => import('./features/approvals/approvals.page').then((m) => m.ApprovalsPage) },
      { path: 'track', title: 'Track · Yudhix', loadComponent: () => import('./features/track/track.page').then((m) => m.TrackPage) },
      { path: 'ideas', title: 'Product ideas · Yudhix', loadComponent: () => import('./features/ideas/ideas.page').then((m) => m.IdeasPage) },
      { path: 'knowledge', title: 'Knowledge · Yudhix', loadComponent: () => import('./features/knowledge/knowledge.page').then((m) => m.KnowledgePage) },
      { path: 'settings', loadChildren: () => import('./features/settings/settings.routes').then((m) => m.SETTINGS_ROUTES) },
    ],
  },
  { path: '**', redirectTo: '' },
];
