import { TestBed } from '@angular/core/testing';
import { AgoPipe, CompactPipe, DuePipe, PctPipe, formatMoney, youtubeAt } from './ui';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { SessionService, initials, trialDaysLeft } from '../core/session.service';

describe('formatting pipes', () => {
  it('formats relative times', () => {
    const ago = new AgoPipe();
    expect(ago.transform(new Date(Date.now() - 30_000).toISOString())).toBe('just now');
    expect(ago.transform(new Date(Date.now() - 5 * 60_000).toISOString())).toBe('5m ago');
    expect(ago.transform(new Date(Date.now() - 3 * 3600_000).toISOString())).toBe('3h ago');
    expect(ago.transform(null)).toBe('');
  });

  it('formats SLA deadlines', () => {
    const due = new DuePipe();
    expect(due.transform(new Date(Date.now() + 2 * 3600_000 + 60_000).toISOString())).toBe('due in 2h');
    expect(due.transform(new Date(Date.now() - 30 * 60_000).toISOString())).toBe('overdue by 30m');
  });

  it('formats numbers and percentages', () => {
    expect(new CompactPipe().transform(2662)).toMatch(/2[.,]7\s?K/i);
    expect(new CompactPipe().transform(null)).toBe('–');
    expect(new PctPipe().transform(0.101)).toBe('10%');
  });

  it('formats rupees with Indian grouping and dollars normally', () => {
    expect(formatMoney(159999, 'INR')).toBe('₹1,59,999');
    expect(formatMoney(1439.82, 'INR')).toBe('₹1,439.82');
    expect(formatMoney(1999, 'USD')).toBe('$1,999');
    expect(formatMoney(116.8, 'USD', 2)).toBe('$116.80');
    expect(formatMoney(null)).toBe('–');
  });

  it('builds YouTube deep links', () => {
    expect(youtubeAt('PTblI6oYfSU', 74.6)).toBe('https://www.youtube.com/watch?v=PTblI6oYfSU&t=74s');
  });
});

describe('SessionService', () => {
  beforeEach(() => TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] }));

  function withRole(role: 'admin' | 'approver' | 'agent' | 'analyst') {
    const session = TestBed.inject(SessionService);
    session.me.set({
      user: { id: 'u1', email: 'asha@example.com', name: 'Asha Rao', emailVerified: true },
      workspaces: [{ id: 'w1', name: 'Acme', slug: 'acme', isDemo: false, country: 'IN', role, plan: 'Starter', subscriptionStatus: 'ACTIVE', trialEndsAt: null }],
      pendingInvitations: [],
      demoAvailable: false,
    });
    session.select('w1');
    return session;
  }

  it('derives permissions from the workspace role', () => {
    expect(withRole('admin').can('billing.manage')).toBeTrue();
    expect(withRole('approver').can('reply.approve')).toBeTrue();
    expect(withRole('agent').can('reply.approve')).toBeFalse();
    expect(withRole('analyst').can('content.write')).toBeFalse();
  });

  it('builds initials from the name', () => {
    expect(withRole('agent').initials()).toBe('AR');
    expect(initials('raj@example.com')).toBe('R');
    expect(initials('PlayStation (Demo)')).toBe('PD');
  });

  it('counts trial days left', () => {
    const ws = { id: 'w', name: 'x', slug: 'x', isDemo: false, country: 'IN', role: 'admin' as const, plan: 'Pro',
      subscriptionStatus: 'TRIALING' as const, trialEndsAt: new Date(Date.now() + 3.5 * 86_400_000).toISOString() };
    expect(trialDaysLeft(ws)).toBe(4);
    expect(trialDaysLeft({ ...ws, subscriptionStatus: 'ACTIVE' })).toBeNull();
  });

  it('cycles themes system → light → dark → system', () => {
    const session = TestBed.inject(SessionService);
    session.theme.set('system');
    session.cycleTheme();
    expect(session.theme()).toBe('light');
    session.cycleTheme();
    expect(session.theme()).toBe('dark');
    session.cycleTheme();
    expect(session.theme()).toBe('system');
  });
});
