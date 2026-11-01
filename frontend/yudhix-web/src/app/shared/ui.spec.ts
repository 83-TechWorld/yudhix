import { TestBed } from '@angular/core/testing';
import { AgoPipe, CompactPipe, DuePipe, PctPipe, youtubeAt } from './ui';
import { DEMO_USERS, SessionService } from '../core/session.service';

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

  it('builds YouTube deep links', () => {
    expect(youtubeAt('PTblI6oYfSU', 74.6)).toBe('https://www.youtube.com/watch?v=PTblI6oYfSU&t=74s');
  });
});

describe('SessionService', () => {
  beforeEach(() => {
    try { localStorage.removeItem('yudhix.role'); } catch { /* ignore */ }
  });

  it('starts as the agent and toggles to the approver', () => {
    const session = TestBed.inject(SessionService);
    expect(session.role()).toBe('agent');
    expect(session.user().id).toBe(DEMO_USERS.agent.id);
    session.toggleRole();
    expect(session.role()).toBe('approver');
    expect(session.user().id).toBe(DEMO_USERS.approver.id);
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
