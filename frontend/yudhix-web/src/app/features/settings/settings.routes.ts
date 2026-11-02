import { Routes } from '@angular/router';
import { permissionGuard } from '../../core/guards';
import { SettingsLayout } from './settings.layout';

export const SETTINGS_ROUTES: Routes = [
  {
    path: '',
    component: SettingsLayout,
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'workspace' },
      { path: 'workspace', title: 'Workspace · Yudhix', loadComponent: () => import('./workspace.page').then((m) => m.WorkspaceSettingsPage) },
      { path: 'team', title: 'Team · Yudhix', loadComponent: () => import('./team.page').then((m) => m.TeamPage) },
      { path: 'billing', title: 'Billing · Yudhix', loadComponent: () => import('./billing.page').then((m) => m.BillingPage) },
    ],
  },
  {
    path: 'billing/invoices/:invoiceId',
    title: 'Invoice · Yudhix',
    canActivate: [permissionGuard('billing.manage')],
    loadComponent: () => import('./invoice.page').then((m) => m.InvoicePage),
  },
];
